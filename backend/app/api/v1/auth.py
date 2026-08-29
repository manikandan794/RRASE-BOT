"""
Authentication endpoints: register (students only), login, refresh, me.

Staff accounts (faculty/admin/principal) are created by an admin through
/api/v1/users, never through public self-registration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_current_user_roles
from app.auth.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.session import get_db
from app.models.role import Role, RoleName
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    student_role = db.query(Role).filter(Role.name == RoleName.STUDENT).first()
    if not student_role:
        raise HTTPException(
            status_code=500,
            detail="Student role is not seeded. Run scripts/seed_roles.py first.",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=student_role.id))
    db.commit()
    db.refresh(user)

    log_action(db, actor_id=user.id, action="user.register", target=f"user:{user.id}")
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name,
        is_active=user.is_active, roles=[RoleName.STUDENT],
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    invalid = HTTPException(status_code=401, detail="Invalid email or password.")
    if not user or user.is_deleted or not verify_password(payload.password, user.hashed_password):
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    roles = get_current_user_roles(user)
    access = create_access_token(subject=user.id, roles=roles)
    refresh = create_refresh_token(subject=user.id)
    log_action(db, actor_id=user.id, action="user.login", target=f"user:{user.id}")
    return TokenResponse(access_token=access, refresh_token=refresh, roles=roles)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise invalid
        user_id = data.get("sub")
    except JWTError:
        raise invalid

    user = db.get(User, user_id)
    if not user or not user.is_active or user.is_deleted:
        raise invalid

    roles = get_current_user_roles(user)
    access = create_access_token(subject=user.id, roles=roles)
    new_refresh = create_refresh_token(subject=user.id)
    return TokenResponse(access_token=access, refresh_token=new_refresh, roles=roles)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=get_current_user_roles(current_user),
    )

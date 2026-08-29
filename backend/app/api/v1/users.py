"""Admin-only user & role management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_roles, require_roles
from app.auth.security import hash_password
from app.database.session import get_db
from app.models.role import Role, RoleName
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.auth import UserOut
from app.schemas.common import MessageResponse
from app.schemas.users import StaffCreateRequest, UserRoleUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(RoleName.ADMIN)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    users = db.query(User).all()
    return [
        UserOut(id=u.id, email=u.email, full_name=u.full_name, is_active=u.is_active,
                roles=get_current_user_roles(u))
        for u in users
    ]


@router.post("/staff", response_model=UserOut, status_code=201)
def create_staff_account(
    payload: StaffCreateRequest, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    if payload.role not in {RoleName.FACULTY, RoleName.ADMIN, RoleName.PRINCIPAL}:
        raise HTTPException(status_code=400, detail="Role must be faculty, admin, or principal.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        raise HTTPException(status_code=500, detail="Role is not seeded. Run scripts/seed_roles.py.")

    user = User(email=payload.email, full_name=payload.full_name,
                hashed_password=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    log_action(db, actor_id=admin.id, action="user.create_staff", target=f"user:{user.id}",
               details=payload.role)
    return UserOut(id=user.id, email=user.email, full_name=user.full_name,
                   is_active=user.is_active, roles=[payload.role])


@router.patch("/{user_id}", response_model=MessageResponse)
def update_user(
    user_id: str, payload: UserRoleUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_only)
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Not found.")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    log_action(db, actor_id=admin.id, action="user.update", target=f"user:{user_id}")
    return MessageResponse(message="Updated.")

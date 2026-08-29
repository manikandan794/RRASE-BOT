"""
FastAPI dependencies for authentication and role-based access control (RBAC).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import JWTError, decode_token
from app.database.session import get_db
from app.models.faculty import Faculty
from app.models.role import RoleName
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise credentials_error
    return user


def get_current_user_roles(user: User) -> list[str]:
    return [ur.role.name for ur in user.user_roles]


def require_roles(*allowed_roles: str):
    """Dependency factory: `Depends(require_roles(RoleName.ADMIN, RoleName.PRINCIPAL))`."""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = set(get_current_user_roles(current_user))
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return _checker


def get_current_faculty_profile(
    current_user: User = Depends(require_roles(RoleName.FACULTY)),
    db: Session = Depends(get_db),
) -> Faculty:
    """Resolves the Faculty profile linked to the logged-in user and
    enforces that department-scoped writes/reads are always evaluated
    against THIS server-derived profile - never a department_id supplied
    by the frontend. 403s if the account has the faculty role but no
    linked profile (e.g. not yet provisioned by an admin)."""
    profile = db.query(Faculty).filter(Faculty.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No faculty profile is linked to this account yet. Contact an administrator.",
        )
    return profile


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None

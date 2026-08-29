from pydantic import BaseModel, EmailStr, Field


class StaffCreateRequest(BaseModel):
    """Used by admins to create faculty/admin/principal accounts - never
    exposed via public self-registration."""
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str  # one of RoleName.FACULTY / ADMIN / PRINCIPAL


class UserRoleUpdate(BaseModel):
    is_active: bool | None = None

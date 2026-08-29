"""
Role model - part of the Role-Based Access Control (RBAC) foundation.

Full role behaviour (permission checks, protected routes) is implemented in
Phase 2 (Authentication). Phase 1 only establishes the schema so that the
database structure does not need to change later.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role id={self.id} name={self.name!r}>"


# Standard role names used across the application.
# Admin manages/seeds these rows - this is just a shared constant, not a
# hard-coded college fact.
class RoleName:
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"
    PRINCIPAL = "principal"

"""
Seed the four standard roles (student, faculty, admin, principal).

This is structural seed data (role names the application logic depends on),
NOT sample college data. Run once after migrations:

    python scripts/seed_roles.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal  # noqa: E402
from app.models import Role, RoleName  # noqa: E402

ROLES = [
    (RoleName.STUDENT, "Can use the chatbot and view their own chat history."),
    (RoleName.FACULTY, "Can manage permitted department information."),
    (RoleName.ADMIN, "Manages college-wide information, users, and content."),
    (RoleName.PRINCIPAL, "Executive dashboard: analytics, approvals, oversight."),
]


def seed_roles() -> None:
    db = SessionLocal()
    try:
        created = 0
        for name, description in ROLES:
            existing = db.query(Role).filter(Role.name == name).first()
            if existing:
                continue
            db.add(Role(name=name, description=description))
            created += 1
        db.commit()
        print(f"Seed complete. {created} new role(s) created, {len(ROLES) - created} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()

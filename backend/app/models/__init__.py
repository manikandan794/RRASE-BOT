"""
Import every ORM model here so that:
1. `Base.metadata` knows about all tables (needed for Alembic autogenerate
   and for `Base.metadata.create_all` in tests).
2. Other modules can do `from app.models import User, Role` etc.
"""
from app.database.base import Base  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.chat import ChatMessage, Conversation  # noqa: F401
from app.models.college import CollegeInfo  # noqa: F401
from app.models.contact import Contact  # noqa: F401
from app.models.course import Course  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.facility import Facility  # noqa: F401
from app.models.faculty import Faculty  # noqa: F401
from app.models.faq import FAQ  # noqa: F401
from app.models.feedback import Feedback, UnansweredQuestion  # noqa: F401
from app.models.knowledge import (  # noqa: F401
    ApprovalStatus,
    KnowledgeChunk,
    SourceType,
    UploadedDocument,
    WebsiteImportBatch,
)
from app.models.notice import Notice  # noqa: F401
from app.models.role import Role, RoleName  # noqa: F401
from app.models.system_settings import SystemSetting  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_role import UserRole  # noqa: F401

__all__ = [
    "Base", "AuditLog", "ChatMessage", "Conversation", "CollegeInfo", "Contact",
    "Course", "Department", "Event", "Facility", "Faculty", "FAQ", "Feedback",
    "UnansweredQuestion", "ApprovalStatus", "KnowledgeChunk", "SourceType",
    "UploadedDocument", "WebsiteImportBatch", "Notice", "Role", "RoleName",
    "SystemSetting", "User", "UserRole",
]

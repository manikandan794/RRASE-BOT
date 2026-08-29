"""Lightweight audit trail. Never raises - a failed audit write must never
break the request it is logging."""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(db: Session, actor_id: str | None, action: str, target: str | None = None,
                details: str | None = None) -> None:
    try:
        db.add(AuditLog(actor_id=actor_id, action=action, target=target, details=details))
        db.commit()
    except Exception:
        db.rollback()

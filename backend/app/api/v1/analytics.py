"""Dashboard analytics for admin/principal - aggregate counts only, never
raw chat transcripts of individual students unless explicitly queried by
conversation id elsewhere (privacy-by-default)."""
from sqlalchemy import func
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.chat import ChatMessage, Conversation
from app.models.feedback import Feedback, UnansweredQuestion
from app.models.knowledge import KnowledgeChunk
from app.models.role import RoleName
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary, AuditLogOut

router = APIRouter(tags=["analytics"])
read_dep = require_roles(RoleName.ADMIN, RoleName.PRINCIPAL, RoleName.FACULTY)
admin_dep = require_roles(RoleName.ADMIN, RoleName.PRINCIPAL)


@router.get("/analytics/summary", response_model=AnalyticsSummary, dependencies=[Depends(read_dep)])
def summary(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(ChatMessage.id)).scalar() or 0

    by_source_rows = (
        db.query(ChatMessage.answer_source, func.count(ChatMessage.id))
        .filter(ChatMessage.role == "assistant")
        .group_by(ChatMessage.answer_source)
        .all()
    )
    messages_by_source = {source or "unknown": count for source, count in by_source_rows}

    unresolved = db.query(func.count(UnansweredQuestion.id)).filter(
        UnansweredQuestion.resolved.is_(False)
    ).scalar() or 0

    avg_rating = db.query(func.avg(Feedback.rating)).scalar()

    total_chunks = db.query(func.count(KnowledgeChunk.id)).scalar() or 0
    embedded_chunks = db.query(func.count(KnowledgeChunk.id)).filter(
        KnowledgeChunk.embedded.is_(True)
    ).scalar() or 0

    return AnalyticsSummary(
        total_users=total_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        messages_by_source=messages_by_source,
        unresolved_unanswered=unresolved,
        average_feedback_rating=float(avg_rating) if avg_rating is not None else None,
        total_knowledge_chunks=total_chunks,
        embedded_knowledge_chunks=embedded_chunks,
    )


@router.get("/audit-logs", response_model=list[AuditLogOut], dependencies=[Depends(admin_dep)])
def audit_logs(db: Session = Depends(get_db), limit: int = 200):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

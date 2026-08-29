from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    messages_by_source: dict[str, int]
    unresolved_unanswered: int
    average_feedback_rating: float | None
    total_knowledge_chunks: int
    embedded_knowledge_chunks: int


class AuditLogOut(BaseModel):
    id: str
    actor_id: str | None
    action: str
    target: str | None
    details: str | None

    model_config = {"from_attributes": True}

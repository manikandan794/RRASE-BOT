from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    answer_source: str | None = None

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessageOut


class FeedbackIn(BaseModel):
    message_id: str | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class UnansweredQuestionOut(BaseModel):
    id: str
    question: str
    times_asked: int
    resolved: bool
    resolution: str | None = None
    department_id: str | None = None

    model_config = {"from_attributes": True}


class UnansweredQuestionTriage(BaseModel):
    """Admin/principal-only: route an unanswered question to a department
    so that department's faculty (and only that department's faculty) can
    see and resolve it."""
    department_id: str | None = None


class UnansweredQuestionResolve(BaseModel):
    resolution: str | None = None

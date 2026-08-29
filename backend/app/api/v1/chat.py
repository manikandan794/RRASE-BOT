"""
Chat endpoints. `/chat` is open to any logged-in student/faculty/staff (or
anonymous, if the frontend allows it) but is always rate-limited, since it
is the most expensive endpoint (it may call an LLM).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.database.session import get_db
from app.models.chat import ChatMessage, Conversation
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services.chat_service import answer_question, get_or_create_conversation
from app.utils.rate_limit import rate_limit_dependency
from app.utils.validators import is_reasonable_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_dependency)])
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    question = payload.question.strip()
    if not is_reasonable_question(question):
        question = question[:2000]

    user_id = current_user.id if current_user else None
    conversation = get_or_create_conversation(db, payload.conversation_id, user_id)
    message = answer_question(db, question, conversation, user_id)

    return ChatResponse(conversation_id=conversation.id, message=ChatMessageOut.model_validate(message))


@router.get("/history/{conversation_id}", response_model=list[ChatMessageOut])
def history(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        return []
    return conversation.messages

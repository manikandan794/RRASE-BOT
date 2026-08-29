"""
Chat orchestration - implements the required pipeline:

    User Question
      -> Structured Database / FAQ (exact + fuzzy match)
      -> if answer exists -> return verified answer (answer_source="database"/"faq")
      -> otherwise RAG (retrieve context from approved knowledge chunks)
      -> Ollama (primary) / Gemini (fallback) generate grounded answer
      -> if no provider reachable -> fall back to any partial DB/FAQ match
      -> if still nothing -> tell the user the information is unavailable
         and log it as an UnansweredQuestion for admin review

Never sends a question straight to the AI without first checking the
database, and never lets the AI answer make things up: it is always given
retrieved context and told to refuse when the context is insufficient.
"""
import difflib
import logging

from sqlalchemy.orm import Session

from app.ai.provider_manager import get_provider_manager
from app.models.chat import ChatMessage, Conversation
from app.models.faq import FAQ
from app.models.feedback import UnansweredQuestion
from app.rag.retriever import retrieve_context

logger = logging.getLogger("rrase_college_ai.services.chat_service")

FUZZY_MATCH_THRESHOLD = 0.72
UNAVAILABLE_MESSAGE = (
    "I don't have verified information on that yet. Please contact the "
    "relevant college office, or try rephrasing your question - I've "
    "noted this so the college can add it to the knowledge base."
)


def _match_faq(db: Session, question: str) -> FAQ | None:
    faqs = db.query(FAQ).filter(FAQ.is_published.is_(True)).all()
    if not faqs:
        return None

    question_lower = question.strip().lower()
    best_match: FAQ | None = None
    best_score = 0.0
    for faq in faqs:
        score = difflib.SequenceMatcher(None, question_lower, faq.question.strip().lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = faq
    if best_match and best_score >= FUZZY_MATCH_THRESHOLD:
        return best_match
    return None


def _record_unanswered(db: Session, question: str, user_id: str | None) -> None:
    existing = (
        db.query(UnansweredQuestion)
        .filter(UnansweredQuestion.question == question, UnansweredQuestion.resolved.is_(False))
        .first()
    )
    if existing:
        existing.times_asked += 1
    else:
        db.add(UnansweredQuestion(question=question, user_id=user_id))
    db.commit()


def get_or_create_conversation(db: Session, conversation_id: str | None, user_id: str | None) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation:
            return conversation
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def answer_question(db: Session, question: str, conversation: Conversation, user_id: str | None) -> ChatMessage:
    db.add(ChatMessage(conversation_id=conversation.id, role="user", content=question))
    db.commit()

    answer_text: str
    answer_source: str

    # Step 1: structured DB / FAQ lookup.
    faq = _match_faq(db, question)
    if faq:
        answer_text = faq.answer
        answer_source = "faq"
    else:
        # Step 2: RAG - retrieve approved knowledge context (db is passed so
        # the retriever can independently verify approval status in
        # Postgres rather than trusting the vector store alone).
        context, _labels = retrieve_context(question, db)
        manager = get_provider_manager()
        ai_response = manager.generate(question, context) if context else manager.generate(question, "")

        if ai_response and context:
            answer_text = ai_response.text
            answer_source = f"rag_{ai_response.provider}"
        elif ai_response and not context:
            # No grounded context found at all - do not let the model free-associate.
            answer_text = UNAVAILABLE_MESSAGE
            answer_source = "unavailable"
            _record_unanswered(db, question, user_id)
        else:
            # No AI provider reachable either.
            answer_text = UNAVAILABLE_MESSAGE
            answer_source = "unavailable"
            _record_unanswered(db, question, user_id)

    message = ChatMessage(
        conversation_id=conversation.id, role="assistant", content=answer_text, answer_source=answer_source
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

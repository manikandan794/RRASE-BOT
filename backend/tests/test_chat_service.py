"""
Chat service tests. The AI provider manager is monkeypatched so the test
suite never makes a real network call to Ollama/Gemini.
"""
from unittest.mock import MagicMock, patch

from app.ai.base import AIResponse
from app.models import FAQ
from app.services.chat_service import answer_question, get_or_create_conversation


def test_faq_match_short_circuits_ai(client, test_db_session):
    test_db_session.add(FAQ(
        question="What are the college office hours?",
        answer="The office is open 9 AM to 5 PM, Monday to Saturday.",
        is_published=True,
    ))
    test_db_session.commit()

    conversation = get_or_create_conversation(test_db_session, None, None)
    with patch("app.services.chat_service.get_provider_manager") as mock_manager:
        message = answer_question(
            test_db_session, "What are the college office hours?", conversation, None
        )
    mock_manager.assert_not_called()
    assert message.answer_source == "faq"
    assert "9 AM" in message.content


def test_no_context_and_no_provider_records_unanswered(client, test_db_session):
    conversation = get_or_create_conversation(test_db_session, None, None)

    with patch("app.services.chat_service.retrieve_context", return_value=("", [])), \
         patch("app.services.chat_service.get_provider_manager") as mock_manager_factory:
        mock_manager = MagicMock()
        mock_manager.generate.return_value = None
        mock_manager_factory.return_value = mock_manager

        message = answer_question(test_db_session, "Does the hostel have wifi?", conversation, None)

    assert message.answer_source == "unavailable"

    from app.models import UnansweredQuestion
    unanswered = test_db_session.query(UnansweredQuestion).all()
    assert len(unanswered) == 1
    assert unanswered[0].question == "Does the hostel have wifi?"


def test_grounded_context_uses_ai_response(client, test_db_session):
    conversation = get_or_create_conversation(test_db_session, None, None)

    with patch("app.services.chat_service.retrieve_context",
               return_value=("[Source: prospectus.pdf]\nECE offers a 4-year B.E. program.", ["prospectus.pdf"])), \
         patch("app.services.chat_service.get_provider_manager") as mock_manager_factory:
        mock_manager = MagicMock()
        mock_manager.generate.return_value = AIResponse(
            text="ECE is a 4-year Bachelor of Engineering program.", provider="ollama", model="llama3.1"
        )
        mock_manager_factory.return_value = mock_manager

        message = answer_question(test_db_session, "How long is the ECE course?", conversation, None)

    assert message.answer_source == "rag_ollama"
    assert "4-year" in message.content

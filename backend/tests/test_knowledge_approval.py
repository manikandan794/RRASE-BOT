"""
Tests for CRITICAL FIX #1: unapproved information must never be retrieved.

Verifies:
- staged (PENDING) chunks are never embedded into the vector store
- approve_source_chunks() is required before a chunk becomes retrievable
- reject_source_chunks() removes staged chunks entirely
- retrieve_context() independently re-checks DB approval status and
  ignores/purges any vector hit that Postgres no longer considers approved
  (defense in depth against a vector store that drifts from Postgres)
"""
from unittest.mock import patch

from app.models.knowledge import ApprovalStatus, KnowledgeChunk, SourceType
from app.rag.indexer import approve_source_chunks, reject_source_chunks, stage_chunks
from app.rag.retriever import retrieve_context


def _fake_embed_result(texts):
    return ([[0.1] * 8 for _ in texts], "ollama")


def test_staged_chunks_are_pending_and_not_embedded(test_db_session):
    rows = stage_chunks(
        test_db_session,
        "This is a reasonably long piece of extracted PDF text about the library timings and rules. " * 3,
        source_type=SourceType.DOCUMENT,
        source_id="doc-1",
        source_label="handbook.pdf",
    )
    assert len(rows) > 0
    for row in rows:
        assert row.status == ApprovalStatus.PENDING
        assert row.embedded is False


def test_approval_required_before_retrieval(test_db_session):
    stage_chunks(
        test_db_session,
        "The library is open from 8 AM to 8 PM on all working days. " * 5,
        source_type=SourceType.DOCUMENT,
        source_id="doc-2",
        source_label="handbook.pdf",
    )

    fake_hit = {
        "id": None,  # filled below once we know the pending chunk's id
        "text": "The library is open from 8 AM to 8 PM on all working days.",
        "metadata": {"source_label": "handbook.pdf", "source_type": "document"},
        "distance": 0.2,
    }
    pending_chunk = test_db_session.query(KnowledgeChunk).filter_by(source_id="doc-2").first()
    fake_hit["id"] = pending_chunk.id

    with patch("app.rag.retriever.get_provider_manager") as mock_manager_factory, \
         patch("app.rag.vector_store.query", return_value=[fake_hit]), \
         patch("app.rag.vector_store.delete_chunk") as mock_delete:
        mock_manager = mock_manager_factory.return_value
        mock_manager.embed.return_value = _fake_embed_result(["question"])

        # Even though the vector store "found" this chunk (simulating a bug
        # or drift), it is still PENDING in Postgres, so it must be dropped.
        context, labels = retrieve_context("What are the library hours?", test_db_session)

    assert context == ""
    assert labels == []
    mock_delete.assert_called_once_with(pending_chunk.id)


def test_approve_then_retrieve_succeeds(test_db_session):
    stage_chunks(
        test_db_session,
        "The library is open from 8 AM to 8 PM on all working days. " * 5,
        source_type=SourceType.DOCUMENT,
        source_id="doc-3",
        source_label="handbook.pdf",
    )

    with patch("app.rag.indexer.get_provider_manager") as mock_manager_factory, \
         patch("app.rag.vector_store.upsert_chunk") as mock_upsert:
        mock_manager = mock_manager_factory.return_value
        mock_manager.embed.side_effect = lambda texts: _fake_embed_result(texts)
        embedded_count = approve_source_chunks(test_db_session, SourceType.DOCUMENT, "doc-3")

    assert embedded_count > 0
    assert mock_upsert.called
    approved_chunk = test_db_session.query(KnowledgeChunk).filter_by(source_id="doc-3").first()
    assert approved_chunk.status == ApprovalStatus.APPROVED
    assert approved_chunk.embedded is True

    fake_hit = {
        "id": approved_chunk.id,
        "text": approved_chunk.text,
        "metadata": {"source_label": "handbook.pdf", "source_type": "document"},
        "distance": 0.2,
    }
    with patch("app.rag.retriever.get_provider_manager") as mock_manager_factory, \
         patch("app.rag.vector_store.query", return_value=[fake_hit]):
        mock_manager = mock_manager_factory.return_value
        mock_manager.embed.return_value = _fake_embed_result(["question"])
        context, labels = retrieve_context("What are the library hours?", test_db_session)

    assert "library" in context.lower()
    assert labels == ["handbook.pdf"]


def test_reject_removes_staged_chunks(test_db_session):
    stage_chunks(
        test_db_session,
        "Some content that should never be approved because it is inaccurate. " * 5,
        source_type=SourceType.DOCUMENT,
        source_id="doc-4",
        source_label="draft.pdf",
    )
    assert test_db_session.query(KnowledgeChunk).filter_by(source_id="doc-4").count() > 0

    reject_source_chunks(test_db_session, SourceType.DOCUMENT, "doc-4")

    assert test_db_session.query(KnowledgeChunk).filter_by(source_id="doc-4").count() == 0


def test_retrieve_context_without_db_session_is_skipped():
    # Old/incorrect call sites that forget to pass `db` must never fall
    # back to trusting the vector store alone.
    context, labels = retrieve_context("anything")
    assert context == ""
    assert labels == []

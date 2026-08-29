"""
Retrieval step of the RAG pipeline: embed the question, query the vector
store, filter by a minimum similarity, and return grounded context text
plus the source labels used (for citation in the chat response).

APPROVAL-AWARE RETRIEVAL (CRITICAL FIX #1 / audit item #4): the vector
store is not treated as the source of truth for approval - a hit is only
used if the corresponding KnowledgeChunk row in Postgres independently
confirms status == APPROVED right now. This means even if a bug elsewhere
ever wrote an unapproved vector, or an admin rejects/archives a chunk
after it was embedded, retrieval still will not surface it.
"""
import logging

from sqlalchemy.orm import Session

from app.ai.provider_manager import get_provider_manager
from app.config import get_settings
from app.models.knowledge import ApprovalStatus, KnowledgeChunk
from app.rag import vector_store

logger = logging.getLogger("rrase_college_ai.rag.retriever")


def retrieve_context(question: str, db: Session | None = None) -> tuple[str, list[str]]:
    """Returns (context_text, source_labels). Both are empty if nothing
    relevant/approved is found or if no embedding backend is reachable -
    callers must treat that as 'no context', never as an error to surface
    raw. `db` is required to perform the approval cross-check; if it is
    not supplied (e.g. an old caller), retrieval is skipped entirely rather
    than trusting the vector store alone."""
    if db is None:
        logger.warning("retrieve_context called without a db session; skipping RAG retrieval.")
        return "", []

    settings = get_settings()
    manager = get_provider_manager()

    embed_result = manager.embed([question])
    if not embed_result:
        logger.info("No embedding backend available; skipping RAG retrieval.")
        return "", []

    vectors, _provider_name = embed_result
    hits = vector_store.query(vectors[0], top_k=settings.RAG_TOP_K)
    if not hits:
        return "", []

    # Chroma cosine distance: 0 = identical, 2 = opposite. Convert to a
    # similarity score and drop weak matches rather than force-feeding the
    # model irrelevant context (which invites fabrication).
    candidates = []
    for hit in hits:
        similarity = 1 - (hit["distance"] / 2)
        if similarity >= settings.RAG_MIN_SIMILARITY:
            candidates.append(hit)
    if not candidates:
        return "", []

    # Independent DB approval check - never trust vector-store metadata alone.
    chunk_ids = [hit["id"] for hit in candidates]
    approved_rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.id.in_(chunk_ids), KnowledgeChunk.status == ApprovalStatus.APPROVED)
        .all()
    )
    approved_ids = {row.id for row in approved_rows}

    stale_ids = [cid for cid in chunk_ids if cid not in approved_ids]
    if stale_ids:
        # Defense in depth: the vector store had an entry that Postgres no
        # longer considers approved (rejected/archived/deleted after being
        # embedded, or a data inconsistency). Purge it so it stops costing
        # a retrieval slot next time, and never use it now.
        for stale_id in stale_ids:
            vector_store.delete_chunk(stale_id)
        logger.warning(
            "Dropped %s non-approved/stale vector hit(s) during retrieval: %s",
            len(stale_ids), stale_ids,
        )

    relevant = [hit for hit in candidates if hit["id"] in approved_ids]
    if not relevant:
        return "", []

    context_parts = []
    labels = []
    for hit in relevant:
        label = hit["metadata"].get("source_label") or hit["metadata"].get("source_type", "college records")
        context_parts.append(f"[Source: {label}]\n{hit['text']}")
        labels.append(label)

    return "\n\n".join(context_parts), labels

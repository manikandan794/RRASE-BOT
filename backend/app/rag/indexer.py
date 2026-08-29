"""
Indexing service - the ONLY place that writes to the vector store.

Lifecycle enforced here (see CRITICAL FIX #1 in the audit):

    stage_chunks()           -> chunk + save KnowledgeChunk rows as PENDING.
                                 Nothing is embedded, nothing is written to
                                 the vector store, so PENDING text can never
                                 be retrieved by the chatbot yet.
    approve_source_chunks()  -> called by a review endpoint once an
                                 admin/principal explicitly approves the
                                 source. Embeds the PENDING chunks for that
                                 source and flips them to APPROVED.
    reject_source_chunks()   -> deletes the PENDING chunks for a source
                                 (nothing was ever embedded, so there is
                                 nothing to remove from the vector store).
    remove_source_chunks()   -> deletes ALL chunks (any status) for a
                                 source, from both Postgres and the vector
                                 store. Used for document/website deletion.

Both the document-upload flow and the website-import-approval flow share
this same code path, so "unapproved information must never be retrievable"
is enforced in one place instead of once per source type.
"""
import logging

from sqlalchemy.orm import Session

from app.ai.provider_manager import get_provider_manager
from app.models.knowledge import ApprovalStatus, KnowledgeChunk
from app.rag import vector_store
from app.rag.chunking import chunk_text

logger = logging.getLogger("rrase_college_ai.rag.indexer")


def stage_chunks(
    db: Session,
    text: str,
    source_type: str,
    source_id: str | None,
    source_label: str | None,
) -> list[KnowledgeChunk]:
    """Chunks `text` and saves each chunk as a PENDING KnowledgeChunk row.
    Does NOT embed and does NOT touch the vector store - staged chunks are
    inert until approve_source_chunks() is called for this source."""
    chunks = chunk_text(text)
    rows: list[KnowledgeChunk] = []
    for chunk in chunks:
        row = KnowledgeChunk(
            source_type=source_type,
            source_id=source_id,
            source_label=source_label,
            text=chunk,
            status=ApprovalStatus.PENDING,
            embedded=False,
        )
        rows.append(row)
        db.add(row)
    db.commit()
    return rows


def approve_source_chunks(db: Session, source_type: str, source_id: str) -> int:
    """Embeds and approves every PENDING chunk belonging to (source_type,
    source_id). Returns the number of chunks successfully embedded. Chunks
    remain PENDING (never retrievable) if no embedding backend is currently
    reachable, so re-running this later (once Ollama/Gemini is back) is
    always safe and idempotent."""
    rows = (
        db.query(KnowledgeChunk)
        .filter(
            KnowledgeChunk.source_type == source_type,
            KnowledgeChunk.source_id == source_id,
            KnowledgeChunk.status == ApprovalStatus.PENDING,
        )
        .all()
    )
    if not rows:
        return 0

    manager = get_provider_manager()
    embed_result = manager.embed([row.text for row in rows])

    embedded_count = 0
    if embed_result:
        vectors, provider_name = embed_result
        for row, vector in zip(rows, vectors):
            try:
                vector_store.upsert_chunk(
                    chunk_id=row.id,
                    text=row.text,
                    embedding=vector,
                    metadata={
                        "source_type": row.source_type,
                        "source_label": row.source_label or "",
                        "source_id": row.source_id or "",
                        "status": ApprovalStatus.APPROVED,
                    },
                )
                row.embedded = True
                row.status = ApprovalStatus.APPROVED
                row.embedding_provider = provider_name
                embedded_count += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to store embedding for chunk %s: %s", row.id, exc)
        logger.info("Embedded %s/%s chunks via %s", embedded_count, len(rows), provider_name)
    else:
        logger.warning(
            "No embedding backend reachable - %s chunk(s) remain PENDING "
            "(not retrievable). Re-run approval once Ollama/Gemini is configured.",
            len(rows),
        )

    db.commit()
    return embedded_count


def reject_source_chunks(db: Session, source_type: str, source_id: str) -> None:
    """Deletes PENDING chunks for a source that was rejected. Nothing here
    was ever embedded, so there is nothing to remove from the vector store."""
    rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.source_type == source_type, KnowledgeChunk.source_id == source_id)
        .all()
    )
    for row in rows:
        if row.embedded:
            # Defensive: should not normally happen for a rejected source,
            # but never leave an embedded/retrievable vector behind.
            vector_store.delete_chunk(row.id)
        db.delete(row)
    db.commit()


def remove_source_chunks(db: Session, source_type: str, source_id: str) -> None:
    """Deletes every chunk (any status) tied to a source, from both Postgres
    and the vector store. Used when a document/website source is deleted."""
    chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.source_type == source_type, KnowledgeChunk.source_id == source_id)
        .all()
    )
    for chunk in chunks:
        vector_store.delete_chunk(chunk.id)
        db.delete(chunk)
    db.commit()


def index_text(
    db: Session,
    text: str,
    source_type: str,
    source_id: str | None,
    source_label: str | None,
) -> int:
    """Convenience helper for flows where the text is ALREADY approved at
    the moment this is called (e.g. the website-import review endpoint,
    where an admin has just clicked Approve). Stages the chunks and
    immediately approves+embeds them. Do NOT use this for content that has
    not yet been reviewed - use stage_chunks() + approve_source_chunks()
    instead so unreviewed content stays PENDING."""
    rows = stage_chunks(db, text, source_type, source_id, source_label)
    if not rows:
        return 0
    if source_id is not None:
        return approve_source_chunks(db, source_type, source_id)
    # No stable source_id to key off (shouldn't normally happen) - approve
    # the specific rows we just created directly.
    manager = get_provider_manager()
    embed_result = manager.embed([row.text for row in rows])
    embedded_count = 0
    if embed_result:
        vectors, provider_name = embed_result
        for row, vector in zip(rows, vectors):
            try:
                vector_store.upsert_chunk(
                    chunk_id=row.id, text=row.text, embedding=vector,
                    metadata={"source_type": row.source_type, "source_label": row.source_label or "",
                              "source_id": row.source_id or "", "status": ApprovalStatus.APPROVED},
                )
                row.embedded = True
                row.status = ApprovalStatus.APPROVED
                row.embedding_provider = provider_name
                embedded_count += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to store embedding for chunk %s: %s", row.id, exc)
        db.commit()
    return embedded_count


def rebuild_index(db: Session) -> dict:
    """Administrator operation: wipes the entire vector store and
    re-embeds every currently-APPROVED KnowledgeChunk row from Postgres
    (the source of truth). Use this after changing the embedding model/
    provider, or if the vector store and Postgres have drifted apart.
    Never re-embeds PENDING/REJECTED/ARCHIVED chunks."""
    approved = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.status == ApprovalStatus.APPROVED)
        .all()
    )
    vector_store.reset_collection()

    manager = get_provider_manager()
    total = len(approved)
    embedded = 0
    batch_size = 32
    for i in range(0, total, batch_size):
        batch = approved[i : i + batch_size]
        embed_result = manager.embed([row.text for row in batch])
        if not embed_result:
            logger.warning("rebuild_index: no embedding backend reachable, stopping early.")
            break
        vectors, provider_name = embed_result
        for row, vector in zip(batch, vectors):
            try:
                vector_store.upsert_chunk(
                    chunk_id=row.id, text=row.text, embedding=vector,
                    metadata={"source_type": row.source_type, "source_label": row.source_label or "",
                              "source_id": row.source_id or "", "status": ApprovalStatus.APPROVED},
                )
                row.embedded = True
                row.embedding_provider = provider_name
                embedded += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("rebuild_index: failed to embed chunk %s: %s", row.id, exc)
    db.commit()
    return {"total_approved_chunks": total, "re_embedded": embedded}

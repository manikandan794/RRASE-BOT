"""
Knowledge base models.

Every fact the RAG pipeline can retrieve lives in `KnowledgeChunk`, tagged
with the source it came from (`document` or `website`) and an approval
status. Nothing reaches `KnowledgeChunk` with status=APPROVED without a
human (admin/principal) explicitly approving it - this is what implements
"Website information must NOT be blindly trusted".
"""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, generate_uuid


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class SourceType:
    DOCUMENT = "document"
    WEBSITE = "website"
    MANUAL = "manual"


class UploadedDocument(Base, TimestampMixin):
    """A PDF/doc uploaded by an admin/authorized faculty, before/after text
    extraction. status follows UPLOADED->PROCESSING->PENDING->APPROVED/
    REJECTED/FAILED->ARCHIVED. Chunks are only embedded once this document
    is explicitly reviewed and APPROVED - see rag/indexer.py."""
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Nullable: NULL means "college-wide", not owned by a single department.
    # Faculty uploads are always tagged with the uploader's own department
    # (derived server-side, never trusted from the request body).
    department_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING, nullable=False)
    extracted_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class WebsiteImportBatch(Base, TimestampMixin):
    """One run of 'import the official website'. Holds raw cleaned text per
    page before an admin reviews/approves it into KnowledgeChunk rows.

    content_hash lets a re-import detect that a previously-approved page is
    unchanged (skip re-creating a pending row) vs. changed (create a new
    pending "version" and mark the old approved batch as superseded so it
    stops being re-embedded, without silently deleting the audit trail)."""
    __tablename__ = "website_import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    page_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class KnowledgeChunk(Base, TimestampMixin):
    """A chunk of text staged for (or approved into) the RAG knowledge base.

    IMPORTANT (approval security): status defaults to PENDING. A chunk is
    only embedded into the vector store, and only returned by
    rag/retriever.py, once status == APPROVED. Rows are created here for
    document/website/manual sources alike so every source follows the same
    reviewable lifecycle - nothing reaches APPROVED without an explicit
    admin/principal action in the corresponding review endpoint.
    """
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING, nullable=False, index=True)
    embedded: Mapped[bool] = mapped_column(default=False)
    # Which provider/model produced the stored vector, so a later embedding
    # model change can be detected instead of silently mixing dimensions.
    embedding_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

"""faculty department scoping + knowledge-approval hardening

Adds:
- faqs.department_id, notices.department_id (department-scoped content
  faculty may manage for their own department only)
- notices.expires_at (so expired notices can be excluded from "current"
  information)
- uploaded_documents.department_id, uploaded_documents.reviewed_by
  (CRITICAL FIX #1: documents now go through an explicit review step
  before their chunks are embedded/approved)
- website_import_batches.content_hash, .superseded_by (avoid uncontrolled
  duplicate knowledge on re-import; CRITICAL FIX #2)
- knowledge_chunks.embedding_provider, .embedding_model (observability for
  future embedding-model migrations; CRITICAL FIX #5)
- unanswered_questions.department_id, .resolution, .resolved_by
  (department-scoped faculty visibility)

Data note: existing knowledge_chunks rows keep their current status
(historically defaulted to "approved" on creation by the old indexer).
This migration does NOT retroactively mark them pending - that would be a
silent, surprising content change for an already-deployed install. New
rows created after this migration go through the new stage/approve
lifecycle in app/rag/indexer.py, which explicitly sets status.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "faqs",
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column(
        "notices",
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
    )
    op.add_column("notices", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "uploaded_documents",
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("uploaded_documents", sa.Column("reviewed_by", sa.String(36), nullable=True))

    op.add_column("website_import_batches", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index(
        "ix_website_import_batches_content_hash", "website_import_batches", ["content_hash"]
    )
    op.add_column("website_import_batches", sa.Column("superseded_by", sa.String(36), nullable=True))

    op.add_column("knowledge_chunks", sa.Column("embedding_provider", sa.String(50), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedding_model", sa.String(100), nullable=True))
    op.create_index("ix_knowledge_chunks_status", "knowledge_chunks", ["status"])
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])

    op.add_column(
        "unanswered_questions",
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("unanswered_questions", sa.Column("resolution", sa.Text(), nullable=True))
    op.add_column("unanswered_questions", sa.Column("resolved_by", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("unanswered_questions", "resolved_by")
    op.drop_column("unanswered_questions", "resolution")
    op.drop_column("unanswered_questions", "department_id")

    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_status", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "embedding_model")
    op.drop_column("knowledge_chunks", "embedding_provider")

    op.drop_column("website_import_batches", "superseded_by")
    op.drop_index("ix_website_import_batches_content_hash", table_name="website_import_batches")
    op.drop_column("website_import_batches", "content_hash")

    op.drop_column("uploaded_documents", "reviewed_by")
    op.drop_column("uploaded_documents", "department_id")

    op.drop_column("notices", "expires_at")
    op.drop_column("notices", "department_id")
    op.drop_column("faqs", "department_id")

"""full feature set: college info, departments, faculty, courses, faqs,
notices, events, facilities, contacts, knowledge base, chat, feedback,
unanswered questions, audit logs

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts_cols():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "college_info",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("short_code", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hod_name", sa.String(150), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "faculty_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("designation", sa.String(150), nullable=True),
        sa.Column("qualification", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("level", sa.String(50), nullable=True),
        sa.Column("duration_years", sa.Integer(), nullable=True),
        sa.Column("intake", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "faqs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts_cols(),
    )

    op.create_table(
        "notices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "facilities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("extracted_pages", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "website_import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("page_url", sa.String(500), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        *_ts_cols(),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("source_label", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="approved"),
        sa.Column("embedded", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_ts_cols(),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("answer_source", sa.String(30), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_feedback_message_id", "feedback", ["message_id"])

    op.create_table(
        "unanswered_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("times_asked", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_ts_cols(),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("unanswered_questions")
    op.drop_table("feedback")
    op.drop_table("chat_messages")
    op.drop_table("conversations")
    op.drop_table("knowledge_chunks")
    op.drop_table("website_import_batches")
    op.drop_table("uploaded_documents")
    op.drop_table("contacts")
    op.drop_table("facilities")
    op.drop_table("events")
    op.drop_table("notices")
    op.drop_table("faqs")
    op.drop_table("courses")
    op.drop_table("faculty_profiles")
    op.drop_table("departments")
    op.drop_table("college_info")

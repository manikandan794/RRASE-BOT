from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, generate_uuid


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = down / unhelpful, 5 = up / helpful
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class UnansweredQuestion(Base, TimestampMixin):
    """Populated whenever the pipeline reaches 'no reliable answer exists'.
    Reviewed by admins so the knowledge base / FAQ can be expanded."""
    __tablename__ = "unanswered_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    times_asked: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # Set by an admin/principal when triaging, so a faculty member only ever
    # sees unanswered questions routed to their own department - faculty
    # cannot self-assign this field.
    department_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

"""Structured college information - the primary source the DB-first lookup
checks before any AI generation happens."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class CollegeInfo(Base, TimestampMixin):
    """Single-row-per-key store for general college facts (address, phone,
    affiliation, accreditation, established year, etc). Admin/Principal
    managed; every value must trace back to a verified official source."""
    __tablename__ = "college_info"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)

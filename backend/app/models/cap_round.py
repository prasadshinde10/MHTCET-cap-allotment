from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from datetime import datetime
from app.models.base import Base, TimestampMixin

class CapRound(Base, TimestampMixin):
    __tablename__ = "cap_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_name: Mapped[str] = mapped_column(String(50), nullable=False)
    source_filename: Mapped[Optional[str]] = mapped_column(String(500))
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processing_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("year", "round_number", name="uix_year_round"),
    )

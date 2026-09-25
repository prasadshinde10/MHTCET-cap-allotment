from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from datetime import datetime
from app.models.base import Base


class ImportBatch(Base):
    """Tracks each PDF import operation."""
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    cap_round_id: Mapped[int] = mapped_column(
        ForeignKey("cap_rounds.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    parser_version: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

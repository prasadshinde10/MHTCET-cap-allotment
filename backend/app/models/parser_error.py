from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, Any
from datetime import datetime
from app.models.base import Base

class ParserError(Base):
    __tablename__ = "parser_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    college_code: Mapped[Optional[str]] = mapped_column(String(20))
    course_code: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    context: Mapped[Optional[Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_parser_errors_batch_status_severity", "import_batch_id", "status", "severity"),
    )

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime
from app.models.base import Base

class ManualCorrection(Base):
    __tablename__ = "manual_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    cutoff_id: Mapped[int] = mapped_column(ForeignKey("cutoffs.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    original_value: Mapped[Optional[str]] = mapped_column(Text)
    corrected_value: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

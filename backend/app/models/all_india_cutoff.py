from sqlalchemy import Integer, String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.models.base import Base

class AllIndiaCutoffRecord(Base):
    __tablename__ = "all_india_cutoff_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cap_round: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(50))
    sr_no: Mapped[Optional[int]] = mapped_column(Integer)
    merit_rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    merit_percentile: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    choice_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    college_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    college_name: Mapped[str] = mapped_column(String(500), nullable=False)
    course_name: Mapped[str] = mapped_column(String(500), nullable=False)
    merit_exam: Mapped[Optional[str]] = mapped_column(String(100))
    type: Mapped[Optional[str]] = mapped_column(String(100))
    seat_type: Mapped[Optional[str]] = mapped_column(String(100))
    source_pdf: Mapped[Optional[str]] = mapped_column(String(500))
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, server_default=func.now())

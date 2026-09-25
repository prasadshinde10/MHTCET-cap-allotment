from sqlalchemy import Integer, String, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from decimal import Decimal
from app.models.base import Base, TimestampMixin

class Cutoff(Base, TimestampMixin):
    __tablename__ = "cutoffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cap_round_id: Mapped[int] = mapped_column(ForeignKey("cap_rounds.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    import_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("import_batches.id"))
    
    seat_section: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    seat_section_raw: Mapped[Optional[str]] = mapped_column(String(200))
    category_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    seat_category: Mapped[Optional[str]] = mapped_column(String(50))
    seat_location: Mapped[Optional[str]] = mapped_column(String(50))
    stage: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    merit_number: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), index=True)
    
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    source_pdf: Mapped[Optional[str]] = mapped_column(String(500))
    source_text_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    is_manually_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    course: Mapped["Course"] = relationship("Course", back_populates="cutoffs")

    __table_args__ = (
        Index("ix_cutoffs_composite", "cap_round_id", "course_id", "category_code", "stage"),
    )

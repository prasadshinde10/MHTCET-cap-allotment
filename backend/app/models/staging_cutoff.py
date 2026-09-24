from sqlalchemy import Integer, String, Numeric, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from decimal import Decimal
from app.models.base import Base, TimestampMixin


class StagingCutoff(Base, TimestampMixin):
    """
    Staging table for cutoff records extracted from PDFs.

    Records land here first before being validated and committed
    to the production cutoffs table. Uses raw college_code/course_code
    strings rather than foreign keys — resolution to IDs happens
    during the commit phase.
    """
    __tablename__ = "staging_cutoffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    cap_round_id: Mapped[int] = mapped_column(ForeignKey("cap_rounds.id"), nullable=False)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False)

    # Raw codes from PDF — resolved to FKs during commit
    college_code: Mapped[str] = mapped_column(String(20), nullable=False)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Resolved FK — populated during commit phase
    course_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    seat_section: Mapped[str] = mapped_column(String(50), nullable=False)
    seat_section_raw: Mapped[Optional[str]] = mapped_column(String(200))
    category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    seat_category: Mapped[Optional[str]] = mapped_column(String(50))
    seat_location: Mapped[Optional[str]] = mapped_column(String(50))
    stage: Mapped[str] = mapped_column(String(10), nullable=False)

    merit_number: Mapped[Optional[int]] = mapped_column(Integer)
    percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))

    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    source_pdf: Mapped[Optional[str]] = mapped_column(String(500))
    source_text_hash: Mapped[Optional[str]] = mapped_column(String(64))

    validation_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    validation_errors: Mapped[Optional[Any]] = mapped_column(JSON)

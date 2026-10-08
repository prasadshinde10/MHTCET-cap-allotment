from sqlalchemy import Integer, String, Float, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.models.base import Base, TimestampMixin


class MedicalCollege(Base, TimestampMixin):
    __tablename__ = "medical_colleges"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    college_name: Mapped[str] = mapped_column(String(500), nullable=False)
    college_type: Mapped[str] = mapped_column(String(100), default="Government/Aided")
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100), default="Maharashtra")

    cutoffs: Mapped[List["MedicalCutoff"]] = relationship("MedicalCutoff", back_populates="college", cascade="all, delete-orphan")


class MedicalCourse(Base, TimestampMixin):
    __tablename__ = "medical_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(100), nullable=False)

    cutoffs: Mapped[List["MedicalCutoff"]] = relationship("MedicalCutoff", back_populates="course", cascade="all, delete-orphan")


class MedicalCutoff(Base, TimestampMixin):
    __tablename__ = "medical_cutoffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    round: Mapped[str] = mapped_column(String(50), default="Round 1", nullable=False, index=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("medical_colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("medical_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    quota_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    base_category: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False, index=True)
    opening_rank: Mapped[Optional[int]] = mapped_column(Integer)
    closing_rank: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    opening_score: Mapped[Optional[int]] = mapped_column(Integer)
    closing_score: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    allotted_seats: Mapped[int] = mapped_column(Integer, default=0)
    exam_name: Mapped[str] = mapped_column(String(100), default="NEET (UG)")
    counselling_type: Mapped[str] = mapped_column(String(20), default="state", index=True)

    college: Mapped["MedicalCollege"] = relationship("MedicalCollege", back_populates="cutoffs")
    course: Mapped["MedicalCourse"] = relationship("MedicalCourse", back_populates="cutoffs")

    __table_args__ = (
        UniqueConstraint("academic_year", "round", "college_id", "course_id", "quota_category", name="uq_medical_cutoff_item"),
        Index("ix_med_cutoffs_comp", "academic_year", "round", "counselling_type", "closing_rank"),
    )


class MedicalMeta(Base, TimestampMixin):
    __tablename__ = "medical_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_files: Mapped[str] = mapped_column(String(255), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(500))


class MedicalImportBatch(Base, TimestampMixin):
    __tablename__ = "medical_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_type: Mapped[str] = mapped_column(String(50), default="auto")
    academic_year: Mapped[Optional[str]] = mapped_column(String(50))
    round_name: Mapped[Optional[str]] = mapped_column(String(50))
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="PROCESSING", index=True)
    current_action: Mapped[Optional[str]] = mapped_column(String(255))
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from app.models.base import Base, TimestampMixin

class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False)
    course_name: Mapped[str] = mapped_column(String(500), nullable=False)

    college: Mapped["College"] = relationship("College", back_populates="courses")
    cutoffs: Mapped[List["Cutoff"]] = relationship("Cutoff", back_populates="course")

    __table_args__ = (
        UniqueConstraint("college_id", "course_code", name="uix_college_course"),
    )

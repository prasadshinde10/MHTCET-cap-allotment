from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.models.base import Base, TimestampMixin

class College(Base, TimestampMixin):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    college_name: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(200))
    district: Mapped[Optional[str]] = mapped_column(String(200))
    college_type: Mapped[str] = mapped_column(String(20), default="Unknown")
    funding_type: Mapped[str] = mapped_column(String(20), default="Unknown")
    minority_status: Mapped[str] = mapped_column(String(20), default="Unknown")
    minority_type: Mapped[Optional[str]] = mapped_column(String(200))
    home_university: Mapped[Optional[str]] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="Active")

    courses: Mapped[List["Course"]] = relationship("Course", back_populates="college")

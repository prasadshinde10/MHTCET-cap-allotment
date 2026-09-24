from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.courses import CourseListItem

class CollegeUpdate(BaseModel):
    city: Optional[str] = None
    district: Optional[str] = None
    college_type: Optional[str] = None
    funding_type: Optional[str] = None
    minority_status: Optional[str] = None
    minority_type: Optional[str] = None
    home_university: Optional[str] = None
    status: Optional[str] = None

class CollegeListItem(BaseModel):
    id: int
    college_code: str
    college_name: str
    city: Optional[str]
    district: Optional[str]
    college_type: Optional[str]
    funding_type: Optional[str]
    minority_status: Optional[str]
    minority_type: Optional[str]
    home_university: Optional[str]
    status: str
    course_count: int

    model_config = ConfigDict(from_attributes=True)

class CollegeDetail(CollegeListItem):
    courses: List[CourseListItem] = []

    model_config = ConfigDict(from_attributes=True)

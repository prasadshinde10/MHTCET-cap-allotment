from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict

class CourseUpdate(BaseModel):
    course_name: Optional[str] = None

class CourseListItem(BaseModel):
    id: int
    college_id: int
    course_code: str
    course_name: str
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    cutoff_count: int

    model_config = ConfigDict(from_attributes=True)

class CourseDetail(CourseListItem):
    cutoffs_per_round: Dict[int, int] = {}

    model_config = ConfigDict(from_attributes=True)

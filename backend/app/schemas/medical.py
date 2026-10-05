from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class MedicalCollegeItem(BaseModel):
    id: int
    college_code: str
    college_name: str
    college_type: Optional[str] = "Government/Aided"
    city: Optional[str] = None
    state: Optional[str] = "Maharashtra"


class MedicalCourseItem(BaseModel):
    id: int
    course_code: str
    course_name: str
    degree_type: str


class MedicalFilterOptions(BaseModel):
    academic_years: List[str]
    rounds: List[str]
    colleges: List[MedicalCollegeItem]
    courses: List[MedicalCourseItem]
    college_types: List[str]
    categories: List[str]
    quotas: List[str]


class MedicalCutoffItem(BaseModel):
    id: int
    academic_year: str
    round: str
    quota_category: str
    base_category: str
    opening_rank: Optional[int] = None
    closing_rank: Optional[int] = None
    opening_score: Optional[int] = None
    closing_score: Optional[int] = None
    allotted_seats: int = 0
    exam_name: str = "NEET (UG)"
    chance: Optional[str] = None
    college_id: int
    college_code: str
    college_name: str
    college_type: Optional[str] = "Government/Aided"
    city: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    course_id: int
    course_code: str
    course_name: str
    degree_type: str


class MedicalPaginatedResponse(BaseModel):
    items: List[MedicalCutoffItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class MedicalDbStats(BaseModel):
    cutoff_count: int
    college_count: int
    course_count: int
    years: List[str]
    college_types: Dict[str, int]
    courses_breakdown: Dict[str, int]

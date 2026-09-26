from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any

class RoundComparisonItem(BaseModel):
    course_code: str
    course_name: str
    college_name: str
    category_code: str
    seat_section: str
    stage: str
    round_a_merit: Optional[int] = None
    round_a_percentile: Optional[float] = None
    round_b_merit: Optional[int] = None
    round_b_percentile: Optional[float] = None
    percentile_change: Optional[float] = None

class DataQualityReport(BaseModel):
    total_records: int
    records_with_missing_merit: int
    records_with_missing_percentile: int
    records_with_zero_merit: int
    duplicate_count: int
    records_by_validation_status: Dict[str, int]
    category_distribution: Dict[str, int]
    section_distribution: Dict[str, int]

class CategorySummary(BaseModel):
    category_code: str
    count: int

class CollegeOption(BaseModel):
    college_code: str
    college_name: str
    city: Optional[str] = None
    district: Optional[str] = None
    college_type: Optional[str] = None
    funding_type: Optional[str] = None

class CourseOption(BaseModel):
    course_code: str
    course_name: str

class FilterOptions(BaseModel):
    years: List[int]
    rounds: List[int]
    categories: List[str]
    seat_sections: List[str]
    stages: List[str]
    cities_districts: List[str]
    colleges: List[CollegeOption]
    courses: List[CourseOption]

class CutoffSummary(BaseModel):
    total_matches: int
    min_percentile: Optional[float] = None
    max_percentile: Optional[float] = None
    avg_percentile: Optional[float] = None
    min_merit: Optional[int] = None
    max_merit: Optional[int] = None
    unique_colleges: int = 0
    unique_courses: int = 0


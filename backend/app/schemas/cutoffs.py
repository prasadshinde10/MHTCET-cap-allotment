from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class CutoffUpdate(BaseModel):
    merit_number: Optional[int] = None
    percentile: Optional[float] = None
    category_code: Optional[str] = None
    seat_section: Optional[str] = None
    stage: Optional[str] = None
    reason: str

class CutoffFilters(BaseModel):
    year: Optional[int] = None
    round_number: Optional[int] = None
    cap_round_id: Optional[int] = None
    college: Optional[str] = None
    college_code: Optional[str] = None
    course: Optional[str] = None
    course_code: Optional[str] = None
    category_code: Optional[str] = None
    gender: Optional[str] = None
    city_district: Optional[str] = None
    seat_section: Optional[str] = None
    stage: Optional[str] = None
    min_percentile: Optional[float] = None
    max_percentile: Optional[float] = None
    min_merit: Optional[int] = None
    max_merit: Optional[int] = None
    sort_by: Optional[str] = None
    is_deleted: Optional[bool] = None

class CutoffListItem(BaseModel):
    id: int
    year: int
    cap_round_id: int
    course_id: int
    seat_section: str
    category_code: str
    gender: Optional[str] = None
    seat_category: Optional[str] = None
    seat_location: Optional[str] = None
    stage: str
    merit_number: Optional[int] = None
    percentile: Optional[float] = None
    source_page: Optional[int] = None
    source_pdf: Optional[str] = None
    is_manually_corrected: bool = False
    is_deleted: bool = False
    college_code: Optional[str] = None
    college_name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    round_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ManualCorrectionItem(BaseModel):
    id: int
    field_name: str
    old_value: str
    new_value: str
    corrected_by: str
    reason: str
    
    model_config = ConfigDict(from_attributes=True)

class CutoffDetail(CutoffListItem):
    import_batch_id: int
    source_pdf: Optional[str]
    manual_corrections: List[ManualCorrectionItem] = []

    model_config = ConfigDict(from_attributes=True)

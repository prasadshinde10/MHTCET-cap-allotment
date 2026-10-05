from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class BitsCampusItem(BaseModel):
    id: int
    campus_code: str
    campus_name: str
    location: Optional[str] = None
    state: Optional[str] = None


class BitsProgramItem(BaseModel):
    id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: str


class BitsFilterOptions(BaseModel):
    academic_years: List[str]
    campuses: List[BitsCampusItem]
    programs: List[BitsProgramItem]
    degree_types: List[str]
    categories: List[str]


class BitsCutoffItem(BaseModel):
    id: int
    academic_year: str
    cutoff_score: int
    max_marks: int
    score_percentage: Optional[float] = None
    category: str = "General Merit"
    exam_name: str = "BITSAT"
    campus_id: int
    campus_code: str
    campus_name: str
    campus_location: Optional[str] = None
    campus_state: Optional[str] = None
    program_id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: str


class BitsPaginatedResponse(BaseModel):
    items: List[BitsCutoffItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class BitsDbStats(BaseModel):
    total_cutoffs: int
    total_campuses: int
    total_programs: int
    available_years: List[str]
    last_scraped_at: Optional[str] = None


class BitsScraperStatus(BaseModel):
    is_running: bool
    status: str  # IDLE, RUNNING, COMPLETED, FAILED
    progress_percent: int
    message: str
    records_count: int
    years_count: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

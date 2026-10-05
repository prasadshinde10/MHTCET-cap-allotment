from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class IiserInstituteItem(BaseModel):
    id: int
    institute_code: Optional[str] = None
    institute_name: str
    state: Optional[str] = None


class IiserProgramItem(BaseModel):
    id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: str


class IiserCategoryItem(BaseModel):
    id: int
    category_code: str
    category_name: str
    is_pwd: bool = False


class IiserFilterOptions(BaseModel):
    rounds: List[int]
    years: List[int]
    institutes: List[IiserInstituteItem]
    programs: List[IiserProgramItem]
    degree_types: List[str]
    categories: List[IiserCategoryItem]
    states: List[str]


class IiserCutoffItem(BaseModel):
    id: int
    academic_year: int
    round_no: int
    raw_program_name: str
    closing_rank: int
    seat_pool: str = "Gender-Neutral"
    allocation_channel: str = "IAT"
    institute_id: int
    institute_code: Optional[str] = None
    institute_name: str
    institute_state: Optional[str] = None
    program_id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: str
    category_id: int
    category_code: str
    category_name: str
    is_pwd: bool = False


class IiserPaginatedResponse(BaseModel):
    items: List[IiserCutoffItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class IiserRoundNoticeItem(BaseModel):
    id: int
    academic_year: int
    round_no: int
    notice_text: str
    created_at: Optional[str] = None


class IiserDbStats(BaseModel):
    total_cutoffs: int
    total_institutes: int
    total_programs: int
    total_categories: int
    total_rounds: int
    total_notices: int
    last_scraped_at: Optional[str] = None


class IiserScraperStatus(BaseModel):
    is_running: bool
    status: str  # IDLE, RUNNING, COMPLETED, FAILED
    progress_percent: int
    current_round: Optional[int] = None
    message: str
    records_count: int
    total_rounds: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

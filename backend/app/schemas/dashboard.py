from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class RecentImport(BaseModel):
    filename: str
    round_name: str
    year: int
    status: str
    records: int
    date: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecentError(BaseModel):
    page: Optional[int] = None
    error: str
    severity: str
    status: str

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_colleges: int
    total_courses: int
    total_cutoffs: int
    rounds_processed: int
    total_imports: int
    successful_imports: int
    warning_imports: int
    failed_imports: int
    open_parser_errors: int
    cap_round_1_records: int
    cap_round_2_records: int
    cap_round_3_records: int
    cap_round_4_records: int
    recent_imports: List[RecentImport]
    recent_errors: List[RecentError]

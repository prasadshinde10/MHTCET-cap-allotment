from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class CapRoundBase(BaseModel):
    round_name: Optional[str] = None

class CapRoundUpdate(CapRoundBase):
    pass

class CapRoundListItem(BaseModel):
    id: int
    year: int
    round_number: int
    round_name: str
    processing_status: str
    total_pages: Optional[int]
    total_records: int
    error_count: int
    uploaded_at: datetime
    processed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class CapRoundStats(BaseModel):
    total_cutoffs: int
    total_colleges: int
    total_courses: int
    cutoffs_by_category: dict
    cutoffs_by_section: dict
    top_colleges: list

class CapRoundDetail(CapRoundListItem):
    stats: Optional[CapRoundStats] = None

    model_config = ConfigDict(from_attributes=True)

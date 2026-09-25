from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class UploadResponse(BaseModel):
    import_batch_id: int
    cap_round_id: int
    filename: str
    file_hash: str
    message: str

class ImportLogItem(BaseModel):
    id: int
    level: str
    message: str
    page_number: int | None = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ImportBatchListItem(BaseModel):
    id: int
    cap_round_id: int
    round_name: str | None = None
    year: int | None = None
    round_number: int | None = None
    filename: str
    status: str
    pages_processed: int
    records_created: int
    records_rejected: int
    warning_count: int
    error_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

class ImportBatchDetail(ImportBatchListItem):
    file_hash: str
    file_path: str | None = None
    parser_version: str
    summary: dict | None = None
    recent_logs: list[ImportLogItem] = []
    error_summary: dict = {}

class StagingCutoffItem(BaseModel):
    id: int
    college_code: str
    course_code: str
    seat_section: str | None = None
    category_code: str | None = None
    stage: str | None = None
    merit_number: int | None = None
    percentile: float | None = None
    source_page: int | None = None
    validation_status: str | None = None

    model_config = {"from_attributes": True}

class CommitResponse(BaseModel):
    records_committed: int
    colleges_created: int
    courses_created: int
    message: str

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

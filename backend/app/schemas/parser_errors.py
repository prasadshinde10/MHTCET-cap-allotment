from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime

class ParserErrorUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

class ParserErrorListItem(BaseModel):
    id: int
    import_batch_id: int
    source_page: int
    error_type: str
    severity: str
    raw_text: Optional[str]
    error_message: str
    college_code: Optional[str]
    course_code: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ParserErrorDetail(ParserErrorListItem):
    context: Optional[Any]

    model_config = ConfigDict(from_attributes=True)

class ParserErrorSummary(BaseModel):
    by_severity: dict
    by_type: dict
    by_batch: dict

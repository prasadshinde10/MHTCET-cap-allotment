from pydantic import BaseModel
from typing import List, Optional

class JosaaInstituteItem(BaseModel):
    id: int
    institute_code: Optional[str] = None
    institute_name: str
    institute_type: str
    state: Optional[str] = None

class JosaaProgramItem(BaseModel):
    id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: Optional[str] = None

class JosaaCategoryItem(BaseModel):
    id: int
    category_code: str
    category_name: Optional[str] = None

class JosaaFilterOptions(BaseModel):
    rounds: List[int]
    years: List[int]
    institute_types: List[str]
    institutes: List[JosaaInstituteItem]
    programs: List[JosaaProgramItem]
    categories: List[JosaaCategoryItem]
    quotas: List[str]
    genders: List[str]
    states: List[str] = []

class JosaaCutoffItem(BaseModel):
    id: int
    academic_year: int
    round_no: int
    quota: str
    gender: str
    opening_rank: int
    closing_rank: int
    is_preparatory: bool = False
    institute_id: int
    institute_code: Optional[str] = None
    institute_name: str
    institute_type: str
    institute_state: Optional[str] = None
    program_id: int
    program_code: Optional[str] = None
    program_name: str
    degree_type: Optional[str] = None
    category_id: int
    category_code: str
    category_name: Optional[str] = None

class JosaaPaginatedResponse(BaseModel):
    items: List[JosaaCutoffItem]
    total: int
    page: int
    page_size: int
    total_pages: int

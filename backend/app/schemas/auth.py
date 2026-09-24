from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class AdminResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

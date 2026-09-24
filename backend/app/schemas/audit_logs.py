from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime

class AuditLogItem(BaseModel):
  id: int
  action: str
  entity_type: Optional[str] = None
  entity_id: Optional[Any] = None
  details: Optional[Any] = None
  ip_address: Optional[str] = None
  created_at: datetime

  model_config = ConfigDict(from_attributes=True)

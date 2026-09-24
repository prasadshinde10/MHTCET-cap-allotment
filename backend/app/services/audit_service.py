from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Any, Dict, Optional

def log_audit(db: Session, action: str, entity_type: Optional[str] = None, entity_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None):
    audit = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()

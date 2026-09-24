from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import AuditLog
from app.schemas.audit_logs import AuditLogItem

from app.schemas.common import PaginatedResponse, PaginationParams
from sqlalchemy import func

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[AuditLogItem])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    skip = (page - 1) * page_size
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at))
    count_stmt = select(func.count(AuditLog.id))
    
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
        
    total = db.scalar(count_stmt) or 0
    stmt = stmt.offset(skip).limit(page_size)
    logs = db.execute(stmt).scalars().all()
    
    items = [AuditLogItem.model_validate(log) for log in logs]
    return PaginatedResponse.create(items=items, total=total, params=PaginationParams(page=page, page_size=page_size))

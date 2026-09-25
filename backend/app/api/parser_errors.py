from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from typing import List, Optional

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import ParserError
from app.schemas.parser_errors import ParserErrorListItem, ParserErrorDetail, ParserErrorUpdate, ParserErrorSummary
from app.services.audit_service import log_audit

from app.schemas.common import PaginatedResponse, PaginationParams

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[ParserErrorListItem])
def list_parser_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    import_batch_id: Optional[int] = None,
    severity: Optional[str] = None,
    error_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    skip = (page - 1) * page_size
    stmt = select(ParserError).order_by(desc(ParserError.id))
    count_stmt = select(func.count(ParserError.id))
    
    if import_batch_id:
        stmt = stmt.where(ParserError.import_batch_id == import_batch_id)
        count_stmt = count_stmt.where(ParserError.import_batch_id == import_batch_id)
    if severity:
        stmt = stmt.where(ParserError.severity == severity)
        count_stmt = count_stmt.where(ParserError.severity == severity)
    if error_type:
        stmt = stmt.where(ParserError.error_type == error_type)
        count_stmt = count_stmt.where(ParserError.error_type == error_type)
    if status:
        stmt = stmt.where(ParserError.status == status)
        count_stmt = count_stmt.where(ParserError.status == status)
        
    total = db.scalar(count_stmt) or 0
    stmt = stmt.offset(skip).limit(page_size)
    errors = db.execute(stmt).scalars().all()
    
    # Truncate raw_text
    items = []
    for e in errors:
        raw = e.raw_text
        if raw and len(raw) > 200:
            raw = raw[:197] + "..."
        e_item = ParserErrorListItem.model_validate(e)
        e_item.raw_text = raw
        items.append(e_item)
            
    return PaginatedResponse.create(items=items, total=total, params=PaginationParams(page=page, page_size=page_size))

@router.get("/summary", response_model=ParserErrorSummary)
def error_summary(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # by severity
    sev_stmt = select(ParserError.severity, func.count(ParserError.id)).group_by(ParserError.severity)
    by_severity = {row[0]: row[1] for row in db.execute(sev_stmt).all() if row[0]}
    
    # by type
    type_stmt = select(ParserError.error_type, func.count(ParserError.id)).group_by(ParserError.error_type)
    by_type = {row[0]: row[1] for row in db.execute(type_stmt).all() if row[0]}
    
    # by batch
    batch_stmt = select(ParserError.import_batch_id, func.count(ParserError.id)).group_by(ParserError.import_batch_id)
    by_batch = {str(row[0]): row[1] for row in db.execute(batch_stmt).all() if row[0]}
    
    return ParserErrorSummary(
        by_severity=by_severity,
        by_type=by_type,
        by_batch=by_batch
    )

@router.get("/{error_id}", response_model=ParserErrorDetail)
def get_parser_error(
    error_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    error = db.execute(select(ParserError).where(ParserError.id == error_id)).scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")
    return error

@router.put("/{error_id}", response_model=ParserErrorListItem)
def update_parser_error(
    error_id: int,
    update_data: ParserErrorUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    error = db.execute(select(ParserError).where(ParserError.id == error_id)).scalar_one_or_none()
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")
        
    error.status = update_data.status
    # resolution_notes is not in the model but let's say it's updated in context or we just log it
    if update_data.resolution_notes:
        if not error.context:
            error.context = {}
        # assuming context is a dict or json
        if isinstance(error.context, dict):
            error.context['resolution_notes'] = update_data.resolution_notes
        else:
            # Maybe it's a string or other, replace it with dict if possible
            error.context = {"resolution_notes": update_data.resolution_notes}
            
    db.commit()
    db.refresh(error)
    log_audit(db, "UPDATE", "parser_error", str(error.id), {"status": update_data.status})
    
    if error.raw_text and len(error.raw_text) > 200:
        error.raw_text = error.raw_text[:197] + "..."
        
    return error

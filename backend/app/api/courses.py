from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import Course, College, Cutoff
from app.schemas.courses import CourseListItem, CourseDetail, CourseUpdate
from app.services.audit_service import log_audit

from app.schemas.common import PaginatedResponse, PaginationParams

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[CourseListItem])
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    college_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    skip = (page - 1) * page_size
    stmt = select(Course, College.college_name, College.college_code, func.count(Cutoff.id).label('cutoff_count'))\
        .join(College, College.id == Course.college_id)\
        .outerjoin(Cutoff, Cutoff.course_id == Course.id)
    count_stmt = select(func.count(Course.id)).join(College, College.id == Course.college_id)
    
    if search:
        condition = or_(Course.course_name.ilike(f"%{search}%"), Course.course_code.ilike(f"%{search}%"))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if college_id:
        stmt = stmt.where(Course.college_id == college_id)
        count_stmt = count_stmt.where(Course.college_id == college_id)
        
    total = db.scalar(count_stmt) or 0
    stmt = stmt.group_by(Course.id, College.id).offset(skip).limit(page_size)
    results = db.execute(stmt).all()
    
    items = []
    for course, college_name, college_code, cutoff_count in results:
        course_dict = {c.name: getattr(course, c.name) for c in course.__table__.columns}
        course_dict['college_name'] = college_name
        course_dict['college_code'] = college_code
        course_dict['cutoff_count'] = cutoff_count
        items.append(CourseListItem(**course_dict))

    return PaginatedResponse.create(items=items, total=total, params=PaginationParams(page=page, page_size=page_size))

@router.get("/{course_id}", response_model=CourseDetail)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Course, College.college_name, College.college_code, func.count(Cutoff.id).label('cutoff_count'))\
        .join(College, College.id == Course.college_id)\
        .outerjoin(Cutoff, Cutoff.course_id == Course.id)\
        .where(Course.id == course_id)\
        .group_by(Course.id, College.id)
        
    result = db.execute(stmt).first()
    if not result:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course, college_name, college_code, cutoff_count = result
    
    # Get cutoff counts per round
    round_stmt = select(Cutoff.cap_round_id, func.count(Cutoff.id))\
        .where(Cutoff.course_id == course_id)\
        .group_by(Cutoff.cap_round_id)
    round_results = db.execute(round_stmt).all()
    cutoffs_per_round = {row[0]: row[1] for row in round_results if row[0]}
    
    course_dict = {c.name: getattr(course, c.name) for c in course.__table__.columns}
    course_dict['college_name'] = college_name
    course_dict['college_code'] = college_code
    course_dict['cutoff_count'] = cutoff_count
    course_dict['cutoffs_per_round'] = cutoffs_per_round
    
    return CourseDetail(**course_dict)

@router.put("/{course_id}")
def update_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Enforce PDF source of truth: manual course modification is disabled."""
    raise HTTPException(
        status_code=403, 
        detail="Manual course modification is disabled. Courses are automatically parsed from CAP Round PDFs."
    )

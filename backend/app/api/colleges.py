from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, or_
from typing import List, Optional

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import College, Course, Cutoff
from app.schemas.colleges import CollegeListItem, CollegeDetail, CollegeUpdate
from app.schemas.courses import CourseListItem
from app.services.audit_service import log_audit

from app.schemas.common import PaginatedResponse, PaginationParams

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[CollegeListItem])
def list_colleges(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    college_type: Optional[str] = None,
    funding_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    skip = (page - 1) * page_size
    stmt = select(College, func.count(Course.id).label('course_count')).outerjoin(Course, Course.college_id == College.id)
    count_stmt = select(func.count(College.id))
    
    if search:
        condition = or_(College.college_name.ilike(f"%{search}%"), College.college_code.ilike(f"%{search}%"))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if status:
        stmt = stmt.where(College.status == status)
        count_stmt = count_stmt.where(College.status == status)
    if college_type:
        stmt = stmt.where(College.college_type == college_type)
        count_stmt = count_stmt.where(College.college_type == college_type)
    if funding_type:
        stmt = stmt.where(College.funding_type == funding_type)
        count_stmt = count_stmt.where(College.funding_type == funding_type)
        
    total = db.scalar(count_stmt) or 0
    stmt = stmt.group_by(College.id).offset(skip).limit(page_size)
    results = db.execute(stmt).all()
    
    items = []
    for college, course_count in results:
        college_dict = {c.name: getattr(college, c.name) for c in college.__table__.columns}
        college_dict['course_count'] = course_count
        items.append(CollegeListItem(**college_dict))

    return PaginatedResponse.create(items=items, total=total, params=PaginationParams(page=page, page_size=page_size))

@router.get("/{college_id}", response_model=CollegeDetail)
def get_college(
    college_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(College, func.count(Course.id).label('course_count')).outerjoin(Course, Course.college_id == College.id).where(College.id == college_id).group_by(College.id)
    result = db.execute(stmt).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="College not found")
    
    college, course_count = result
    
    courses_stmt = select(Course, func.count(Cutoff.id).label('cutoff_count')).outerjoin(Cutoff, Cutoff.course_id == Course.id).where(Course.college_id == college_id).group_by(Course.id)
    courses_result = db.execute(courses_stmt).all()
    
    courses_list = []
    for course, cutoff_count in courses_result:
        course_dict = {c.name: getattr(course, c.name) for c in course.__table__.columns}
        course_dict['cutoff_count'] = cutoff_count
        course_dict['college_name'] = college.college_name
        course_dict['college_code'] = college.college_code
        courses_list.append(CourseListItem(**course_dict))
        
    college_dict = {c.name: getattr(college, c.name) for c in college.__table__.columns}
    college_dict['course_count'] = course_count
    college_dict['courses'] = courses_list
    
    return CollegeDetail(**college_dict)

@router.put("/{college_id}")
def update_college(
    college_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Enforce PDF source of truth: manual college modification is disabled."""
    raise HTTPException(
        status_code=403, 
        detail="Manual college modification is disabled. Colleges are automatically parsed from CAP Round PDFs."
    )

@router.get("/{college_id}/courses", response_model=List[CourseListItem])
def list_college_courses(
    college_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    college = db.execute(select(College).where(College.id == college_id)).scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
        
    courses_stmt = select(Course, func.count(Cutoff.id).label('cutoff_count')).outerjoin(Cutoff, Cutoff.course_id == Course.id).where(Course.college_id == college_id).group_by(Course.id)
    courses_result = db.execute(courses_stmt).all()
    
    courses_list = []
    for course, cutoff_count in courses_result:
        course_dict = {c.name: getattr(course, c.name) for c in course.__table__.columns}
        course_dict['cutoff_count'] = cutoff_count
        course_dict['college_name'] = college.college_name
        course_dict['college_code'] = college.college_code
        courses_list.append(CourseListItem(**course_dict))
        
    return courses_list

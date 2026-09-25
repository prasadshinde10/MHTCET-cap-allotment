from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from typing import List

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import CapRound, Cutoff, College, Course
from app.schemas.cap_rounds import CapRoundListItem, CapRoundDetail, CapRoundUpdate, CapRoundStats
from app.services.audit_service import log_audit

router = APIRouter()

@router.get("/", response_model=List[CapRoundListItem])
def list_cap_rounds(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(CapRound).order_by(desc(CapRound.year), desc(CapRound.round_number)).offset(skip).limit(limit)
    rounds = db.execute(stmt).scalars().all()
    return rounds

@router.get("/{round_id}", response_model=CapRoundDetail)
def get_cap_round(
    round_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(CapRound).where(CapRound.id == round_id)
    cap_round = db.execute(stmt).scalar_one_or_none()
    if not cap_round:
        raise HTTPException(status_code=404, detail="Cap round not found")
    
    total_cutoffs = db.execute(select(func.count(Cutoff.id)).where(Cutoff.cap_round_id == round_id)).scalar() or 0
    total_courses = db.execute(
        select(func.count(func.distinct(Cutoff.course_id))).where(Cutoff.cap_round_id == round_id)
    ).scalar() or 0
    
    # Getting total colleges by joining course to cutoff
    stmt_colleges = select(func.count(func.distinct(Course.college_id))).join(Cutoff, Cutoff.course_id == Course.id).where(Cutoff.cap_round_id == round_id)
    total_colleges = db.execute(stmt_colleges).scalar() or 0

    stats = CapRoundStats(
        total_cutoffs=total_cutoffs,
        total_colleges=total_colleges,
        total_courses=total_courses,
        cutoffs_by_category={}, # basic mock
        cutoffs_by_section={},  # basic mock
        top_colleges=[]
    )
    
    response = CapRoundDetail.model_validate(cap_round)
    response.stats = stats
    return response

@router.put("/{round_id}", response_model=CapRoundListItem)
def update_cap_round(
    round_id: int,
    update_data: CapRoundUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(CapRound).where(CapRound.id == round_id)
    cap_round = db.execute(stmt).scalar_one_or_none()
    if not cap_round:
        raise HTTPException(status_code=404, detail="Cap round not found")
    
    if update_data.round_name is not None:
        cap_round.round_name = update_data.round_name
        
    db.commit()
    db.refresh(cap_round)
    log_audit(db, "UPDATE", "cap_round", str(cap_round.id), {"round_name": update_data.round_name})
    
    return cap_round

@router.get("/{round_id}/stats", response_model=CapRoundStats)
def get_cap_round_stats(
    round_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # Cutoffs by category
    cat_stmt = select(Cutoff.category_code, func.count(Cutoff.id)).where(Cutoff.cap_round_id == round_id).group_by(Cutoff.category_code)
    cat_res = db.execute(cat_stmt).all()
    cutoffs_by_category = {row[0]: row[1] for row in cat_res if row[0]}
    
    # Cutoffs by section
    sec_stmt = select(Cutoff.seat_section, func.count(Cutoff.id)).where(Cutoff.cap_round_id == round_id).group_by(Cutoff.seat_section)
    sec_res = db.execute(sec_stmt).all()
    cutoffs_by_section = {row[0]: row[1] for row in sec_res if row[0]}
    
    total_cutoffs = db.execute(select(func.count(Cutoff.id)).where(Cutoff.cap_round_id == round_id)).scalar() or 0
    total_courses = db.execute(
        select(func.count(func.distinct(Cutoff.course_id))).where(Cutoff.cap_round_id == round_id)
    ).scalar() or 0
    stmt_colleges = select(func.count(func.distinct(Course.college_id))).join(Cutoff, Cutoff.course_id == Course.id).where(Cutoff.cap_round_id == round_id)
    total_colleges = db.execute(stmt_colleges).scalar() or 0

    return CapRoundStats(
        total_cutoffs=total_cutoffs,
        total_colleges=total_colleges,
        total_courses=total_courses,
        cutoffs_by_category=cutoffs_by_category,
        cutoffs_by_section=cutoffs_by_section,
        top_colleges=[]
    )

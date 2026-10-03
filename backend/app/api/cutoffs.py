from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, asc, func, or_, and_, not_
from typing import List, Optional
import io
import csv
import math
import re

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import Cutoff, College, Course, CapRound, ManualCorrection
from app.schemas.cutoffs import CutoffListItem, CutoffDetail, CutoffUpdate, ManualCorrectionItem
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.audit_service import log_audit

router = APIRouter()

def get_cutoff_query(
    db: Session,
    year: Optional[int] = None,
    round_number: Optional[str] = None,
    cap_round_id: Optional[int] = None,
    college: Optional[str] = None,
    college_code: Optional[str] = None,
    course: Optional[str] = None,
    course_code: Optional[str] = None,
    category_code: Optional[str] = None,
    gender: Optional[str] = None,
    city_district: Optional[str] = None,
    seat_section: Optional[str] = None,
    stage: Optional[str] = None,
    min_percentile: Optional[float] = None,
    max_percentile: Optional[float] = None,
    min_merit: Optional[int] = None,
    max_merit: Optional[int] = None,
    is_deleted: Optional[bool] = False,
    quota_group: Optional[str] = None,
    college_type: Optional[str] = None,
    funding_type: Optional[str] = None
):
    stmt = select(Cutoff, College, Course, CapRound)\
        .join(Course, Course.id == Cutoff.course_id)\
        .join(College, College.id == Course.college_id)\
        .join(CapRound, CapRound.id == Cutoff.cap_round_id)

    if quota_group:
        qg = quota_group.strip().upper()
        if qg in ['ALL_INDIA', 'AI', 'ALLINDIA']:
            stmt = stmt.where(Cutoff.seat_section == 'All India Seats (AI)')
        elif qg in ['STATE', 'MH', 'MHT_CET', 'MAHARASHTRA']:
            stmt = stmt.where(Cutoff.seat_section != 'All India Seats (AI)')
        
    if year is not None:
        stmt = stmt.where(Cutoff.year == year)
    if round_number is not None:
        round_str = str(round_number).strip()
        round_nums = [int(r.strip()) for r in round_str.split(',') if r.strip().isdigit()]
        if len(round_nums) == 1:
            stmt = stmt.where(CapRound.round_number == round_nums[0])
        elif len(round_nums) > 1:
            stmt = stmt.where(CapRound.round_number.in_(round_nums))
    if cap_round_id is not None:
        stmt = stmt.where(Cutoff.cap_round_id == cap_round_id)
        
    college_param = college_code or college
    if college_param:
        college_items = [c.strip() for c in college_param.split(',') if c.strip()]
        dte_codes = [c for c in college_items if re.match(r'^\d{4,5}[A-Za-z]?$', c)]
        name_queries = [c for c in college_items if not re.match(r'^\d{4,5}[A-Za-z]?$', c)]

        conds = []
        if dte_codes:
            if len(dte_codes) == 1:
                conds.append(College.college_code == dte_codes[0])
            else:
                conds.append(College.college_code.in_(dte_codes))
        for nq in name_queries:
            conds.append(
                or_(
                    College.college_code == nq,
                    College.college_name.ilike(f"%{nq}%")
                )
            )
        if conds:
            stmt = stmt.where(or_(*conds))

    if course:
        course_items = [c.strip() for c in course.split(',') if c.strip()]
        if len(course_items) == 1:
            c_val = course_items[0]
            stmt = stmt.where(
                or_(
                    Course.course_code.ilike(f"%{c_val}%"),
                    Course.course_name.ilike(f"%{c_val}%")
                )
            )
        elif len(course_items) > 1:
            course_conditions = [
                or_(
                    Course.course_code.ilike(f"%{c_val}%"),
                    Course.course_name.ilike(f"%{c_val}%")
                )
                for c_val in course_items
            ]
            stmt = stmt.where(or_(*course_conditions))
    elif course_code:
        stmt = stmt.where(Course.course_code == course_code)

    cat_handled_gender = False
    if category_code:
        cat_items = [c.strip() for c in category_code.split(',') if c.strip()]
        if len(cat_items) == 1:
            cat = cat_items[0]
            cat_upper = cat.upper()
            if '%' in cat:
                pat = cat if cat.endswith('%') else f"{cat}%"
                stmt = stmt.where(Cutoff.category_code.ilike(pat))
            elif cat_upper in ['OPEN', 'OBC', 'SC', 'ST', 'VJ', 'NT1', 'NT2', 'NT3', 'SEBC']:
                # Bare caste category passed without gender prefix
                if gender and gender.strip().lower() in ['ladies', 'l', 'female']:
                    stmt = stmt.where(Cutoff.category_code.ilike(f"L{cat_upper}%"))
                    cat_handled_gender = True
                elif gender and gender.strip().lower() in ['general', 'g', 'male']:
                    stmt = stmt.where(Cutoff.category_code.ilike(f"G{cat_upper}%"))
                    cat_handled_gender = True
                else:
                    stmt = stmt.where(
                        or_(
                            Cutoff.category_code.ilike(f"G{cat_upper}%"),
                            Cutoff.category_code.ilike(f"L{cat_upper}%")
                        )
                    )
            else:
                stmt = stmt.where(Cutoff.category_code.ilike(f"{cat}%"))
        elif len(cat_items) > 1:
            cat_conds = []
            for cat in cat_items:
                cat_upper = cat.upper()
                if '%' in cat:
                    pat = cat if cat.endswith('%') else f"{cat}%"
                    cat_conds.append(Cutoff.category_code.ilike(pat))
                elif cat_upper in ['OPEN', 'OBC', 'SC', 'ST', 'VJ', 'NT1', 'NT2', 'NT3', 'SEBC']:
                    cat_conds.append(
                        or_(
                            Cutoff.category_code.ilike(f"G{cat_upper}%"),
                            Cutoff.category_code.ilike(f"L{cat_upper}%")
                        )
                    )
                else:
                    cat_conds.append(Cutoff.category_code.ilike(f"{cat}%"))
            stmt = stmt.where(or_(*cat_conds))
            cat_handled_gender = True

    if gender and not cat_handled_gender:
        g = gender.strip().lower()
        if g in ['general', 'g', 'male']:
            stmt = stmt.where(Cutoff.category_code.like('G%'))
        elif g in ['ladies', 'l', 'female']:
            stmt = stmt.where(
                or_(
                    Cutoff.gender.ilike('Ladies'),
                    Cutoff.gender == 'L',
                    Cutoff.category_code.like('L%')
                )
            )

    if city_district:
        dist_items = [d.strip() for d in city_district.split(',') if d.strip()]
        if len(dist_items) == 1:
            cd = dist_items[0]
            stmt = stmt.where(
                or_(
                    College.city.ilike(f"%{cd}%"),
                    College.district.ilike(f"%{cd}%"),
                    College.college_name.ilike(f"%{cd}%")
                )
            )
        elif len(dist_items) > 1:
            dist_conditions = [
                or_(
                    College.city.ilike(f"%{cd}%"),
                    College.district.ilike(f"%{cd}%"),
                    College.college_name.ilike(f"%{cd}%")
                )
                for cd in dist_items
            ]
            stmt = stmt.where(or_(*dist_conditions))

    if seat_section:
        stmt = stmt.where(Cutoff.seat_section == seat_section)
    if stage:
        stmt = stmt.where(Cutoff.stage == stage)

    if min_percentile is not None:
        stmt = stmt.where(Cutoff.percentile >= min_percentile)
    if max_percentile is not None:
        stmt = stmt.where(Cutoff.percentile <= max_percentile)

    if min_merit is not None:
        stmt = stmt.where(Cutoff.merit_number >= min_merit)
    if max_merit is not None:
        stmt = stmt.where(Cutoff.merit_number <= max_merit)

    if is_deleted is not None:
        stmt = stmt.where(Cutoff.is_deleted == is_deleted)

    if college_type:
        ct = college_type.strip().lower()
        if ct == 'autonomous':
            stmt = stmt.where(College.college_type == 'Autonomous')
        elif ct in ['non-autonomous', 'non autonomous', 'nonautonomous']:
            stmt = stmt.where(College.college_type == 'Non-Autonomous')
        else:
            stmt = stmt.where(College.college_type.ilike(f"%{college_type}%"))

    if funding_type:
        ft = funding_type.strip().lower()
        if ft == 'government':
            stmt = stmt.where(
                or_(
                    College.funding_type.ilike('%Government%'),
                    College.college_name.ilike('%Government%'),
                    College.college_name.ilike('%Govt%'),
                    College.college_name.ilike('%VJTI%'),
                    College.college_name.ilike('%University Department%'),
                    College.college_name.ilike('%Institute of Chemical Technology%'),
                    College.college_name.ilike('%Lahoti%')
                )
            )
        elif ft == 'private':
            stmt = stmt.where(
                and_(
                    College.funding_type.ilike('%Private%'),
                    not_(College.college_name.ilike('%Government%')),
                    not_(College.college_name.ilike('%Govt%')),
                    not_(College.college_name.ilike('%VJTI%')),
                    not_(College.college_name.ilike('%University Department%')),
                    not_(College.college_name.ilike('%Institute of Chemical Technology%')),
                    not_(College.college_name.ilike('%Lahoti%'))
                )
            )
        else:
            stmt = stmt.where(College.funding_type.ilike(f"%{funding_type}%"))
        
    return stmt


@router.get("/", response_model=PaginatedResponse[CutoffListItem])
def list_cutoffs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    year: Optional[int] = None,
    round_number: Optional[str] = None,
    cap_round_id: Optional[int] = None,
    college: Optional[str] = None,
    college_code: Optional[str] = None,
    course: Optional[str] = None,
    course_code: Optional[str] = None,
    category_code: Optional[str] = None,
    gender: Optional[str] = None,
    city_district: Optional[str] = None,
    seat_section: Optional[str] = None,
    stage: Optional[str] = None,
    min_percentile: Optional[float] = None,
    max_percentile: Optional[float] = None,
    min_merit: Optional[int] = None,
    max_merit: Optional[int] = None,
    sort_by: Optional[str] = Query("percentile_desc"),
    is_deleted: Optional[bool] = False,
    quota_group: Optional[str] = None,
    college_type: Optional[str] = None,
    funding_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # Ensure int even if called directly outside FastAPI
    page = int(page.default if hasattr(page, 'default') else page)
    page_size = int(page_size.default if hasattr(page_size, 'default') else page_size)
    skip = (page - 1) * page_size
    stmt = get_cutoff_query(
        db=db,
        year=year,
        round_number=round_number,
        cap_round_id=cap_round_id,
        college=college,
        college_code=college_code,
        course=course,
        course_code=course_code,
        category_code=category_code,
        gender=gender,
        city_district=city_district,
        seat_section=seat_section,
        stage=stage,
        min_percentile=min_percentile,
        max_percentile=max_percentile,
        min_merit=min_merit,
        max_merit=max_merit,
        is_deleted=is_deleted,
        quota_group=quota_group,
        college_type=college_type,
        funding_type=funding_type
    )
    
    # Total count query
    count_query = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_query) or 0

    # Sorting
    if sort_by == "percentile_asc":
        stmt = stmt.order_by(Cutoff.percentile.asc().nullslast(), Cutoff.merit_number.desc())
    elif sort_by == "merit_asc":
        stmt = stmt.order_by(Cutoff.merit_number.asc().nullslast(), desc(Cutoff.percentile))
    elif sort_by == "merit_desc":
        stmt = stmt.order_by(Cutoff.merit_number.desc().nullslast(), Cutoff.percentile.asc())
    elif sort_by == "college_name":
        stmt = stmt.order_by(College.college_name.asc(), desc(Cutoff.percentile))
    elif sort_by == "course_name":
        stmt = stmt.order_by(Course.course_name.asc(), desc(Cutoff.percentile))
    elif sort_by == "round_asc":
        stmt = stmt.order_by(CapRound.round_number.asc(), desc(Cutoff.percentile))
    else:  # percentile_desc (default)
        stmt = stmt.order_by(desc(Cutoff.percentile), Cutoff.merit_number.asc())

    stmt = stmt.offset(skip).limit(page_size)
    results = db.execute(stmt).all()
    
    items = []
    for cutoff, college_obj, course_obj, cap_round in results:
        cutoff_dict = {c.name: getattr(cutoff, c.name) for c in cutoff.__table__.columns}
        cutoff_dict['college_code'] = college_obj.college_code
        cutoff_dict['college_name'] = college_obj.college_name
        cutoff_dict['city'] = college_obj.city
        cutoff_dict['district'] = college_obj.district
        cutoff_dict['course_code'] = course_obj.course_code
        cutoff_dict['course_name'] = course_obj.course_name
        cutoff_dict['round_number'] = cap_round.round_number
        cutoff_dict['percentile'] = float(cutoff.percentile) if cutoff.percentile is not None else None
        items.append(CutoffListItem(**cutoff_dict))
        
    import math
    total_pages = math.ceil(total / page_size) if page_size else 0
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/export")
def export_cutoffs(
    year: Optional[int] = None,
    round_number: Optional[str] = None,
    cap_round_id: Optional[int] = None,
    college: Optional[str] = None,
    college_code: Optional[str] = None,
    course: Optional[str] = None,
    course_code: Optional[str] = None,
    category_code: Optional[str] = None,
    gender: Optional[str] = None,
    city_district: Optional[str] = None,
    seat_section: Optional[str] = None,
    stage: Optional[str] = None,
    min_percentile: Optional[float] = None,
    max_percentile: Optional[float] = None,
    min_merit: Optional[int] = None,
    max_merit: Optional[int] = None,
    sort_by: Optional[str] = Query("percentile_desc"),
    is_deleted: Optional[bool] = False,
    quota_group: Optional[str] = None,
    college_type: Optional[str] = None,
    funding_type: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = get_cutoff_query(
        db=db,
        year=year,
        round_number=round_number,
        cap_round_id=cap_round_id,
        college=college,
        college_code=college_code,
        course=course,
        course_code=course_code,
        category_code=category_code,
        gender=gender,
        city_district=city_district,
        seat_section=seat_section,
        stage=stage,
        min_percentile=min_percentile,
        max_percentile=max_percentile,
        min_merit=min_merit,
        max_merit=max_merit,
        is_deleted=is_deleted,
        quota_group=quota_group,
        college_type=college_type,
        funding_type=funding_type
    )

    if sort_by == "percentile_asc":
        stmt = stmt.order_by(Cutoff.percentile.asc().nullslast(), Cutoff.merit_number.desc())
    elif sort_by == "merit_asc":
        stmt = stmt.order_by(Cutoff.merit_number.asc().nullslast(), desc(Cutoff.percentile))
    elif sort_by == "merit_desc":
        stmt = stmt.order_by(Cutoff.merit_number.desc().nullslast(), Cutoff.percentile.asc())
    elif sort_by == "college_name":
        stmt = stmt.order_by(College.college_name.asc(), desc(Cutoff.percentile))
    elif sort_by == "course_name":
        stmt = stmt.order_by(Course.course_name.asc(), desc(Cutoff.percentile))
    else:
        stmt = stmt.order_by(desc(Cutoff.percentile), Cutoff.merit_number.asc())

    results = db.execute(stmt).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Year", "Round", "College Code", "College Name", "City/District", 
        "Course Code", "Course Name", "Seat Section", "Category Code", 
        "Gender", "Stage", "Merit Rank", "Percentile", "Source Page", "Source PDF"
    ])
    
    for cutoff, college_obj, course_obj, cap_round in results:
        writer.writerow([
            cutoff.year,
            cap_round.round_number,
            college_obj.college_code,
            college_obj.college_name,
            college_obj.district or college_obj.city or "",
            course_obj.course_code,
            course_obj.course_name,
            cutoff.seat_section,
            cutoff.category_code,
            cutoff.gender or "",
            cutoff.stage,
            cutoff.merit_number or "",
            float(cutoff.percentile) if cutoff.percentile is not None else "",
            cutoff.source_page or "",
            cutoff.source_pdf or ""
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=cutoff_analysis_export.csv"}
    )


@router.get("/{cutoff_id}", response_model=CutoffDetail)
def get_cutoff(
    cutoff_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Cutoff, College, Course, CapRound)\
        .join(Course, Course.id == Cutoff.course_id)\
        .join(College, College.id == Course.college_id)\
        .join(CapRound, CapRound.id == Cutoff.cap_round_id)\
        .where(Cutoff.id == cutoff_id)
        
    result = db.execute(stmt).first()
    if not result:
        raise HTTPException(status_code=404, detail="Cutoff not found")
        
    cutoff, college_obj, course_obj, cap_round = result
    
    corrections_stmt = select(ManualCorrection).where(ManualCorrection.cutoff_id == cutoff_id)
    corrections = db.execute(corrections_stmt).scalars().all()
    
    cutoff_dict = {c.name: getattr(cutoff, c.name) for c in cutoff.__table__.columns}
    cutoff_dict['college_code'] = college_obj.college_code
    cutoff_dict['college_name'] = college_obj.college_name
    cutoff_dict['city'] = college_obj.city
    cutoff_dict['district'] = college_obj.district
    cutoff_dict['course_code'] = course_obj.course_code
    cutoff_dict['course_name'] = course_obj.course_name
    cutoff_dict['round_number'] = cap_round.round_number
    cutoff_dict['percentile'] = float(cutoff.percentile) if cutoff.percentile is not None else None
    cutoff_dict['manual_corrections'] = [ManualCorrectionItem.model_validate(c) for c in corrections]
    
    return CutoffDetail(**cutoff_dict)


@router.put("/{cutoff_id}")
def update_cutoff(
    cutoff_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Enforce PDF source of truth: manual editing is disabled."""
    raise HTTPException(
        status_code=403, 
        detail="Manual modification is disabled. Official CAP Round PDF is the sole source of truth."
    )


@router.delete("/{cutoff_id}")
def delete_cutoff(
    cutoff_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """Enforce PDF source of truth: manual deletion is disabled."""
    raise HTTPException(
        status_code=403, 
        detail="Manual deletion is disabled. Official CAP Round PDF is the sole source of truth."
    )

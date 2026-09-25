from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import Cutoff, College, Course, CapRound
from app.schemas.analysis import (
    RoundComparisonItem, 
    DataQualityReport, 
    CategorySummary,
    FilterOptions,
    CutoffSummary,
    CollegeOption,
    CourseOption
)

router = APIRouter()

@router.get("/round-comparison", response_model=List[RoundComparisonItem])
def round_comparison(
    year: int,
    round_a: int,
    round_b: int,
    college_code: Optional[str] = None,
    course_code: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    # This requires a complex self-join or two queries joined in memory
    # For simplicity, we'll fetch round A and round B cutoffs and merge in memory
    
    stmt = select(Cutoff, College, Course, CapRound)\
        .join(Course, Course.id == Cutoff.course_id)\
        .join(College, College.id == Course.college_id)\
        .join(CapRound, CapRound.id == Cutoff.cap_round_id)\
        .where(Cutoff.year == year, Cutoff.is_deleted == False)
        
    if college_code:
        stmt = stmt.where(College.college_code == college_code)
    if course_code:
        stmt = stmt.where(Course.course_code == course_code)
        
    # Only rounds A and B
    stmt = stmt.where(CapRound.round_number.in_([round_a, round_b]))
    
    results = db.execute(stmt).all()
    
    # Group by a unique key
    grouped = {}
    for cutoff, college, course, cap_round in results:
        key = (course.course_code, cutoff.category_code, cutoff.seat_section, cutoff.stage)
        if key not in grouped:
            grouped[key] = {
                "course_code": course.course_code,
                "course_name": course.course_name,
                "college_name": college.college_name,
                "category_code": cutoff.category_code,
                "seat_section": cutoff.seat_section,
                "stage": cutoff.stage,
                "round_a_merit": None,
                "round_a_percentile": None,
                "round_b_merit": None,
                "round_b_percentile": None,
                "percentile_change": None
            }
            
        if cap_round.round_number == round_a:
            grouped[key]["round_a_merit"] = cutoff.merit_number
            grouped[key]["round_a_percentile"] = float(cutoff.percentile) if cutoff.percentile is not None else None
        elif cap_round.round_number == round_b:
            grouped[key]["round_b_merit"] = cutoff.merit_number
            grouped[key]["round_b_percentile"] = float(cutoff.percentile) if cutoff.percentile is not None else None
            
    # Calculate change
    for val in grouped.values():
        if val["round_a_percentile"] is not None and val["round_b_percentile"] is not None:
            val["percentile_change"] = val["round_b_percentile"] - val["round_a_percentile"]
            
    return list(grouped.values())

@router.get("/data-quality", response_model=DataQualityReport)
def data_quality(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    total = db.execute(select(func.count(Cutoff.id))).scalar() or 0
    missing_merit = db.execute(select(func.count(Cutoff.id)).where(Cutoff.merit_number == None)).scalar() or 0
    missing_percentile = db.execute(select(func.count(Cutoff.id)).where(Cutoff.percentile == None)).scalar() or 0
    zero_merit = db.execute(select(func.count(Cutoff.id)).where(Cutoff.merit_number == 0)).scalar() or 0
    
    # Dummy duplicates for now as actual dup check is heavy
    duplicate_count = 0
    
    # Category distributions
    cat_stmt = select(Cutoff.category_code, func.count(Cutoff.id)).group_by(Cutoff.category_code)
    cat_dist = {row[0]: row[1] for row in db.execute(cat_stmt).all() if row[0]}
    
    sec_stmt = select(Cutoff.seat_section, func.count(Cutoff.id)).group_by(Cutoff.seat_section)
    sec_dist = {row[0]: row[1] for row in db.execute(sec_stmt).all() if row[0]}
    
    return DataQualityReport(
        total_records=total,
        records_with_missing_merit=missing_merit,
        records_with_missing_percentile=missing_percentile,
        records_with_zero_merit=zero_merit,
        duplicate_count=duplicate_count,
        records_by_validation_status={"valid": total},
        category_distribution=cat_dist,
        section_distribution=sec_dist
    )

@router.get("/category-summary", response_model=List[CategorySummary])
def category_summary(
    year: int,
    cap_round_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = select(Cutoff.category_code, func.count(Cutoff.id)).where(Cutoff.year == year)
    if cap_round_id:
        stmt = stmt.where(Cutoff.cap_round_id == cap_round_id)
        
    stmt = stmt.group_by(Cutoff.category_code)
    results = db.execute(stmt).all()
    
    return [CategorySummary(category_code=row[0] or "UNKNOWN", count=row[1]) for row in results]


@router.get("/filter-options", response_model=FilterOptions)
def get_filter_options(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    years = [r[0] for r in db.execute(select(Cutoff.year).distinct().order_by(Cutoff.year.desc())).all() if r[0]]
    rounds = [r[0] for r in db.execute(select(CapRound.round_number).distinct().order_by(CapRound.round_number.asc())).all() if r[0]]
    categories = [r[0] for r in db.execute(select(Cutoff.category_code).distinct().order_by(Cutoff.category_code.asc())).all() if r[0]]
    seat_sections = [r[0] for r in db.execute(select(Cutoff.seat_section).distinct().order_by(Cutoff.seat_section.asc())).all() if r[0]]
    stages = [r[0] for r in db.execute(select(Cutoff.stage).distinct().order_by(Cutoff.stage.asc())).all() if r[0]]
    
    # Collect unique cities and districts
    cities = [r[0] for r in db.execute(select(College.city).distinct()).all() if r[0]]
    districts = [r[0] for r in db.execute(select(College.district).distinct()).all() if r[0]]
    cities_districts = sorted(list(set(cities + districts)))

    # Colleges
    college_rows = db.execute(
        select(College.college_code, College.college_name, College.city, College.district, College.college_type)
        .order_by(College.college_name.asc())
    ).all()
    colleges = [
        CollegeOption(
            college_code=r[0],
            college_name=r[1],
            city=r[2],
            district=r[3],
            college_type=r[4]
        )
        for r in college_rows
    ]

    # Courses (distinct by course_name)
    course_rows = db.execute(
        select(Course.course_code, Course.course_name)
        .distinct()
        .order_by(Course.course_name.asc())
    ).all()
    courses = [
        CourseOption(
            course_code=r[0],
            course_name=r[1]
        )
        for r in course_rows
    ]

    return FilterOptions(
        years=years,
        rounds=rounds,
        categories=categories,
        seat_sections=seat_sections,
        stages=stages,
        cities_districts=cities_districts,
        colleges=colleges,
        courses=courses
    )


@router.get("/summary", response_model=CutoffSummary)
def get_cutoff_summary(
    year: Optional[int] = None,
    round_number: Optional[int] = None,
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
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    agg_query = select(
        func.count(Cutoff.id).label("total_matches"),
        func.min(Cutoff.percentile).label("min_percentile"),
        func.max(Cutoff.percentile).label("max_percentile"),
        func.avg(Cutoff.percentile).label("avg_percentile"),
        func.min(Cutoff.merit_number).label("min_merit"),
        func.max(Cutoff.merit_number).label("max_merit"),
        func.count(func.distinct(College.id)).label("unique_colleges"),
        func.count(func.distinct(Course.id)).label("unique_courses")
    ).join(Course, Course.id == Cutoff.course_id)\
     .join(College, College.id == Course.college_id)\
     .join(CapRound, CapRound.id == Cutoff.cap_round_id)

    if year is not None:
        agg_query = agg_query.where(Cutoff.year == year)
    if round_number is not None:
        agg_query = agg_query.where(CapRound.round_number == round_number)
    if cap_round_id is not None:
        agg_query = agg_query.where(Cutoff.cap_round_id == cap_round_id)
        
    if college:
        agg_query = agg_query.where(
            or_(
                College.college_code.ilike(f"%{college}%"),
                College.college_name.ilike(f"%{college}%")
            )
        )
    elif college_code:
        agg_query = agg_query.where(College.college_code == college_code)

    if course:
        agg_query = agg_query.where(
            or_(
                Course.course_code.ilike(f"%{course}%"),
                Course.course_name.ilike(f"%{course}%")
            )
        )
    elif course_code:
        agg_query = agg_query.where(Course.course_code == course_code)

    if category_code:
        agg_query = agg_query.where(Cutoff.category_code.ilike(f"%{category_code}%"))

    if gender:
        g = gender.strip().lower()
        if g in ['general', 'g', 'male']:
            agg_query = agg_query.where(
                or_(
                    Cutoff.gender.ilike('General'),
                    Cutoff.gender == 'G',
                    Cutoff.category_code.like('G%')
                )
            )
        elif g in ['ladies', 'l', 'female']:
            agg_query = agg_query.where(
                or_(
                    Cutoff.gender.ilike('Ladies'),
                    Cutoff.gender == 'L',
                    Cutoff.category_code.like('L%')
                )
            )

    if city_district:
        cd = city_district.strip()
        agg_query = agg_query.where(
            or_(
                College.city.ilike(f"%{cd}%"),
                College.district.ilike(f"%{cd}%"),
                College.college_name.ilike(f"%{cd}%")
            )
        )

    if seat_section:
        agg_query = agg_query.where(Cutoff.seat_section == seat_section)
    if stage:
        agg_query = agg_query.where(Cutoff.stage == stage)

    if min_percentile is not None:
        agg_query = agg_query.where(Cutoff.percentile >= min_percentile)
    if max_percentile is not None:
        agg_query = agg_query.where(Cutoff.percentile <= max_percentile)

    if min_merit is not None:
        agg_query = agg_query.where(Cutoff.merit_number >= min_merit)
    if max_merit is not None:
        agg_query = agg_query.where(Cutoff.merit_number <= max_merit)

    if is_deleted is not None:
        agg_query = agg_query.where(Cutoff.is_deleted == is_deleted)

    res = db.execute(agg_query).first()
    if not res or res[0] == 0:
        return CutoffSummary(
            total_matches=0,
            min_percentile=None,
            max_percentile=None,
            avg_percentile=None,
            min_merit=None,
            max_merit=None,
            unique_colleges=0,
            unique_courses=0
        )

    return CutoffSummary(
        total_matches=res[0] or 0,
        min_percentile=float(res[1]) if res[1] is not None else None,
        max_percentile=float(res[2]) if res[2] is not None else None,
        avg_percentile=round(float(res[3]), 4) if res[3] is not None else None,
        min_merit=res[4],
        max_merit=res[5],
        unique_colleges=res[6] or 0,
        unique_courses=res[7] or 0
    )

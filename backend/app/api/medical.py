from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
import csv

from app.schemas.medical import (
    MedicalFilterOptions,
    MedicalPaginatedResponse,
    MedicalDbStats,
)
from app.medical_db import (
    fetch_medical_filter_options,
    query_medical_cutoffs,
    get_medical_stats,
    wipe_medical_database,
)

router = APIRouter()


@router.get("/filter-options", response_model=MedicalFilterOptions)
def get_medical_filter_options_endpoint():
    """
    Returns available filter options from medical.db:
    academic_years, rounds, colleges, courses, college_types, categories, quotas.
    """
    try:
        return fetch_medical_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Medical filter options: {str(e)}")


@router.get("/cutoffs", response_model=MedicalPaginatedResponse)
def get_medical_cutoffs_endpoint(
    academic_year: Optional[str] = Query(None, description="Academic year (e.g. 2026-2027, 2025-2026, 2024-2025)"),
    round_name: Optional[str] = Query(None, description="Round (Round 1, Round 2, All)"),
    college_id: Optional[int] = Query(None, description="Specific College ID"),
    college_name: Optional[str] = Query(None, description="College name or code (supports multi-select with ||)"),
    course_id: Optional[int] = Query(None, description="Specific Course ID"),
    course_name: Optional[str] = Query(None, description="Course code or name (MBBS, BDS, BAMS, etc.)"),
    college_type: Optional[str] = Query(None, description="Government/Aided or Private"),
    category: Optional[str] = Query(None, description="Base Category (OPEN, OBC, EWS, SC, ST, etc.)"),
    quota: Optional[str] = Query(None, description="Detailed Quota (OPEN, OPEN (W), DEF1, etc.)"),
    student_rank: Optional[int] = Query(None, description="Student NEET AIR (filters reachable colleges and assigns chances)"),
    student_score: Optional[int] = Query(None, description="Student NEET Score / Marks out of 720"),
    min_rank: Optional[int] = Query(None, description="Minimum rank"),
    max_rank: Optional[int] = Query(None, description="Maximum rank"),
    min_score: Optional[int] = Query(None, description="Minimum score"),
    max_score: Optional[int] = Query(None, description="Maximum score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("rank_asc", description="rank_asc, rank_desc, score_desc, score_asc, year_desc, college_asc, course_asc"),
):
    """
    Query NEET Medical cutoffs with filtering, sorting, pagination, and eligibility chance estimation.
    """
    try:
        return query_medical_cutoffs(
            academic_year=academic_year,
            round_name=round_name,
            college_id=college_id,
            college_name=college_name,
            course_id=course_id,
            course_name=course_name,
            college_type=college_type,
            category=category,
            quota=quota,
            student_rank=student_rank,
            student_score=student_score,
            min_rank=min_rank,
            max_rank=max_rank,
            min_score=min_score,
            max_score=max_score,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query Medical cutoffs: {str(e)}")


@router.get("/stats", response_model=MedicalDbStats)
def get_medical_stats_endpoint():
    """
    Returns counts of cutoffs, colleges, courses, available years, and breakdown.
    """
    try:
        return get_medical_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Medical stats: {str(e)}")


@router.get("/export")
def export_medical_cutoffs_csv(
    academic_year: Optional[str] = Query(None),
    round_name: Optional[str] = Query(None),
    college_id: Optional[int] = Query(None),
    college_name: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None),
    course_name: Optional[str] = Query(None),
    college_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    quota: Optional[str] = Query(None),
    student_rank: Optional[int] = Query(None),
    student_score: Optional[int] = Query(None),
    sort_by: str = Query("rank_asc"),
):
    """
    Exports filtered NEET Medical cutoffs as a CSV stream.
    """
    try:
        data = query_medical_cutoffs(
            academic_year=academic_year,
            round_name=round_name,
            college_id=college_id,
            college_name=college_name,
            course_id=course_id,
            course_name=course_name,
            college_type=college_type,
            category=category,
            quota=quota,
            student_rank=student_rank,
            student_score=student_score,
            page=1,
            page_size=10000,
            sort_by=sort_by,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Academic Year",
            "Round",
            "Course",
            "College Code",
            "College Name",
            "College Type",
            "Quota / Category",
            "Base Category",
            "Opening Rank (AIR)",
            "Closing Rank (AIR)",
            "Opening NEET Marks",
            "Closing NEET Marks",
            "Eligibility Chance"
        ])

        for item in data.get("items", []):
            writer.writerow([
                item.get("academic_year"),
                item.get("round"),
                item.get("course_code"),
                item.get("college_code"),
                item.get("college_name"),
                item.get("college_type"),
                item.get("quota_category"),
                item.get("base_category"),
                item.get("opening_rank") or "",
                item.get("closing_rank") or "",
                item.get("opening_score") or "",
                item.get("closing_score") or "",
                item.get("chance") or "",
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="neet_medical_cutoffs.csv"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export Medical CSV: {str(e)}")


@router.post("/wipe")
def wipe_medical_endpoint():
    """
    Clears all Medical data from dedicated medical.db.
    """
    try:
        wipe_medical_database()
        return {"success": True, "message": "Medical database successfully reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to wipe medical database: {str(e)}")

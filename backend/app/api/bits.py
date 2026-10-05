from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
import csv

from app.schemas.bits import (
    BitsFilterOptions,
    BitsPaginatedResponse,
    BitsDbStats,
    BitsScraperStatus,
)
from app.bits_db import (
    fetch_bits_filter_options,
    query_bits_cutoffs,
    get_bits_stats,
    wipe_bits_database,
)
from app.services.scrape_bits_official import (
    start_bits_scraper_background,
    get_bits_scraper_status,
    run_bits_scraper,
    TARGET_YEARS,
)

router = APIRouter()


@router.get("/filter-options", response_model=BitsFilterOptions)
def get_bits_filter_options_endpoint():
    """
    Returns available filter options from bits.db:
    academic_years, campuses, programs, degree_types, categories.
    """
    try:
        return fetch_bits_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch BITS filter options: {str(e)}")


@router.get("/cutoffs", response_model=BitsPaginatedResponse)
def get_bits_cutoffs_endpoint(
    academic_year: Optional[str] = Query(None, description="Academic year (e.g. 2026-2027 or 2025-2026)"),
    campus_id: Optional[int] = Query(None, description="Specific Campus ID"),
    campus_name: Optional[str] = Query(None, description="Campus name or code (Pilani, Goa, Hyderabad)"),
    program_id: Optional[int] = Query(None, description="Specific Program ID"),
    program_name: Optional[str] = Query(None, description="Academic Program name query"),
    degree_type: Optional[str] = Query(None, description="Degree type (B.E., M.Sc., B.Pharm.)"),
    min_score: Optional[int] = Query(None, description="Minimum cutoff score"),
    max_score: Optional[int] = Query(None, description="Maximum cutoff score"),
    student_score: Optional[int] = Query(None, description="Student BITSAT score (shows options where student score >= cutoff score)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("score_desc", description="score_desc, score_asc, year_desc, year_asc, campus_asc, program_asc"),
):
    """
    Query BITSAT cutoffs with filtering, sorting, pagination, and student chance calculation.
    """
    try:
        return query_bits_cutoffs(
            academic_year=academic_year,
            campus_id=campus_id,
            campus_name=campus_name,
            program_id=program_id,
            program_name=program_name,
            degree_type=degree_type,
            min_score=min_score,
            max_score=max_score,
            student_score=student_score,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query BITS cutoffs: {str(e)}")


@router.get("/stats", response_model=BitsDbStats)
def get_bits_stats_endpoint():
    """
    Returns counts of cutoffs, campuses, programs, available years, and last scraped time.
    """
    try:
        return get_bits_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch BITS database stats: {str(e)}")


@router.get("/export")
def export_bits_cutoffs_csv(
    academic_year: Optional[str] = Query(None),
    campus_id: Optional[int] = Query(None),
    campus_name: Optional[str] = Query(None),
    program_id: Optional[int] = Query(None),
    program_name: Optional[str] = Query(None),
    degree_type: Optional[str] = Query(None),
    student_score: Optional[int] = Query(None),
    sort_by: str = Query("score_desc"),
):
    """
    Export matching BITSAT cutoffs to CSV.
    """
    try:
        res = query_bits_cutoffs(
            academic_year=academic_year,
            campus_id=campus_id,
            campus_name=campus_name,
            program_id=program_id,
            program_name=program_name,
            degree_type=degree_type,
            student_score=student_score,
            page=1,
            page_size=10000,
            sort_by=sort_by,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Academic Year", "Campus", "Location", "State",
            "Degree Program", "Degree Type", "Cutoff Score",
            "Maximum Marks", "Score Percentage", "Category", "Exam"
        ])

        for item in res["items"]:
            writer.writerow([
                item["academic_year"],
                item["campus_name"],
                item["campus_location"] or "",
                item["campus_state"] or "",
                item["program_name"],
                item["degree_type"],
                item["cutoff_score"],
                item["max_marks"],
                f"{item['score_percentage']}%" if item["score_percentage"] is not None else "",
                item["category"],
                item["exam_name"],
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=bitsat_cutoffs.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/scrape")
def trigger_bits_scraper_endpoint(
    years: Optional[List[str]] = Query(None, description="Years to scrape (default: 2026-2027 and 2025-2026)")
):
    """
    Triggers web-scraper to fetch BITSAT cutoff data directly from the official website.
    """
    try:
        target = years if years else TARGET_YEARS
        started = start_bits_scraper_background(target_years=target)
        if not started:
            return {
                "success": False,
                "message": "BITSAT scraper is already running in background."
            }
        return {
            "success": True,
            "message": f"BITSAT scraper started in background for years: {', '.join(target)}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start BITSAT scraper: {str(e)}")


@router.get("/scraper-status", response_model=BitsScraperStatus)
def get_bits_scraper_status_endpoint():
    """
    Returns live progress and state of the BITSAT background scraper.
    """
    return get_bits_scraper_status()


@router.post("/reset-database")
def reset_bits_database_endpoint():
    """
    Safely resets all records in bits.db while preserving the schema.
    """
    try:
        return wipe_bits_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset BITS database: {str(e)}")

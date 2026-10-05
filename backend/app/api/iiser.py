from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
import csv

from app.schemas.iiser import (
    IiserFilterOptions,
    IiserPaginatedResponse,
    IiserRoundNoticeItem,
    IiserDbStats,
    IiserScraperStatus,
)
from app.iiser_db import (
    fetch_iiser_filter_options,
    query_iiser_cutoffs,
    fetch_iiser_round_notices,
    get_iiser_stats,
    wipe_iiser_database,
)
from app.services.scrape_iiser_official import (
    start_iiser_scraper_background,
    get_iiser_scraper_status,
    run_iiser_scraper,
)

router = APIRouter()


@router.get("/filter-options", response_model=IiserFilterOptions)
def get_iiser_filter_options_endpoint():
    """
    Returns available filter options from iiser.db:
    rounds, years, institutes, programs, degree_types, categories, states.
    """
    try:
        return fetch_iiser_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch IISER filter options: {str(e)}")


@router.get("/cutoffs", response_model=IiserPaginatedResponse)
def get_iiser_cutoffs_endpoint(
    round_no: Optional[str] = Query(None, description="Round number(s), comma-separated (e.g. 1 or 1,2,3)"),
    academic_year: Optional[int] = Query(None, description="Academic Year (e.g. 2024)"),
    institute_id: Optional[int] = Query(None, description="Specific Institute ID"),
    institute_name: Optional[str] = Query(None, description="Institute name query"),
    state: Optional[str] = Query(None, description="State of the IISER campus"),
    program_id: Optional[int] = Query(None, description="Specific Program ID"),
    academic_program: Optional[str] = Query(None, description="Academic Program name query"),
    degree_type: Optional[str] = Query(None, description="Degree type (BS-MS, B.Tech, BS)"),
    category: Optional[str] = Query(None, description="Category code (UR, EWS, OBC-NCL, SC, ST, KM, etc.)"),
    max_rank: Optional[int] = Query(None, description="Student IAT Rank (shows where student rank <= closing_rank)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("rank_asc", description="rank_asc, rank_desc, round_asc, round_desc, institute_asc, program_asc"),
):
    """
    Query IISER cutoffs with filtering, sorting, pagination, and chance predictor.
    """
    try:
        return query_iiser_cutoffs(
            round_no=round_no,
            academic_year=academic_year,
            institute_id=institute_id,
            institute_name=institute_name,
            state=state,
            program_id=program_id,
            academic_program=academic_program,
            degree_type=degree_type,
            category=category,
            max_rank=max_rank,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query IISER cutoffs: {str(e)}")


@router.get("/notices", response_model=List[IiserRoundNoticeItem])
def get_iiser_notices_endpoint(
    round_no: Optional[int] = Query(None, description="Optional round filter")
):
    """
    Fetch official admission updates and program closure notices.
    """
    try:
        return fetch_iiser_round_notices(round_no=round_no)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch IISER notices: {str(e)}")


@router.get("/stats", response_model=IiserDbStats)
def get_iiser_stats_endpoint():
    """
    Returns counts of cutoffs, institutes, programs, categories, rounds, and notices.
    """
    try:
        return get_iiser_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch IISER database stats: {str(e)}")


@router.get("/export")
def export_iiser_cutoffs_csv(
    round_no: Optional[str] = Query(None),
    academic_year: Optional[int] = Query(None),
    institute_id: Optional[int] = Query(None),
    institute_name: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    program_id: Optional[int] = Query(None),
    academic_program: Optional[str] = Query(None),
    degree_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    max_rank: Optional[int] = Query(None),
    sort_by: str = Query("rank_asc"),
):
    """
    Export matching IISER cutoffs to CSV.
    """
    try:
        res = query_iiser_cutoffs(
            round_no=round_no,
            academic_year=academic_year,
            institute_id=institute_id,
            institute_name=institute_name,
            state=state,
            program_id=program_id,
            academic_program=academic_program,
            degree_type=degree_type,
            category=category,
            max_rank=max_rank,
            page=1,
            page_size=10000,
            sort_by=sort_by,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Year", "Round", "Institute Name", "State",
            "Academic Program", "Degree", "Category", 
            "Seat Pool", "Allocation Channel", "Closing Rank (Overall)"
        ])

        for item in res["items"]:
            writer.writerow([
                item["academic_year"],
                f"Round {item['round_no']}",
                item["institute_name"],
                item["institute_state"] or "India",
                item["program_name"],
                item["degree_type"],
                item["category_code"],
                item["seat_pool"],
                item["allocation_channel"],
                item["closing_rank"],
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=iiser_cutoffs.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/scrape")
def trigger_iiser_scraper_endpoint():
    """
    Triggers web-scraper to fetch IISER cutoff data directly from the official website.
    """
    try:
        started = start_iiser_scraper_background()
        if not started:
            return {
                "success": False,
                "message": "IISER scraper is already running in background."
            }
        return {
            "success": True,
            "message": "IISER web scraper started in background from official website."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start IISER scraper: {str(e)}")


@router.get("/scraper-status", response_model=IiserScraperStatus)
def get_iiser_scraper_status_endpoint():
    """
    Returns live progress and state of the IISER background scraper.
    """
    return get_iiser_scraper_status()


@router.post("/reset-database")
def reset_iiser_database_endpoint():
    """
    Safely resets all records in iiser.db while keeping the schema intact.
    """
    try:
        return wipe_iiser_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset IISER database: {str(e)}")

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import csv

from app.schemas.csab import CsabFilterOptions, CsabPaginatedResponse
from app.csab_db import fetch_csab_filter_options, query_csab_cutoffs, wipe_csab_database, get_csab_connection

router = APIRouter()

@router.get("/filter-options", response_model=CsabFilterOptions)
def get_csab_filter_options():
    """
    Returns available filter options from csab.db:
    rounds, years, institute_types, institutes, programs, categories, quotas, and genders.
    """
    try:
        data = fetch_csab_filter_options()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch CSAB filter options: {str(e)}")


@router.get("/cutoffs", response_model=CsabPaginatedResponse)
def get_csab_cutoffs(
    round_no: Optional[str] = Query(None, description="Special Round number(s), comma-separated (e.g. 1 or 1,2)"),
    institute_type: Optional[str] = Query(None, description="NIT, IIIT, IIEST, SPA, Other-GFTI"),
    institute_name: Optional[str] = Query(None, description="Institute name query or comma-separated"),
    institute_id: Optional[int] = Query(None, description="Specific institute ID"),
    state: Optional[str] = Query(None, description="Institute physical location state"),
    candidate_state: Optional[str] = Query(None, description="Candidate Home State for HS/OS quota eligibility"),
    academic_program: Optional[str] = Query(None, description="Academic program / branch name"),
    program_id: Optional[int] = Query(None, description="Specific program ID"),
    category: Optional[str] = Query(None, description="Category code (OPEN, OBC-NCL, SC, ST, etc.)"),
    quota: Optional[str] = Query(None, description="AI, HS, OS, GO, JK, LA"),
    gender: Optional[str] = Query(None, description="Gender pool (Gender-Neutral or Female-only)"),
    academic_year: Optional[int] = Query(None, description="Year (e.g. 2026)"),
    max_rank: Optional[int] = Query(None, description="Candidate JEE CRL rank (shows where student rank <= closing_rank)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    sort_by: str = Query("rank_asc", description="rank_asc, rank_desc, opening_rank_asc, institute, program"),
):
    """
    Query CSAB Special Round cutoffs with Opening and Closing CRL ranks.
    """
    try:
        res = query_csab_cutoffs(
            round_no=round_no,
            institute_type=institute_type,
            institute_name=institute_name,
            institute_id=institute_id,
            state=state,
            candidate_state=candidate_state,
            academic_program=academic_program,
            program_id=program_id,
            category=category,
            quota=quota,
            gender=gender,
            academic_year=academic_year,
            max_rank=max_rank,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query CSAB cutoffs: {str(e)}")


@router.get("/export")
def export_csab_cutoffs_csv(
    round_no: Optional[str] = Query(None),
    institute_type: Optional[str] = Query(None),
    institute_name: Optional[str] = Query(None),
    institute_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    candidate_state: Optional[str] = Query(None),
    academic_program: Optional[str] = Query(None),
    program_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    quota: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    academic_year: Optional[int] = Query(None),
    max_rank: Optional[int] = Query(None),
    sort_by: str = Query("rank_asc"),
):
    """
    Export matching CSAB cutoffs to CSV.
    """
    try:
        res = query_csab_cutoffs(
            round_no=round_no,
            institute_type=institute_type,
            institute_name=institute_name,
            institute_id=institute_id,
            state=state,
            candidate_state=candidate_state,
            academic_program=academic_program,
            program_id=program_id,
            category=category,
            quota=quota,
            gender=gender,
            academic_year=academic_year,
            max_rank=max_rank,
            page=1,
            page_size=10000,
            sort_by=sort_by,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Year", "Round", "Institute Type", "Institute Name",
            "Academic Program", "Degree", "Quota", "Seat Pool / Gender",
            "Category", "Opening CRL Rank", "Closing CRL Rank"
        ])

        for item in res["items"]:
            writer.writerow([
                item["academic_year"],
                f"Special Round {item['round_no']}",
                item["institute_type"],
                item["institute_name"],
                item["program_name"],
                item["degree_type"] or "B.Tech",
                item["quota"],
                item["gender"],
                item["category_code"],
                item["opening_rank"],
                item["closing_rank"],
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=csab_special_cutoffs.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stats")
def get_csab_db_stats():
    """
    Returns current row counts of CSAB database (institutes, programs, categories, cutoffs).
    """
    conn = get_csab_connection()
    try:
        cursor = conn.cursor()
        total_cutoffs = cursor.execute("SELECT COUNT(*) FROM cutoff_records").fetchone()[0]
        total_institutes = cursor.execute("SELECT COUNT(*) FROM institutes").fetchone()[0]
        total_programs = cursor.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        total_categories = cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        return {
            "total_cutoffs": total_cutoffs,
            "total_institutes": total_institutes,
            "total_programs": total_programs,
            "total_categories": total_categories,
        }
    finally:
        conn.close()


@router.post("/reset-database")
def reset_csab_database_endpoint():
    """
    Wipes all records from csab.db while keeping schema intact.
    """
    try:
        return wipe_csab_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset CSAB database: {str(e)}")


@router.post("/scrape")
def trigger_csab_scraper_endpoint():
    """
    Triggers background scraping of official CSAB Special Round cutoffs across both rounds.
    """
    from app.services.scrape_csab_official import start_csab_scraper_background
    try:
        started = start_csab_scraper_background()
        if not started:
            return {
                "success": False,
                "message": "CSAB scraper is already actively running in the background."
            }
        return {
            "success": True,
            "message": "CSAB scraper started in background for Special Rounds 1 and 2."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start CSAB scraper: {str(e)}")


@router.get("/scraper-status")
def get_csab_scraper_status_endpoint():
    """
    Returns live progress, percentage, stage, and telemetry for the background CSAB scraper.
    """
    from app.services.scrape_csab_official import get_csab_scraper_status
    return get_csab_scraper_status()

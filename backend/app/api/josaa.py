from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import csv

from app.schemas.josaa import JosaaFilterOptions, JosaaPaginatedResponse
from app.josaa_db import fetch_josaa_filter_options, query_josaa_cutoffs

router = APIRouter()

@router.get("/filter-options", response_model=JosaaFilterOptions)
def get_josaa_filter_options():
    """
    Returns available filter options from josaa.db:
    rounds, years, institute_types, institutes, programs, categories, quotas, and genders.
    """
    try:
        data = fetch_josaa_filter_options()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JoSAA filter options: {str(e)}")

@router.get("/cutoffs", response_model=JosaaPaginatedResponse)
def get_josaa_cutoffs(
    round_no: Optional[str] = Query(None, description="JoSAA Round number(s), comma-separated (e.g. 1 or 1,2,3)"),
    institute_type: Optional[str] = Query(None, description="IIT, NIT, IIIT, Other-GFTI"),
    institute_name: Optional[str] = Query(None, description="Institute name query or comma-separated"),
    institute_id: Optional[int] = Query(None, description="Specific institute ID"),
    state: Optional[str] = Query(None, description="Institute physical location state (e.g. Maharashtra, Karnataka)"),
    candidate_state: Optional[str] = Query(None, description="Candidate Home State for HS/OS quota eligibility"),
    academic_program: Optional[str] = Query(None, description="Academic program / branch name"),
    program_id: Optional[int] = Query(None, description="Specific program ID"),
    category: Optional[str] = Query(None, description="Category code (OPEN, OBC-NCL, SC, ST, etc.)"),
    quota: Optional[str] = Query(None, description="AI, HS, OS"),
    gender: Optional[str] = Query(None, description="Gender pool (Gender-Neutral or Female-only)"),
    academic_year: Optional[int] = Query(None, description="Year (e.g. 2026)"),
    max_rank: Optional[int] = Query(None, description="Student JEE rank (shows where student rank <= closing_rank)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    sort_by: str = Query("rank_asc", description="rank_asc, rank_desc, opening_rank_asc, institute, program"),
):
    """
    Query JoSAA cutoffs with Opening and Closing ranks.
    """
    try:
        res = query_josaa_cutoffs(
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
        raise HTTPException(status_code=500, detail=f"Failed to query JoSAA cutoffs: {str(e)}")

@router.get("/export")
def export_josaa_cutoffs_csv(
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
    Export matching JoSAA cutoffs to CSV.
    """
    try:
        res = query_josaa_cutoffs(
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
            "Category", "Opening Rank", "Closing Rank"
        ])

        for item in res["items"]:
            writer.writerow([
                item["academic_year"],
                f"Round {item['round_no']}",
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
            headers={"Content-Disposition": "attachment; filename=josaa_cutoffs.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/stats")
def get_josaa_db_stats():
    """
    Returns current row counts of JoSAA database (institutes, programs, categories, cutoffs).
    """
    from app.josaa_db import get_josaa_connection
    conn = get_josaa_connection()
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
def reset_josaa_database_endpoint():
    """
    Wipes all records from josaa.db while keeping schema intact.
    """
    from app.josaa_db import wipe_josaa_database
    try:
        return wipe_josaa_database()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset JoSAA database: {str(e)}")

@router.post("/reload-data")
def reload_josaa_data_endpoint():
    """
    Re-seeds official institutes and complete cutoffs into josaa.db for both 2025 & 2026.
    """
    from app.services.scrape_josaa_official import start_josaa_scraper_background
    try:
        started = start_josaa_scraper_background()
        if not started:
            return {
                "success": True,
                "message": "JoSAA multi-year web scraper is already actively running in the background."
            }
        return {
            "success": True,
            "message": "JoSAA multi-year web scraper started in background for Years 2025 and 2026 across all rounds."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start JoSAA scraper: {str(e)}")

@router.post("/scrape")
def trigger_josaa_scraper_endpoint():
    """
    Triggers multi-year background scraping of official JoSAA cutoffs across all rounds
    (all 6 rounds for Year 2025, and 5 rounds for Year 2026).
    """
    from app.services.scrape_josaa_official import start_josaa_scraper_background
    try:
        started = start_josaa_scraper_background()
        if not started:
            return {
                "success": False,
                "message": "JoSAA scraper is already actively running in the background."
            }
        return {
            "success": True,
            "message": "JoSAA scraper started in background for Years 2025 and 2026 across all rounds."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start JoSAA scraper: {str(e)}")


@router.get("/scraper-status")
def get_josaa_scraper_status_endpoint():
    """
    Returns live progress, percentage, stage, and telemetry for the background JoSAA scraper.
    """
    from app.services.scrape_josaa_official import get_josaa_scraper_status
    return get_josaa_scraper_status()


@router.post("/scrape-home-states")
def scrape_home_states_endpoint():
    """
    Scrapes the official JoSAA seat matrix institute view to detect institutes
    offering Home State (HS) quota and populates their Home State in josaa.db.
    """
    from app.services.scrape_josaa_official import scrape_institute_home_states
    try:
        updated = scrape_institute_home_states()
        return {
            "success": True,
            "message": f"Successfully mapped and updated Home State for {len(updated)} institutes offering Home State quota.",
            "updated_count": len(updated),
            "institutes": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape institute home states: {str(e)}")





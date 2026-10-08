from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io
import csv
import time
import uuid
from pathlib import Path
import fitz

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
from app.services.medical_import_service import (
    wipe_all_medical_data,
    restore_verified_medical_dataset,
    ingest_medical_file,
    run_medical_import_task,
    get_medical_task_status,
    ACTIVE_MEDICAL_IMPORT_TASKS,
    UPLOAD_DIR,
    BACKUP_DIR,
)

router = APIRouter()


@router.get("/filter-options", response_model=MedicalFilterOptions)
def get_medical_filter_options_endpoint(
    counselling_type: Optional[str] = Query(None, description="central (MCC) or state (Maharashtra)"),
):
    """
    Returns available filter options from medical.db:
    academic_years, rounds, colleges, courses, college_types, categories, quotas, states, cities.
    """
    try:
        return fetch_medical_filter_options(counselling_type=counselling_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Medical filter options: {str(e)}")


@router.get("/cutoffs", response_model=MedicalPaginatedResponse)
def get_medical_cutoffs_endpoint(
    counselling_type: Optional[str] = Query(None, description="central (MCC) or state (Maharashtra)"),
    academic_year: Optional[str] = Query(None, description="Academic year (e.g. 2026-2027, 2025-2026, 2024-2025)"),
    round_name: Optional[str] = Query(None, description="Round (Round 1, Round 2, All)"),
    college_id: Optional[int] = Query(None, description="Specific College ID"),
    college_name: Optional[str] = Query(None, description="College name or code (supports multi-select with ||)"),
    course_id: Optional[int] = Query(None, description="Specific Course ID"),
    course_name: Optional[str] = Query(None, description="Course code or name (MBBS, BDS, BAMS, etc.)"),
    college_type: Optional[str] = Query(None, description="College management or type"),
    state: Optional[str] = Query(None, description="College State (for Central MCC)"),
    city: Optional[str] = Query(None, description="College City (for State)"),
    category: Optional[str] = Query(None, description="Base Category (OPEN, OBC, EWS, SC, ST, etc.)"),
    quota: Optional[str] = Query(None, description="Detailed Quota (OPEN, OPEN (W), DEF1, etc.)"),
    gender: Optional[str] = Query(None, description="Gender / Seat Quota: women (30% quota) or general"),
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
            counselling_type=counselling_type,
            academic_year=academic_year,
            round_name=round_name,
            college_id=college_id,
            college_name=college_name,
            course_id=course_id,
            course_name=course_name,
            college_type=college_type,
            state=state,
            city=city,
            category=category,
            quota=quota,
            gender=gender,
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
    counselling_type: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    round_name: Optional[str] = Query(None),
    college_id: Optional[int] = Query(None),
    college_name: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None),
    course_name: Optional[str] = Query(None),
    college_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    quota: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    student_rank: Optional[int] = Query(None),
    student_score: Optional[int] = Query(None),
    sort_by: str = Query("rank_asc"),
):
    """
    Exports filtered NEET Medical cutoffs as a CSV stream.
    """
    try:
        data = query_medical_cutoffs(
            counselling_type=counselling_type,
            academic_year=academic_year,
            round_name=round_name,
            college_id=college_id,
            college_name=college_name,
            course_id=course_id,
            course_name=course_name,
            college_type=college_type,
            state=state,
            city=city,
            category=category,
            quota=quota,
            gender=gender,
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
def wipe_medical_endpoint(
    counselling_type: Optional[str] = Query(None, description="central, state, or leave empty for both"),
):
    """
    Clears Medical data from dedicated medical_central.db and/or medical_state.db.
    """
    try:
        return wipe_all_medical_data(counselling_type=counselling_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to wipe medical database: {str(e)}")


@router.post("/restore")
def restore_medical_endpoint(
    counselling_type: Optional[str] = Query(None, description="central, state, or leave empty for both"),
):
    """
    Restores verified Medical datasets into medical_central.db and/or medical_state.db from backup.
    """
    try:
        return restore_verified_medical_dataset(counselling_type=counselling_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore medical database: {str(e)}")


@router.get("/db-status")
def get_medical_db_status_endpoint():
    """
    Returns live database status and record counts for medical.db.
    """
    try:
        stats = get_medical_stats()
        has_backup = (BACKUP_DIR / "medical_backup_full_33613.db").exists()
        return {
            "cutoff_count": stats.get("cutoff_count", 0),
            "college_count": stats.get("college_count", 0),
            "course_count": stats.get("course_count", 0),
            "years": stats.get("years", []),
            "has_backup": has_backup,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch medical DB status: {str(e)}")


@router.post("/upload")
def upload_medical_pdf_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    academic_year: Optional[str] = Form(None),
    round_name: Optional[str] = Form(None),
    stream_type: Optional[str] = Form("auto"),
):
    """
    Uploads a Medical Cutoff PDF (MCC AIQ or Maharashtra State Medical),
    starts background asynchronous parsing with live progress telemetry,
    and returns a task_id immediately.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for Medical cutoffs.")

    try:
        # Save file to storage/uploads/medical/
        safe_filename = f"{int(time.time())}_{file.filename}"
        target_path = UPLOAD_DIR / safe_filename
        
        content = file.file.read()
        with open(target_path, "wb") as f:
            f.write(content)

        # Inspect total pages for accurate immediate progress setup
        total_pages = 1
        try:
            doc = fitz.open(str(target_path))
            total_pages = len(doc)
            doc.close()
        except Exception:
            pass

        task_id = f"med_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        ACTIVE_MEDICAL_IMPORT_TASKS[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "status": "PROCESSING",
            "progress_percent": 5,
            "current_page": 0,
            "total_pages": total_pages,
            "records_created": 0,
            "current_action": f"PDF uploaded successfully ({total_pages} pages). Starting extraction...",
            "started_at": time.time(),
            "finished_at": None,
            "error": None,
            "result": None,
        }

        # Launch background task
        background_tasks.add_task(
            run_medical_import_task,
            task_id,
            target_path,
            academic_year,
            round_name,
            stream_type
        )

        return {
            "task_id": task_id,
            "status": "PROCESSING",
            "filename": file.filename,
            "total_pages": total_pages,
            "progress_percent": 5,
            "current_action": f"PDF uploaded successfully ({total_pages} pages). Starting extraction...",
            "message": f"Medical PDF uploaded ({total_pages} pages). Background parsing started."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Medical PDF upload failed: {str(e)}")


@router.get("/upload/progress/{task_id}")
def get_medical_upload_progress_endpoint(task_id: str):
    """
    Returns real-time progress and telemetry for a medical PDF ingestion background task.
    """
    task = get_medical_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Upload task not found or expired.")
    return task

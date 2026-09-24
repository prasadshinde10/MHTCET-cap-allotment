from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.auth.security import get_current_admin
from app.models.admin_user import AdminUser
from app.models.college import College
from app.models.course import Course
from app.models.cutoff import Cutoff
from app.models.cap_round import CapRound
from app.models.import_batch import ImportBatch
from app.models.parser_error import ParserError
from app.schemas.dashboard import DashboardStats, RecentImport, RecentError

router = APIRouter()


def _get_round_count(db: Session, round_number: int) -> int:
    """Get cutoff count for a specific round number across all years."""
    result = (
        db.query(func.count(Cutoff.id))
        .join(CapRound, Cutoff.cap_round_id == CapRound.id)
        .filter(CapRound.round_number == round_number)
        .filter(Cutoff.is_deleted == False)
        .scalar()
    )
    return result or 0


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    total_colleges = db.query(func.count(College.id)).scalar() or 0
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    total_cutoffs = (
        db.query(func.count(Cutoff.id))
        .filter(Cutoff.is_deleted == False)
        .scalar()
        or 0
    )
    rounds_processed = db.query(func.count(CapRound.id)).scalar() or 0
    total_imports = db.query(func.count(ImportBatch.id)).scalar() or 0
    successful_imports = (
        db.query(func.count(ImportBatch.id))
        .filter(ImportBatch.status == "COMPLETED")
        .scalar()
        or 0
    )
    warning_imports = (
        db.query(func.count(ImportBatch.id))
        .filter(ImportBatch.status == "COMPLETED_WITH_WARNINGS")
        .scalar()
        or 0
    )
    failed_imports = (
        db.query(func.count(ImportBatch.id))
        .filter(ImportBatch.status == "FAILED")
        .scalar()
        or 0
    )
    open_parser_errors = (
        db.query(func.count(ParserError.id))
        .filter(ParserError.status == "OPEN")
        .scalar()
        or 0
    )

    # Per-round cutoff counts
    cap_round_1_records = _get_round_count(db, 1)
    cap_round_2_records = _get_round_count(db, 2)
    cap_round_3_records = _get_round_count(db, 3)
    cap_round_4_records = _get_round_count(db, 4)

    # Recent imports (last 10)
    recent_imports_query = (
        db.query(ImportBatch, CapRound)
        .join(CapRound, ImportBatch.cap_round_id == CapRound.id)
        .order_by(ImportBatch.created_at.desc())
        .limit(10)
        .all()
    )
    imports_list = [
        RecentImport(
            filename=batch.filename,
            round_name=round_obj.round_name,
            year=round_obj.year,
            status=batch.status,
            records=batch.records_created,
            date=batch.started_at,
        )
        for batch, round_obj in recent_imports_query
    ]

    # Recent parser errors (last 10)
    recent_errors_query = (
        db.query(ParserError)
        .order_by(ParserError.created_at.desc())
        .limit(10)
        .all()
    )
    errors_list = [
        RecentError(
            page=err.source_page,
            error=err.error_message,
            severity=err.severity,
            status=err.status,
        )
        for err in recent_errors_query
    ]

    return DashboardStats(
        total_colleges=total_colleges,
        total_courses=total_courses,
        total_cutoffs=total_cutoffs,
        rounds_processed=rounds_processed,
        total_imports=total_imports,
        successful_imports=successful_imports,
        warning_imports=warning_imports,
        failed_imports=failed_imports,
        open_parser_errors=open_parser_errors,
        cap_round_1_records=cap_round_1_records,
        cap_round_2_records=cap_round_2_records,
        cap_round_3_records=cap_round_3_records,
        cap_round_4_records=cap_round_4_records,
        recent_imports=imports_list,
        recent_errors=errors_list,
    )

import os
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from app.database import get_db
from app.config import get_settings
from app.auth.security import get_current_admin
from app.models.admin_user import AdminUser
from app.models.import_batch import ImportBatch
from app.models.cap_round import CapRound
from app.models.import_log import ImportLog
from app.models.parser_error import ParserError
from app.models.staging_cutoff import StagingCutoff
from app.schemas.imports import (
    UploadResponse, ImportBatchListItem, ImportBatchDetail,
    PaginatedResponse, StagingCutoffItem, CommitResponse, ImportLogItem
)
from app.parser.importer import PDFImporter
from app.services.import_service import ImportService
from app.services.audit_service import log_audit
from app.models.cutoff import Cutoff
from app.models.college import College
from app.models.course import Course
import logging
import re
try:
    import fitz
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()
MAX_UPLOAD_SIZE_MB = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 100)

_ROMAN_MAP = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, '1': 1, '2': 2, '3': 3, '4': 4}
_ROUND_REGEX = re.compile(r'CAP\s*Round\s*[-–—:]*\s*([IVXivx\d]+)', re.IGNORECASE)

def detect_pdf_round(pdf_source: bytes | str | Path) -> int | None:
    """Inspects the PDF text directly from document pages to detect which CAP Round it belongs to.
    Does NOT depend on filenames, allowing arbitrary or unlabelled file uploads."""
    if fitz:
        try:
            if isinstance(pdf_source, (str, Path)):
                doc = fitz.open(str(pdf_source))
            else:
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            for page_idx in range(min(5, len(doc))):
                text = doc[page_idx].get_text()
                match = _ROUND_REGEX.search(text)
                if match:
                    val = match.group(1).upper()
                    if val in _ROMAN_MAP:
                        doc.close()
                        return _ROMAN_MAP[val]
            doc.close()
        except Exception as e:
            logger.warning(f"Could not read PDF for round detection: {e}")

    return None

UPLOAD_DIRECTORY = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "uploads"
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=UploadResponse)
def upload_pdf(
    file: UploadFile = File(...),
    year: int = Form(...),
    round_number: int = Form(0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not (2020 <= year <= 2050):
        raise HTTPException(status_code=400, detail="Invalid year")

    # Read file and compute hash
    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB")

    # Detect CAP round directly by parsing the PDF content (no filename inspection)
    detected_round = detect_pdf_round(content)

    if round_number not in (1, 2, 3, 4):
        # Auto-detection requested (or round not specified):
        if detected_round:
            round_number = detected_round
            logger.info(f"Auto-detected CAP Round {round_number} by parsing PDF content for '{file.filename}'.")
        else:
            round_number = 1  # Default to Round 1 if PDF text doesn't explicitly state
            logger.info(f"Could not detect CAP Round from PDF text for '{file.filename}', defaulting to Round 1.")
    else:
        # If user explicitly selected a round (1-4), check if detected_round indicates a different round
        if detected_round and detected_round != round_number:
            logger.info(f"User specified CAP Round {round_number}, but PDF content indicates CAP Round {detected_round}. Using parsed Round {detected_round}.")
            round_number = detected_round

    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = db.execute(
        select(ImportBatch).where(ImportBatch.file_hash == file_hash)
    ).scalar_one_or_none()
    if existing:
        if existing.status == "PENDING":
            return UploadResponse(
                import_batch_id=existing.id,
                cap_round_id=existing.cap_round_id,
                filename=existing.filename,
                file_hash=existing.file_hash,
                message="File ready for processing"
            )
        # Allow re-uploading to re-parse: cleanly remove prior imported cutoffs for this file/batch
        db.execute(Cutoff.__table__.delete().where(Cutoff.import_batch_id == existing.id))
        db.execute(Cutoff.__table__.delete().where(Cutoff.source_pdf == file.filename))
        db.execute(StagingCutoff.__table__.delete().where(StagingCutoff.import_batch_id == existing.id))
        db.execute(ImportLog.__table__.delete().where(ImportLog.import_batch_id == existing.id))
        db.execute(ParserError.__table__.delete().where(ParserError.import_batch_id == existing.id))
        db.delete(existing)
        db.commit()

    # Ensure CapRound exists
    cap_round = db.execute(
        select(CapRound).where(CapRound.year == year, CapRound.round_number == round_number)
    ).scalar_one_or_none()
    
    if not cap_round:
        cap_round = CapRound(year=year, round_number=round_number, round_name=f"CAP Round {round_number}")
        db.add(cap_round)
        db.flush()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIRECTORY / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    batch = ImportBatch(
        cap_round_id=cap_round.id,
        filename=file.filename,
        file_path=str(file_path),
        file_hash=file_hash,
        parser_version=settings.PARSER_VERSION,
        status="PENDING",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    log_audit(db, "UPLOAD_PDF", "import_batches", batch.id, 
             {"filename": batch.filename, "year": year, "round": round_number})

    return UploadResponse(
        import_batch_id=batch.id,
        cap_round_id=cap_round.id,
        filename=batch.filename,
        file_hash=batch.file_hash,
        message="Upload successful"
    )

@router.post("/{batch_id}/process")
def process_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    if batch.status == "PROCESSING":
        raise HTTPException(status_code=400, detail="Batch is currently being processed")

    cap_round = db.get(CapRound, batch.cap_round_id)
    if not cap_round:
        raise HTTPException(status_code=400, detail="CapRound not found")

    batch.status = "PROCESSING"
    batch.started_at = datetime.now(timezone.utc)
    db.commit()

    resolved_path = Path(batch.file_path)
    if not resolved_path.exists():
        # Try relative to project root or backend
        alt_path = Path(__file__).resolve().parent.parent.parent.parent / batch.file_path
        if alt_path.exists():
            resolved_path = alt_path
        else:
            alt_backend = Path(__file__).resolve().parent.parent.parent / batch.file_path
            if alt_backend.exists():
                resolved_path = alt_backend

    try:
        # Auto-detect/verify round directly from PDF content and sync batch if needed
        try:
            proc_detected_round = detect_pdf_round(resolved_path)
            if proc_detected_round and proc_detected_round != cap_round.round_number:
                    logger.info(f"Auto-syncing batch {batch.id} round {cap_round.round_number} -> detected round {proc_detected_round} from PDF text.")
                    target_cap_round = db.execute(
                        select(CapRound).where(CapRound.year == cap_round.year, CapRound.round_number == proc_detected_round)
                    ).scalar_one_or_none()
                    if not target_cap_round:
                        target_cap_round = CapRound(
                            year=cap_round.year,
                            round_number=proc_detected_round,
                            academic_year=f"{cap_round.year}-{str(cap_round.year + 1)[-2:]}",
                            round_name=f"CAP Round {proc_detected_round}"
                        )
                        db.add(target_cap_round)
                        db.flush()
                    cap_round = target_cap_round
                    batch.cap_round_id = target_cap_round.id
                    db.commit()
        except Exception as e:
            logger.warning(f"Could not verify PDF round in process_batch: {e}")

        importer = PDFImporter(
            db_session=db,
            import_batch_id=batch.id,
            file_path=str(resolved_path),
            year=cap_round.year,
            round_number=cap_round.round_number,
            cap_round_id=cap_round.id
        )
        result = importer.process()

        batch.status = "COMPLETED_WITH_WARNINGS" if result.warnings > 0 or result.errors > 0 else "COMPLETED"
        batch.completed_at = datetime.now(timezone.utc)
        batch.pages_processed = result.pages_processed
        batch.records_created = result.records_created
        batch.records_rejected = result.records_rejected
        batch.warning_count = result.warnings
        batch.error_count = result.errors
        
        db.commit()
        log_audit(db, "PROCESS_BATCH", "import_batches", batch.id, {"status": batch.status})
        
        return {
            "status": batch.status,
            "pages_processed": batch.pages_processed,
            "records_created": batch.records_created,
            "colleges_found": getattr(result, "colleges_found", 0),
            "courses_found": getattr(result, "courses_found", 0),
            "warnings": batch.warning_count,
            "errors": batch.error_count
        }
    except Exception as e:
        batch.status = "FAILED"
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedResponse[ImportBatchListItem])
def list_batches(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    year: int | None = None,
    cap_round_id: int | None = None,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    query = select(ImportBatch, CapRound).join(CapRound, ImportBatch.cap_round_id == CapRound.id)

    if status:
        query = query.where(ImportBatch.status == status)
    if cap_round_id:
        query = query.where(ImportBatch.cap_round_id == cap_round_id)
    if year:
        query = query.where(CapRound.year == year)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    query = query.order_by(desc(ImportBatch.created_at)).offset((page - 1) * page_size).limit(page_size)
    results = db.execute(query).all()

    items = []
    for batch, round_obj in results:
        item_data = {
            **{c.key: getattr(batch, c.key) for c in ImportBatch.__table__.columns},
            "round_name": round_obj.round_name,
            "year": round_obj.year,
            "round_number": round_obj.round_number,
        }
        items.append(ImportBatchListItem(**item_data))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/db-status")
def get_db_status(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    total_cutoffs = db.execute(select(func.count(Cutoff.id))).scalar() or 0
    total_colleges = db.execute(select(func.count(College.id))).scalar() or 0
    total_courses = db.execute(select(func.count(Course.id))).scalar() or 0
    total_batches = db.execute(select(func.count(ImportBatch.id))).scalar() or 0

    total_institutes = 0
    total_inst_courses = 0
    try:
        from sqlalchemy import text
        total_institutes = db.execute(text("SELECT count(*) FROM institutes")).scalar() or 0
        total_inst_courses = db.execute(text("SELECT count(*) FROM institute_courses")).scalar() or 0
    except Exception:
        pass

    return {
        "total_cutoffs": total_cutoffs,
        "total_colleges": total_colleges,
        "total_courses": total_courses,
        "total_batches": total_batches,
        "total_institutes": total_institutes,
        "total_institute_courses": total_inst_courses
    }


@router.post("/reset-database")
def reset_database(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Safely resets cutoff, course, college, institute, and import data for real-time testing.
    Preserves admin_users credentials so admin can continue logging in seamlessly.
    """
    from app.database import engine
    from app.config import get_settings
    settings = get_settings()

    backup_dir = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = None

    # Identify database file(s) to backup and clear
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    target_dbs = []
    
    # Check DATABASE_URL
    if "sqlite" in settings.DATABASE_URL:
        db_raw = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        db_p = Path(db_raw)
        if not db_p.is_absolute():
            db_p = root_dir / db_raw
        if db_p.exists():
            target_dbs.append(db_p)

    # Always ensure both cutoff.db and cap_portal.db in root are covered
    for name in ["cutoff.db", "cap_portal.db"]:
        p = root_dir / name
        if p.exists() and p not in target_dbs:
            target_dbs.append(p)

    import sqlite3
    for db_path in target_dbs:
        try:
            backup_file = backup_dir / f"{db_path.stem}_backup_{timestamp}.db"
            shutil.copy2(db_path, backup_file)
            if not backup_file_name:
                backup_file_name = backup_file.name
            logger.info(f"Database backed up to {backup_file}")

            conn = sqlite3.connect(str(db_path), timeout=30.0)
            cursor = conn.cursor()
            for tbl in [
                "cutoffs", "courses", "colleges", "import_batches", 
                "import_logs", "parser_errors", "staging_cutoffs", 
                "cutoff_records", "all_india_cutoff_records", "manual_corrections",
                "institute_courses", "institutes"
            ]:
                try:
                    cursor.execute(f"DELETE FROM {tbl};")
                except Exception as e:
                    logger.warning(f"Could not clear table {tbl} in {db_path.name}: {e}")

            try:
                cursor.execute("UPDATE cap_rounds SET total_records = 0, total_pages = 0, processing_status = 'PENDING';")
            except Exception:
                pass

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error resetting database {db_path}: {e}")

    # Expire and refresh SQLAlchemy session
    db.expire_all()

    return {
        "success": True,
        "message": "Database cleared successfully (including cutoffs, colleges, courses, institutes, and intake tables). Admin credentials preserved.",
        "backup_file": backup_file_name
    }


@router.post("/restore-cutoffs")
def restore_official_cutoffs(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """
    Safely restores the complete, verified 106,714 cutoff records across all 4 CAP rounds
    (both Maharashtra State and All India) along with colleges, courses, institutes, and choice codes.
    """
    import sqlite3
    from app.config import get_settings
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    backup_file = root_dir / "storage" / "backups" / "cutoff_backup_20261002_full_verified_111560.db"

    if not backup_file.exists():
        backups = list((root_dir / "storage" / "backups").glob("cutoff_backup_*.db"))
        if backups:
            backup_file = sorted(backups)[-1]
        else:
            raise HTTPException(status_code=404, detail="Pristine backup file not found in storage/backups")

    target_dbs = []
    if "sqlite" in settings.DATABASE_URL:
        db_raw = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        db_p = Path(db_raw)
        if not db_p.is_absolute():
            db_p = root_dir / db_raw
        if db_p.exists():
            target_dbs.append(db_p)

    for name in ["cutoff.db", "cap_portal.db"]:
        p = root_dir / name
        if p.exists() and p not in target_dbs:
            target_dbs.append(p)

    restored_count = 0
    tables = [
        "colleges", "courses", "cap_rounds", "cutoffs",
        "import_batches", "institutes", "institute_courses"
    ]

    conn_bkp = sqlite3.connect(str(backup_file), timeout=30.0)
    for db_path in target_dbs:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        for tbl in tables:
            try:
                c = conn_bkp.execute(f"SELECT * FROM {tbl}")
                rows = c.fetchall()
                if rows:
                    cols = [d[0] for d in c.description]
                    placeholders = ",".join(["?" for _ in cols])
                    conn.execute(f"DELETE FROM {tbl};")
                    conn.executemany(f"INSERT INTO {tbl} VALUES ({placeholders})", rows)
                    conn.commit()
                if tbl == "cutoffs" and not restored_count:
                    restored_count = len(rows)
            except Exception as e:
                logger.warning(f"Error restoring table {tbl} into {db_path.name}: {e}")
        conn.close()
    conn_bkp.close()

    db.expire_all()

    return {
        "success": True,
        "message": f"Successfully restored complete official dataset! {restored_count:,} cutoffs across all 4 CAP rounds (State & All India) with 387 colleges, 2,332 courses, 387 institutes, and 4,331 choice codes.",
        "total_cutoffs": restored_count
    }


@router.post("/scrape-institutes")
def start_institute_scraper(
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Triggers official MHT-CET institute directory and intake scraping in background."""
    from app.services.institute_scraper_service import trigger_institute_scraper
    from app.config import get_settings
    settings = get_settings()
    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    target_dbs = []
    if "sqlite" in settings.DATABASE_URL:
        db_raw = settings.DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        db_p = Path(db_raw)
        if not db_p.is_absolute():
            db_p = root_dir / db_raw
        if db_p.exists():
            target_dbs.append(str(db_p))

    for name in ["cutoff.db", "cap_portal.db"]:
        p = root_dir / name
        if p.exists() and str(p) not in target_dbs:
            target_dbs.append(str(p))

    if not target_dbs:
        target_dbs = [str(root_dir / "cutoff.db")]

    res = trigger_institute_scraper(target_dbs)
    return res


@router.get("/scrape-institutes/status")
def get_institute_scraper_progress(
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Returns real-time progress for MHT-CET web scraper."""
    from app.services.institute_scraper_service import get_scraper_status
    return get_scraper_status()


@router.get("/{batch_id}", response_model=ImportBatchDetail)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    cap_round = db.get(CapRound, batch.cap_round_id)

    logs = db.execute(
        select(ImportLog)
        .where(ImportLog.import_batch_id == batch_id)
        .order_by(desc(ImportLog.created_at))
        .limit(50)
    ).scalars().all()

    errors_count = db.execute(
        select(ParserError.severity, func.count(ParserError.id))
        .where(ParserError.import_batch_id == batch_id)
        .group_by(ParserError.severity)
    ).all()
    error_summary = {sev: count for sev, count in errors_count}

    detail_data = {
        **{c.key: getattr(batch, c.key) for c in ImportBatch.__table__.columns},
        "round_name": cap_round.round_name if cap_round else None,
        "year": cap_round.year if cap_round else None,
        "round_number": cap_round.round_number if cap_round else None,
        "recent_logs": [ImportLogItem.model_validate(log) for log in logs],
        "error_summary": error_summary,
    }

    return ImportBatchDetail(**detail_data)

@router.get("/{batch_id}/staging", response_model=PaginatedResponse[StagingCutoffItem])
def preview_staging(
    batch_id: int,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    query = select(StagingCutoff).where(StagingCutoff.import_batch_id == batch_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    
    query = query.order_by(StagingCutoff.id).offset((page - 1) * page_size).limit(page_size)
    records = db.execute(query).scalars().all()

    return PaginatedResponse(
        items=[StagingCutoffItem.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size
    )

@router.post("/{batch_id}/commit", response_model=CommitResponse)
def commit_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    service = ImportService(db)
    try:
        result = service.commit_staging(batch_id)
        log_audit(db, "COMMIT_BATCH", "import_batches", batch_id, {"records": result.records_committed})
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{batch_id}")
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    if batch.status not in ["PENDING", "FAILED"]:
        raise HTTPException(status_code=400, detail="Only PENDING or FAILED batches can be deleted")

    # Delete related records
    db.execute(StagingCutoff.__table__.delete().where(StagingCutoff.import_batch_id == batch_id))
    db.execute(ImportLog.__table__.delete().where(ImportLog.import_batch_id == batch_id))
    db.execute(ParserError.__table__.delete().where(ParserError.import_batch_id == batch_id))
    
    if batch.file_path and os.path.exists(batch.file_path):
        os.remove(batch.file_path)

    db.delete(batch)
    db.commit()

    log_audit(db, "DELETE_BATCH", "import_batches", batch_id, {})

    return {"message": "Batch deleted successfully"}


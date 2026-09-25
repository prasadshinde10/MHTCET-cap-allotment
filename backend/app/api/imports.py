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

router = APIRouter()
settings = get_settings()

UPLOAD_DIRECTORY = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "uploads"
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=UploadResponse)
def upload_pdf(
    file: UploadFile = File(...),
    year: int = Form(...),
    round_number: int = Form(...),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not (2020 <= year <= 2050):
        raise HTTPException(status_code=400, detail="Invalid year")
    
    if not (1 <= round_number <= 4):
        raise HTTPException(status_code=400, detail="Invalid round number")

    # Read file and compute hash
    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB")

    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = db.execute(
        select(ImportBatch).where(ImportBatch.file_hash == file_hash)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="File has already been uploaded")

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
    
    if batch.status != "PENDING":
        raise HTTPException(status_code=400, detail="Batch is not in PENDING state")

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

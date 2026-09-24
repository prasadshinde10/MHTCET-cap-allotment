from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import College, Course, Cutoff, ImportBatch
from pydantic import BaseModel

router = APIRouter()

class SystemSettings(BaseModel):
    app_version: str
    parser_version: str
    db_stats: dict
    storage_info: dict

@router.get("/", response_model=SystemSettings)
def get_settings(
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    total_colleges = db.execute(select(func.count(College.id))).scalar() or 0
    total_courses = db.execute(select(func.count(Course.id))).scalar() or 0
    total_cutoffs = db.execute(select(func.count(Cutoff.id))).scalar() or 0
    total_imports = db.execute(select(func.count(ImportBatch.id))).scalar() or 0
    
    last_import = db.execute(select(ImportBatch.created_at).order_by(ImportBatch.created_at.desc())).scalar()
    
    # Storage info is mocked for now
    
    return SystemSettings(
        app_version="1.0.0",
        parser_version="1.0.0",
        db_stats={
            "total_colleges": total_colleges,
            "total_courses": total_courses,
            "total_cutoffs": total_cutoffs,
            "total_imports": total_imports
        },
        storage_info={
            "upload_dir_size_mb": 0.0,
            "last_import_date": last_import.isoformat() if last_import else None
        }
    )

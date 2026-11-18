from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.auth.security import get_current_admin
from app.models import College, Course, Cutoff, ImportBatch
from app.config import get_settings as get_app_settings
from app.services.update_checker import check_github_releases
from pydantic import BaseModel

router = APIRouter()

class SystemSettings(BaseModel):
    app_version: str
    parser_version: str
    db_stats: dict
    storage_info: dict

class UpdateCheckResponse(BaseModel):
    current_version: str
    latest_version: str
    update_available: bool
    release_title: Optional[str] = None
    release_notes: Optional[str] = None
    published_at: Optional[str] = None
    release_url: Optional[str] = None
    download_url: Optional[str] = None
    asset_name: Optional[str] = None
    asset_size_mb: Optional[float] = None
    cached: Optional[bool] = False
    checked_at: Optional[int] = None
    error: Optional[str] = None

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
    
    cfg = get_app_settings()
    
    return SystemSettings(
        app_version=getattr(cfg, "APP_VERSION", "1.0.0"),
        parser_version=getattr(cfg, "PARSER_VERSION", "1.0.0"),
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

@router.get("/check-update", response_model=UpdateCheckResponse)
def check_for_updates(
    force_refresh: bool = Query(False, description="Bypass in-memory cache and re-query GitHub releases"),
    admin=Depends(get_current_admin)
):
    """
    Check if a newer release has been published on GitHub and return download details.
    """
    return check_github_releases(force_refresh=force_refresh)


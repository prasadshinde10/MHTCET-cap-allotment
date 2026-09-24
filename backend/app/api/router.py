from fastapi import APIRouter
from app.api import auth, dashboard, imports, cap_rounds, colleges, courses, cutoffs, analysis, parser_errors, audit_logs, settings

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(cap_rounds.router, prefix='/cap-rounds', tags=['cap-rounds'])
api_router.include_router(colleges.router, prefix='/colleges', tags=['colleges'])
api_router.include_router(courses.router, prefix='/courses', tags=['courses'])
api_router.include_router(cutoffs.router, prefix='/cutoffs', tags=['cutoffs'])
api_router.include_router(analysis.router, prefix='/analysis', tags=['analysis'])
api_router.include_router(parser_errors.router, prefix='/parser-errors', tags=['parser-errors'])
api_router.include_router(audit_logs.router, prefix='/audit-logs', tags=['audit-logs'])
api_router.include_router(settings.router, prefix='/settings', tags=['settings'])

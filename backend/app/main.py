from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import os

from app.api.router import api_router
from app.api.health import router as health_router
from app.config import get_settings
from app.database import engine, SessionLocal
from app.models.base import Base
from app.auth.seed import seed_admin_user
from app.auth.middleware import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)

    # Ensure database schema tables exist
    Base.metadata.create_all(bind=engine)

    # Seed admin user on startup
    db = SessionLocal()
    try:
        seed_admin_user(db)
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
    finally:
        db.close()
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title="MHT-CET CAP Cutoff Admin Portal",
    description="Admin portal for managing MHT-CET Engineering CAP cutoff data",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/api/redoc" if settings.APP_ENV == "development" else None,
    openapi_url="/api/openapi.json" if settings.APP_ENV == "development" else None,
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — locked down
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# Trusted host middleware in production
if settings.APP_ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.CORS_ORIGINS,
    )

# Mount health at root level (no auth required)
app.include_router(health_router, prefix="/health", tags=["health"])

# Mount all API routes under /api
app.include_router(api_router, prefix="/api")

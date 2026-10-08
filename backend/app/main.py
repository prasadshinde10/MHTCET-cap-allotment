from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import os

# Router configurations
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
    # Ensure database schema migrations run safely in isolated transactions
    if engine.dialect.name == "postgresql":
        migration_stmts = [
            "ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS total_pages INTEGER DEFAULT 0;",
            "ALTER TABLE colleges ALTER COLUMN minority_status TYPE VARCHAR(200);",
            "ALTER TABLE colleges ALTER COLUMN minority_type TYPE VARCHAR(200);",
            "ALTER TABLE colleges ALTER COLUMN college_type TYPE VARCHAR(200);",
            "ALTER TABLE colleges ALTER COLUMN funding_type TYPE VARCHAR(200);",
            "ALTER TABLE colleges ALTER COLUMN status TYPE VARCHAR(50);",
            "ALTER TABLE colleges ALTER COLUMN college_name TYPE VARCHAR(500);",
            "ALTER TABLE colleges ALTER COLUMN home_university TYPE VARCHAR(300);",
            "ALTER TABLE colleges ALTER COLUMN city TYPE VARCHAR(200);",
            "ALTER TABLE colleges ALTER COLUMN district TYPE VARCHAR(200);",
            "ALTER TABLE courses ALTER COLUMN course_name TYPE VARCHAR(500);",
            "ALTER TABLE courses ALTER COLUMN course_code TYPE VARCHAR(50);"
        ]
        for stmt in migration_stmts:
            try:
                with engine.begin() as conn:
                    conn.exec_driver_sql(stmt)
            except Exception as e:
                logger.info(f"Schema migration statement note: {stmt} -> {e}")
    else:
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql("ALTER TABLE import_batches ADD COLUMN total_pages INTEGER DEFAULT 0;")
        except Exception:
            pass

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

# CORS — Allow credentials with dynamic origin matching for Cloudflare & local dev
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Authorization"],
    max_age=600,
)


# Trusted host middleware in production
if settings.APP_ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],
    )

# Mount health at root level (no auth required)
app.include_router(health_router, prefix="/health", tags=["health"])

# Mount all API routes under /api
app.include_router(api_router, prefix="/api")

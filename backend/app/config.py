from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./cap_portal.db"

    # Authentication
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = ""
    ADMIN_PASSWORD_HASH: str = "$2b$12$vCg5FomS/gQ5in6ZQmeKHedz8vVk8N7fStXChyqy5WLFERBsWcXtC"  # default: Admin@12345
    SECRET_KEY: str = "cap_super_secret_jwt_key_development_change_in_prod"
    JWT_EXPIRY_HOURS: int = 8

    # Application development
    APP_ENV: str = "production"
    APP_VERSION: str = "1.0.0"
    PARSER_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = [
        "*",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # File Storage
    UPLOAD_DIRECTORY: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    # Rate Limiting
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=[str(ROOT_DIR / ".env"), ".env", "backend/.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

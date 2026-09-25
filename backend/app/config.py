from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Authentication
    ADMIN_USERNAME: str
    ADMIN_EMAIL: str
    ADMIN_PASSWORD_HASH: str
    SECRET_KEY: str
    JWT_EXPIRY_HOURS: int = 8

    # Application
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    PARSER_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = [
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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

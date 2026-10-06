from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

import os
from pathlib import Path

settings = get_settings()

connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30.0
    # If using relative sqlite path, resolve to project root directory
    if "sqlite:///./" in db_url:
        db_filename = db_url.split("sqlite:///./")[-1]
        db_file = Path(__file__).resolve().parent.parent.parent / db_filename
        db_url = f"sqlite:///{db_file.as_posix()}"
    elif db_url == "sqlite:///cap_portal.db":
        db_file = Path(__file__).resolve().parent.parent.parent / "cap_portal.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args=connect_args)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
else:
    # Supabase connection URL normalization (postgres:// -> postgresql://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


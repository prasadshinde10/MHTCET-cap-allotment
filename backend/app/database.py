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
    if "sqlite:///" in db_url:
        db_raw_name = db_url.replace("sqlite:///./", "").replace("sqlite:///", "")
        app_file = Path(__file__).resolve().parent.parent / db_raw_name
        root_file = Path(__file__).resolve().parent.parent.parent / db_raw_name
        cwd_file = Path.cwd() / db_raw_name

        if app_file.exists():
            resolved_file = app_file
        elif root_file.exists():
            resolved_file = root_file
        elif cwd_file.exists():
            resolved_file = cwd_file
        else:
            resolved_file = app_file

        db_url = f"sqlite:///{resolved_file.as_posix()}"
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


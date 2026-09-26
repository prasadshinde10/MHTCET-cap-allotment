from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

import os
from pathlib import Path

settings = get_settings()

connect_args = {}
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # If using relative sqlite path, resolve to project root directory
    if "sqlite:///./" in db_url:
        db_filename = db_url.split("sqlite:///./")[-1]
        db_file = Path(__file__).resolve().parent.parent.parent / db_filename
        db_url = f"sqlite:///{db_file.as_posix()}"
    elif db_url == "sqlite:///cap_portal.db":
        db_file = Path(__file__).resolve().parent.parent.parent / "cap_portal.db"
        db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args=connect_args)
else:
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

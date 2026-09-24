@echo off
title MHT-CET CAP Cutoff Admin Portal Launcher
echo ============================================================
echo   MHT-CET CAP Cutoff Admin Portal - Local Launcher
echo ============================================================
echo.

echo 1. Initializing Local Database (SQLite)...
set PYTHONPATH=%~dp0backend
python -c "from app.database import engine, SessionLocal; from app.models.base import Base; import app.models; from app.auth.seed import seed_admin_user; Base.metadata.create_all(bind=engine); db=SessionLocal(); seed_admin_user(db); db.close()"

echo.
echo 2. Starting Backend Server on http://localhost:8000 ...
start "Backend Server (FastAPI)" cmd /k "cd /d %~dp0backend && set PYTHONPATH=%~dp0backend && python -m uvicorn app.main:app --port 8000 --reload"

echo.
echo 3. Starting Frontend Dev Server on http://localhost:3000 ...
start "Frontend Server (Vite React)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo   Portal is starting up!
echo   Open your browser at: http://localhost:3000
echo   Default Admin Login:
echo     Username: admin
echo     Password: admin123
echo ============================================================
echo.
pause

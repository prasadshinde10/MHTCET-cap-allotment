Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MHT-CET CAP Cutoff Admin Portal - Local Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "1. Initializing Local Database (SQLite)..." -ForegroundColor Yellow
$env:PYTHONPATH = "$root\backend"
python -c "from app.database import engine, SessionLocal; from app.models.base import Base; import app.models; from app.auth.seed import seed_admin_user; Base.metadata.create_all(bind=engine); db=SessionLocal(); seed_admin_user(db); db.close()"

Write-Host "2. Starting Backend Server on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; `$env:PYTHONPATH='$root\backend'; python -m uvicorn app.main:app --port 8000 --reload"

Write-Host "3. Starting Frontend Dev Server on http://localhost:3000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Portal is running!" -ForegroundColor Green
Write-Host "  Browser URL : http://localhost:3000" -ForegroundColor White
Write-Host "  Admin Login : admin / admin123" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

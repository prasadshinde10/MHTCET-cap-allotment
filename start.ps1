Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MHT-CET CAP Cutoff Admin Portal - Local Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Environment file check
if (-not (Test-Path "$root\.env")) {
    if (Test-Path "$root\.env.example") {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Cyan
        Copy-Item "$root\.env.example" "$root\.env"
    }
}

# 2. Database preparation
Write-Host "1. Initializing Local Database (SQLite)..." -ForegroundColor Yellow
$env:PYTHONPATH = "$root\backend"
python -c "from app.database import engine, SessionLocal; from app.models.base import Base; import app.models; from app.auth.seed import seed_admin_user; Base.metadata.create_all(bind=engine); db=SessionLocal(); seed_admin_user(db); db.close()"

# 3. Frontend node_modules check
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies (first-time setup)..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    npm install --legacy-peer-deps
    Pop-Location
}

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

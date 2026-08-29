# RRASE College AI Assistant - Windows local setup helper (PowerShell)
# Run from the project root: rrase-college-ai\
#
# This automates the steps described in README.md section "Local Development".
# It assumes Python 3.11+, PostgreSQL, and (later, for Phase 5) Ollama are
# already installed.

Write-Host "== RRASE College AI Assistant: local setup ==" -ForegroundColor Cyan

Set-Location backend

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example (edit this with your real values!)" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Edit backend\.env with your real PostgreSQL credentials."
Write-Host "  2. Create the PostgreSQL database (see README.md)."
Write-Host "  3. Run migrations:   alembic upgrade head"
Write-Host "  4. Seed roles:       python scripts\seed_roles.py"
Write-Host "  5. Start the API:    uvicorn app.main:app --reload --port 8000"
Write-Host "  6. Open frontend\index.html in your browser (or serve it, e.g. VS Code Live Server)."

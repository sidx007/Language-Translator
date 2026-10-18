Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          LinguaSync - 100% Local AI Voice Translator" -ForegroundColor Green
Write-Host "               Optimized for 8GB RAM CPU Systems" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
# Automatically detect and activate virtual environment if present
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment (venv)..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} elseif (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment (.venv)..." -ForegroundColor Green
    & ".\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[NOTE] No virtual environment detected. Running with system Python." -ForegroundColor Yellow
    Write-Host "To create one: python -m venv venv ; .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
}

Write-Host "Starting FastAPI Backend Server on http://127.0.0.1:8000 ..." -ForegroundColor White
Start-Process "http://127.0.0.1:8000"
python server.py

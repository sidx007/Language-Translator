@echo off
title LinguaSync - Local AI Translator Backend (8GB RAM Mode)
echo =====================================================================
echo           LinguaSync - 100%% Local AI Voice Translator
echo                Optimized for 8GB RAM CPU Systems
echo =====================================================================
echo.
:: Automatically detect and activate virtual environment if present
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else (
    echo [NOTE] No virtual environment detected. Running with system Python.
    echo To create one: python -m venv venv ^&^& venv\Scripts\activate
)

echo Starting FastAPI Backend Server on http://127.0.0.1:8000 ...
echo.
start http://127.0.0.1:8000
python server.py
pause

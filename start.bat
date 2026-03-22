@echo off
echo ============================================
echo  Boomi Process Reviewer - Starting...
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "backend\__pycache__" (
    echo Installing dependencies...
    pip install -r backend\requirements.txt
    echo.
)

REM Create data directory
if not exist "data" mkdir data

echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop.
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause

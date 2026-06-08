@echo off
REM Quick launcher for Unified AI Pipeline
REM Activates venv and starts the server

echo.
echo =========================================
echo Unified AI Talking Head Pipeline Launcher
echo =========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup_unified_pipeline.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Checking dependencies...
.\venv\Scripts\python.exe -c "import torch; print('✓ PyTorch OK'); print('  GPU:', 'Available' if torch.cuda.is_available() else 'CPU Only')"
.\venv\Scripts\python.exe -c "import flask; print('✓ Flask OK')"

echo.
echo =========================================
echo Starting Unified Pipeline Server
echo =========================================
echo.
echo Server will be available at:
echo   http://localhost:5000/live_chunk
echo.
echo Press Ctrl+C to stop the server
echo.
echo =========================================
echo.

.\venv\Scripts\python.exe app_unified_backend.py

pause

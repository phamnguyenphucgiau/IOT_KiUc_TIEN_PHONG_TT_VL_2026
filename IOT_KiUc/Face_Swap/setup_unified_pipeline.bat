@echo off
REM Unified AI Talking Head Pipeline - Setup Script
REM Windows batch file for automatic setup

echo.
echo ============================================
echo AI Talking Head - Unified Pipeline Setup
echo ============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Python found: 
python --version
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if not exist "venv_unified" (
    python -m venv venv_unified
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv_unified\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated
echo.

REM Upgrade pip
echo [4/5] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo WARNING: pip upgrade had issues (usually safe to continue)
)
echo.

REM Install PyTorch
echo [5/5] Installing PyTorch and dependencies...
echo.
echo Checking GPU availability...
python -c "import torch; print('GPU Available' if torch.cuda.is_available() else 'CPU Only')"
echo.

set /p install_choice="Do you have an NVIDIA GPU? (y/n): "
if /i "%install_choice%"=="y" (
    echo Installing PyTorch with CUDA support...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Installing PyTorch with CPU support...
    pip install torch torchvision torchaudio
)
echo.

REM Install requirements
echo Installing unified pipeline requirements...
pip install -r requirements_unified.txt
if errorlevel 1 (
    echo WARNING: Some packages may have failed to install
    echo This is sometimes normal - check the output above
)
echo.

REM Verify installation
echo.
echo ============================================
echo Setup Verification
echo ============================================
echo.

python -c "import torch; print('✓ PyTorch:', torch.__version__)"
python -c "import torch; print('✓ GPU Available:', torch.cuda.is_available())"
python -c "import flask; print('✓ Flask installed')"
python -c "import cv2; print('✓ OpenCV installed')"
echo.

echo.
echo ============================================
echo ✓ Setup Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Download SadTalker checkpoints (if not already present):
echo    cd SadTalker
echo    REM Download from: https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/checkpoints.zip
echo    cd ..
echo.
echo 2. Download VideoReTalking checkpoints (if not already present):
echo    cd video-retalking
echo    REM Download from: https://github.com/OpenTalker/video-retalking/releases/download/v0.0.1/checkpoints.zip
echo    cd ..
echo.
echo 3. Start the web server:
echo    python app_unified_backend.py
echo.
echo 4. Open your browser:
echo    http://localhost:5000
echo.
echo ============================================
echo.

set /p start_server="Start the web server now? (y/n): "
if /i "%start_server%"=="y" (
    echo.
    echo Starting Flask server...
    echo Open http://localhost:5000 in your browser
    echo.
    python app_unified_backend.py
) else (
    echo.
    echo To start the server later, run:
    echo python app_unified_backend.py
    echo.
)

pause

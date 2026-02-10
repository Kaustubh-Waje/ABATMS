@echo off
REM ============================================
REM Intelligent Traffic Management System
REM One-Click Environment Setup Script
REM ============================================

echo.
echo ============================================
echo  INTELLIGENT TRAFFIC MANAGEMENT SYSTEM
echo  Environment Setup Script
echo ============================================
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found

REM Check SUMO installation
echo.
echo [2/5] Checking SUMO installation...
if defined SUMO_HOME (
    echo [OK] SUMO_HOME is set to: %SUMO_HOME%
) else (
    echo [WARNING] SUMO_HOME environment variable is not set
    echo.
    echo Please set SUMO_HOME to your SUMO installation directory:
    echo   - Default location: C:\Program Files (x86)\Eclipse\Sumo
    echo.
    echo To set permanently:
    echo   1. Open System Properties - Environment Variables
    echo   2. Add new System Variable: SUMO_HOME
    echo   3. Set value to your SUMO installation path
    echo.
    set /p SUMO_PATH="Enter SUMO path (or press Enter to skip): "
    if not "%SUMO_PATH%"=="" (
        set SUMO_HOME=%SUMO_PATH%
        echo [OK] SUMO_HOME set temporarily to: %SUMO_PATH%
    )
)

REM Create virtual environment
echo.
echo [3/5] Setting up Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo [4/5] Installing Python dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Create output directory
echo.
echo [5/5] Creating output directories...
if not exist "output" mkdir output
echo [OK] Output directory ready

echo.
echo ============================================
echo  SETUP COMPLETE!
echo ============================================
echo.
echo To run the simulation:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python src/main.py --mode adaptive
echo.
echo To launch the dashboard:
echo   streamlit run dashboard/app.py
echo.
echo Available commands:
echo   python src/main.py --help          Show all options
echo   python src/main.py --mode adaptive Run adaptive control
echo   python src/main.py --mode fixed    Run fixed-time control
echo   python src/main.py --compare       Compare both modes
echo   python src/main.py --test-connection  Test SUMO connection
echo.
pause

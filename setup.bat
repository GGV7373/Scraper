@echo off

REM Simple setup for native installation on Windows
echo Setting up Web Scraper...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Remove old virtual environment
if exist ".venv" (
    echo Removing old virtual environment...
    rmdir /s /q .venv
)

REM Create fresh virtual environment
echo Creating virtual environment...
python -m venv .venv

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip first
echo Upgrading pip...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create output directory
if not exist "output" mkdir output

REM Create simple launcher
echo @echo off > launch.bat
echo cd /d "%%~dp0" >> launch.bat
echo call .venv\Scripts\activate.bat >> launch.bat
echo python main.py >> launch.bat
echo pause >> launch.bat

echo Setup complete!
echo.
echo To run the scraper:
echo   launch.bat
pause
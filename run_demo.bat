@echo off
REM Django Orbit - Quick Demo Setup (Windows)
REM 
REM This script sets up everything needed for a demo:
REM 1. Creates virtual environment
REM 2. Installs dependencies
REM 3. Runs migrations
REM 4. Creates sample data
REM 5. Starts the server

echo.
echo ================================================
echo   Django Orbit - Demo Setup
echo ================================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate and install
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install django requests -q
pip install -e . -q

REM Migrations
echo Running migrations...
python manage.py migrate --run-syncdb -v 0

REM Setup demo data
echo Creating demo data...
python demo.py setup

echo.
echo ================================================
echo   Ready! Starting server...
echo ================================================
echo.
echo   Demo:  http://localhost:8000/
echo   Orbit: http://localhost:8000/orbit/
echo.
echo   To simulate activity (in another terminal):
echo   python demo.py simulate
echo.
echo ================================================
echo.

python manage.py runserver

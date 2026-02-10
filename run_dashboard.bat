@echo off
echo Starting Traffic Management Dashboard...
echo.
echo 1. Starting Backend API Server...
start "" http://localhost:8000
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
pause

@echo off
REM CareLoop one-command demo launcher for Windows (for recording the demo video).
REM Usage: demo.bat [grace_minutes]   (default 30; pass 1 for the escalation shot)
set GRACE=%1
if "%GRACE%"=="" set GRACE=30

echo ==^> Backend (grace %GRACE% min)...
if not exist backend\.venv (
  py -m venv backend\.venv
)
backend\.venv\Scripts\pip install -q -r backend\requirements.txt
set CARELOOP_GRACE_MINUTES=%GRACE%
start "careloop-backend" backend\.venv\Scripts\uvicorn app.main:app --port 8000 --app-dir backend

echo ==^> Frontend...
if not exist frontend\node_modules (
  cd frontend && npm install && cd ..
)
start "careloop-frontend" /D frontend npm run dev

echo.
echo CareLoop is up:
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo Close the two new windows to stop.

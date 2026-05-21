@echo off
:: ============================================================
::  start-local.bat — LOCAL DEVELOPMENT startup
::
::  Starts the FastAPI backend (port 8000) and the Next.js
::  frontend (port 3000) in separate terminal windows.
::
::  Usage:
::    start-local.bat
:: ============================================================

setlocal

set ROOT=%~dp0
set VENV=%ROOT%.venv\Scripts

:: ── Ensure frontend .env.local points to localhost ──────────
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > "%ROOT%frontend\.env.local"
echo NEXT_PUBLIC_APP_ENV=local >> "%ROOT%frontend\.env.local"

:: ── Backend ─────────────────────────────────────────────────
echo [ParkSmart] Starting FastAPI backend on http://localhost:8000 ...
start "ParkSmart Backend" cmd /k "cd /d %ROOT% && call %VENV%\activate.bat && python -m uvicorn src.api.server:app --reload --port 8000"

:: Short pause so backend starts before frontend connects
timeout /t 2 /nobreak >nul

:: ── Frontend ─────────────────────────────────────────────────
echo [ParkSmart] Starting Next.js frontend on http://localhost:3000 ...
start "ParkSmart Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo.
echo ============================================================
echo  LOCAL DEVELOPMENT running
echo  Frontend : http://localhost:3000
echo  Backend  : http://localhost:8000
echo  API docs : http://localhost:8000/docs
echo ============================================================
echo.
echo  Close the two terminal windows to stop the servers.
echo.

endlocal

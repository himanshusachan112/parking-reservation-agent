@echo off
:: ============================================================
::  start-demo.bat — PUBLIC DEMO startup with ngrok support
::
::  Starts backend + frontend, then configures the frontend to
::  talk to your ngrok backend URL.
::
::  Usage (two ways):
::
::    1. Pass ngrok URL as argument (non-interactive):
::       start-demo.bat https://abc123.ngrok-free.app
::
::    2. Run without argument — script prompts you:
::       start-demo.bat
::
::  Prerequisites:
::    - ngrok installed and authenticated
::    - See docs/NGROK_SETUP.md for setup instructions
:: ============================================================

setlocal enabledelayedexpansion

set ROOT=%~dp0
set VENV=%ROOT%.venv\Scripts

:: ── Get ngrok backend URL ─────────────────────────────────
if not "%~1"=="" (
    set NGROK_BACKEND=%~1
) else (
    echo.
    echo ============================================================
    echo  ParkSmart — PUBLIC DEMO SETUP
    echo ============================================================
    echo.
    echo  Step 1: Open a separate terminal and run:
    echo    ngrok http 8000
    echo.
    echo  Step 2: Copy the Forwarding URL shown by ngrok.
    echo    Example:  https://abc123.ngrok-free.app
    echo.
    set /p NGROK_BACKEND="  Paste your ngrok backend URL here: "
)

:: Strip trailing slash if present
if "!NGROK_BACKEND:~-1!"=="/" set NGROK_BACKEND=!NGROK_BACKEND:~0,-1!

:: Validate it looks like a URL
if "!NGROK_BACKEND!"=="" (
    echo [ERROR] No ngrok URL provided. Exiting.
    exit /b 1
)

:: ── Write frontend .env.local with ngrok backend URL ─────
echo Writing frontend environment for DEMO mode...
echo NEXT_PUBLIC_API_URL=!NGROK_BACKEND!  > "%ROOT%frontend\.env.local"
echo NEXT_PUBLIC_APP_ENV=demo            >> "%ROOT%frontend\.env.local"

:: Also update backend CORS to allow the ngrok frontend URL
:: (ngrok frontend URL is typically the same host with :3000 or a separate tunnel)
:: The backend reads CORS_ORIGINS from .env — update it here.
echo Updating backend CORS_ORIGINS in .env ...
:: Append/replace CORS_ORIGINS line in .env (simple approach: append if not present)
findstr /C:"CORS_ORIGINS" "%ROOT%.env" >nul 2>&1
if errorlevel 1 (
    echo CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,!NGROK_BACKEND! >> "%ROOT%.env"
) else (
    powershell -Command "(Get-Content '%ROOT%.env') -replace '^CORS_ORIGINS=.*', 'CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,!NGROK_BACKEND!' | Set-Content '%ROOT%.env'"
)

:: ── Start Backend ─────────────────────────────────────────
echo.
echo [ParkSmart] Starting FastAPI backend on http://localhost:8000 ...
start "ParkSmart Backend (Demo)" cmd /k "cd /d %ROOT% && call %VENV%\activate.bat && python -m uvicorn src.api.server:app --reload --port 8000"

timeout /t 2 /nobreak >nul

:: ── Start Frontend ────────────────────────────────────────
echo [ParkSmart] Starting Next.js frontend on http://localhost:3000 ...
start "ParkSmart Frontend (Demo)" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo.
echo ============================================================
echo  PUBLIC DEMO running
echo.
echo  Backend (local)  : http://localhost:8000
echo  Frontend (local) : http://localhost:3000
echo  Backend (public) : !NGROK_BACKEND!
echo.
echo  NEXT STEPS:
echo   1. Expose the frontend too (optional):
echo      In a new terminal:  ngrok http 3000
echo   2. Share the ngrok frontend URL with your audience.
echo.
echo  The yellow demo banner is visible on all pages.
echo ============================================================
echo.

endlocal

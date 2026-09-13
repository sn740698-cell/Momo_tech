@echo off
setlocal enabledelayedexpansion
title MOMO Fullstack Server Launcher

:: 1. Normalize Root Directory (strip trailing backslash)
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\Backend"
set "FRONTEND_DIR=%ROOT_DIR%\Frontend"

echo ========================================================
echo             MOMO Fullstack Server Launcher
echo ========================================================
echo Project Directory: %ROOT_DIR%
echo.

:: 2. Verify Node.js and npm Environment
echo [1/4] Checking Node.js and Frontend setup...
if exist "C:\Program Files\nodejs" (
    set "PATH=C:\Program Files\nodejs;!PATH!"
)
where npm >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] npm was not found in PATH or C:\Program Files\nodejs!
    echo Please install Node.js from https://nodejs.org/ and re-run.
    pause
    exit /b 1
)
echo   * Node.js and npm detected.

:: 3. Verify Python Virtual Environment
echo.
echo [2/4] Checking Backend setup...
if not exist "%BACKEND_DIR%\manage.py" (
    echo [ERROR] Backend\manage.py could not be found at:
    echo "%BACKEND_DIR%\manage.py"
    pause
    exit /b 1
)

set "PY_CMD=python"
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
    echo   * Using Python venv: Backend\venv\Scripts\python.exe
) else (
    echo   * Using system Python
)

:: 4. Launch USB-C Hardware Companion Bridge
echo.
echo [3/4] Starting USB-C Hardware Companion Bridge...
start "MOMO ESP32 USB-C Bridge" /D "%BACKEND_DIR%" cmd /k "%PY_CMD% -m iot.serial_bridge"

:: 5. Launch Servers
echo.
echo [4/4] Launching Servers...
echo   * Starting Django Backend on http://127.0.0.1:8000 ...
start "Django Backend Server (Port 8000)" /D "%BACKEND_DIR%" cmd /k "%PY_CMD% manage.py runserver 127.0.0.1:8000"

echo   * Starting React Frontend on http://localhost:5173 ...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo   * Installing frontend dependencies...
    cd /d "%FRONTEND_DIR%"
    call npm install
    cd /d "%ROOT_DIR%"
)
start "React Frontend Server (Port 5173)" /D "%FRONTEND_DIR%" cmd /k "call npm run dev -- --host 127.0.0.1"

:: 6. Fast Health Verification
echo   * Verifying servers are coming online...
set "BACKEND_UP=0"
for /L %%i in (1,1,10) do (
    if !BACKEND_UP! equ 0 (
        ping 127.0.0.1 -n 1 >nul
        curl.exe -s http://127.0.0.1:8000/api/status/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_UP=1"
            echo   * [OK] Django Backend is online and ready!
        )
    )
)

set "FRONTEND_UP=0"
for /L %%i in (1,1,10) do (
    if !FRONTEND_UP! equ 0 (
        ping 127.0.0.1 -n 1 >nul
        curl.exe -s -I http://127.0.0.1:5173/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "FRONTEND_UP=1"
            echo   * [OK] React Frontend is online and ready!
        )
    )
)

:: 7. Open Browser
echo.
echo ========================================================
echo  All systems initialized successfully!
echo   - Backend API: http://127.0.0.1:8000/api/
echo   - Frontend:    http://localhost:5173/
echo   - ESP32 Body:  USB-C COM Port Listening
echo ========================================================
echo Opening browser...
start "" "http://localhost:5173/"

echo.
echo Note: Keep the server windows open while developing.
echo You may close this launcher window at any time.
echo.
pause

@echo off
setlocal enabledelayedexpansion
title MOMO Fullstack Launcher

cd /d "%~dp0"
set "ROOT_DIR=%~dp0"

echo ========================================================
echo             MOMO Fullstack Server Launcher
echo ========================================================
echo Project Directory: %ROOT_DIR%
echo.

REM 1. Verify Node.js and npm
echo [1/4] Checking Node.js & Frontend setup...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\nodejs\npm.cmd" (
        set "PATH=C:\Program Files\nodejs;%PATH%"
    )
)
where node >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\nodejs\node.exe" (
        set "PATH=C:\Program Files\nodejs;%PATH%"
    )
)

where npm >nul 2>&1
if %errorlevel% equ 0 (
    echo   * Node.js and npm detected.
) else (
    echo [ERROR] npm was not found! Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM 2. Verify Python Virtual Environment
echo.
echo [2/4] Checking Backend setup...
if not exist "%ROOT_DIR%Backend\manage.py" (
    echo [ERROR] Backend\manage.py could not be found at:
    echo "%ROOT_DIR%Backend\manage.py"
    pause
    exit /b 1
)

set "PYTHON_EXE=python"
if exist "%ROOT_DIR%Backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%Backend\venv\Scripts\python.exe"
    echo   * Using Python venv: Backend\venv\Scripts\python.exe
) else (
    echo   * Using system Python
)

REM 3. Launch USB-C Hardware Serial Bridge
echo.
echo [3/4] Starting USB-C Hardware Companion Bridge...
start "MOMO ESP32 USB-C Bridge" cmd /k "cd /d "%ROOT_DIR%Backend" && "%PYTHON_EXE%" -m iot.serial_bridge"

REM 4. Launch Backend in a separate window
echo.
echo [4/4] Launching Servers...
echo   * Starting Django Backend on http://127.0.0.1:8000 ...
start "Django Backend Server (Port 8000)" cmd /k "cd /d "%ROOT_DIR%Backend" && "%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000"

echo   * Waiting for Django Backend to respond...
set "BACKEND_UP=0"
for /L %%i in (1,1,15) do (
    if !BACKEND_UP! equ 0 (
        ping 127.0.0.1 -n 2 >nul
        curl.exe -s http://127.0.0.1:8000/api/status/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_UP=1"
            echo   * [OK] Django Backend is online and ready!
        )
    )
)

REM 5. Launch Frontend in a separate window
echo   * Starting React Frontend on http://localhost:5173 ...
if not exist "%ROOT_DIR%Frontend\node_modules" (
    echo   * Installing frontend dependencies...
    cd /d "%ROOT_DIR%Frontend"
    call npm install
    cd /d "%ROOT_DIR%"
)

start "React Frontend Server (Port 5173)" cmd /k "cd /d "%ROOT_DIR%Frontend" && call npm run dev -- --host 127.0.0.1"

echo   * Waiting for React Frontend server to become ready...
set "FRONTEND_UP=0"
for /L %%i in (1,1,20) do (
    if !FRONTEND_UP! equ 0 (
        ping 127.0.0.1 -n 2 >nul
        curl.exe -s -I http://127.0.0.1:5173/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "FRONTEND_UP=1"
            echo   * [OK] React Frontend is online and ready!
        )
    )
)

REM 6. Open browser
echo.
echo ========================================================
echo  All systems started successfully!
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

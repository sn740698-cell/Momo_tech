@echo off
setlocal
title MOMO Fullstack Launcher

cd /d "%~dp0"
set "ROOT_DIR=%~dp0"

echo ========================================================
echo             MOMO Fullstack Server Launcher
echo ========================================================
echo Project Directory: %ROOT_DIR%
echo.

REM 1. Verify and configure Python / Virtual Environment
echo [1/4] Checking Backend setup...
if not exist "%ROOT_DIR%Backend\manage.py" (
    echo [ERROR] Backend\manage.py could not be found at:
    echo "%ROOT_DIR%Backend\manage.py"
    pause >nul
    exit /b 1
)

set "PYTHON_EXE=python"
if exist "%ROOT_DIR%Backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%Backend\venv\Scripts\python.exe"
    echo   * Using Python venv: Backend\venv\Scripts\python.exe
) else (
    echo   * Using system Python
)

REM 2. Launch USB-C Hardware Serial Bridge
echo.
echo [2/4] Starting USB-C Hardware Companion Bridge...
start "MOMO ESP32 USB-C Bridge" /D "%ROOT_DIR%Backend" cmd /k ""%PYTHON_EXE%" -m iot.serial_bridge"

REM 3. Launch Backend in a separate window
echo.
echo [3/4] Launching Servers...
echo   * Starting Django Backend on http://127.0.0.1:8000 ...
start "Django Backend Server (Port 8000)" /D "%ROOT_DIR%Backend" cmd /k ""%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000"

ping 127.0.0.1 -n 3 >nul

REM 4. Launch Frontend in a separate window
echo   * Starting React Frontend on http://localhost:5173 ...
start "React Frontend Server (Port 5173)" /D "%ROOT_DIR%Frontend" cmd /k "npm run dev"

ping 127.0.0.1 -n 4 >nul

REM 5. Open browser
echo.
echo ========================================================
echo  All systems started successfully!
echo   - Backend API: http://127.0.0.1:8000/api/
echo   - Frontend:    http://localhost:5173/
echo   - ESP32 Body:  USB-C COM Port Listening
echo ========================================================
echo Opening browser...
start http://localhost:5173/

echo.
echo Note: Keep the server windows open while developing.
echo You may close this launcher window at any time.
echo.
pause

@echo off
setlocal
title MOMO Fullstack Launcher

cd /d "%~dp0"

REM Resolve project root directory dynamically
if exist "%~dp0Backend\manage.py" (
    for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI\"
) else if exist "%~dp0..\Backend\manage.py" (
    for %%I in ("%~dp0..") do set "ROOT_DIR=%%~fI\"
) else (
    set "ROOT_DIR=%~dp0"
)

echo ========================================================
echo             MOMO Fullstack Server Launcher
echo ========================================================
echo Project Directory: %ROOT_DIR%
echo.

REM 1. Verify and configure Python / Virtual Environment
echo [1/3] Checking Backend setup...
if not exist "%ROOT_DIR%Backend\manage.py" (
    echo [ERROR] Backend\manage.py could not be found at:
    echo "%ROOT_DIR%Backend\manage.py"
    echo.
    echo Press any key to exit...
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

REM 2. Verify Frontend setup
echo.
echo [2/3] Checking Frontend setup...
if not exist "%ROOT_DIR%Frontend\package.json" (
    echo [ERROR] Frontend\package.json could not be found at:
    echo "%ROOT_DIR%Frontend\package.json"
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
echo   * Frontend directory verified.

REM 3. Launch Backend in a separate window
echo.
echo [3/3] Launching Servers...
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
echo  Both servers started successfully!
echo   - Backend API: http://127.0.0.1:8000/api/
echo   - Frontend:    http://localhost:5173/
echo ========================================================
echo Opening browser...
start http://localhost:5173/

echo.
echo Note: Keep the server windows open while developing.
echo You may close this launcher window at any time.
echo.
pause

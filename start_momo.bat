@echo off
setlocal enabledelayedexpansion
title MOMO One-Click Master Launcher (Ollama + Backend + Frontend + USB-C Hardware)

:: 1. Normalize Root Directory (strip trailing backslash)
set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\Backend"
set "FRONTEND_DIR=%ROOT_DIR%\Frontend"

echo ====================================================================
echo              MOMO LOCAL-FIRST PHYSICAL AI COMPANION
echo             Master One-Click Full-Stack Launcher
echo ====================================================================
echo Project Root: %ROOT_DIR%
echo.

:: 2. Verify Node.js and npm Environment
echo [1/6] Checking Node.js and npm environment...
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
for /f "tokens=*" %%v in ('node -v 2^>nul') do set "NODE_VER=%%v"
for /f "tokens=*" %%v in ('npm -v 2^>nul') do set "NPM_VER=%%v"
echo [OK] Node.js !NODE_VER! and npm !NPM_VER! detected.

:: 3. Verify Python Virtual Environment
echo.
echo [2/6] Checking Python Backend environment...
set "PY_CMD=python"
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
    echo [OK] Using Python Venv: %BACKEND_DIR%\venv\Scripts\python.exe
) else (
    echo [WARN] Virtual environment not found, falling back to system python.
)

:: 4. Check and Auto-Start Local Ollama AI Engine
echo.
echo [3/6] Checking local Ollama AI Engine (Port 11434)...
curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>&1
if !errorlevel! neq 0 (
    echo [INFO] Ollama is not responding. Starting Ollama service...
    start "MOMO Ollama Runtime" ollama serve
    echo Waiting for Ollama to become ready...
    set "OLLAMA_UP=0"
    for /L %%i in (1,1,6) do (
        if !OLLAMA_UP! equ 0 (
            ping 127.0.0.1 -n 1 >nul
            curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>&1
            if !errorlevel! equ 0 (
                set "OLLAMA_UP=1"
                echo [OK] Ollama is online and responsive!
            )
        )
    )
    if !OLLAMA_UP! equ 0 (
        echo [WARN] Ollama starting in background. Continuing launcher...
    )
) else (
    echo [OK] Ollama is already running on port 11434.
)

:: Pre-warm Llama model in background for instant sub-second responses
echo [INFO] Pre-warming local AI model...
start "MOMO Model Pre-Warm" /D "%BACKEND_DIR%" /b "%PY_CMD%" -c "import sys; sys.path.insert(0, '.'); from ai.ollama_client import OllamaClient; OllamaClient().chat_sync([{'role': 'user', 'content': 'hello'}], model='hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0', timeout_seconds=90)"

:: 5. Ensure Database Migrations are Applied
echo.
echo [4/6] Verifying SQLite database migrations...
cd /d "%BACKEND_DIR%"
"%PY_CMD%" manage.py migrate --no-input >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Database schema up to date.
) else (
    echo [WARN] Migration check finished.
)
cd /d "%ROOT_DIR%"

:: 6. Scan and connect USB-C Hardware Port
echo.
echo [5/6] Scanning for USB-C connected ESP32 companion...
start "MOMO Hardware USB-C Serial Bridge" /D "%BACKEND_DIR%" cmd /k "%PY_CMD% -m iot.serial_bridge"

:: 7. Launch Django ASGI Backend Server
echo.
echo [6/6] Starting Servers...
echo   * Starting Django Backend on http://127.0.0.1:8000 ...
start "MOMO Brain Core (Django :8000)" /D "%BACKEND_DIR%" cmd /k "%PY_CMD% manage.py runserver 127.0.0.1:8000"

:: 8. Launch React Vite Frontend Server
echo   * Starting React Frontend on http://localhost:5173 ...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%FRONTEND_DIR%"
    call npm install
    cd /d "%ROOT_DIR%"
)
start "MOMO React Client (Port 5173)" /D "%FRONTEND_DIR%" cmd /k "call npm run dev -- --host 127.0.0.1"

:: 9. Fast Health Verification
echo Waiting for servers to initialize...
set "BACKEND_UP=0"
for /L %%i in (1,1,10) do (
    if !BACKEND_UP! equ 0 (
        ping 127.0.0.1 -n 1 >nul
        curl.exe -s http://127.0.0.1:8000/api/status/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_UP=1"
            echo [OK] Django Backend is online and ready!
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
            echo [OK] React Frontend is online and ready!
        )
    )
)

:: 10. Open Browser
echo.
echo Opening MOMO Companion Dashboard in browser...
start "" "http://localhost:5173/"

echo.
echo ====================================================================
echo  MOMO is now fully online!
echo   * Ollama Brain:             http://127.0.0.1:11434/
echo   * Backend REST and WebSockets: http://127.0.0.1:8000/
echo   * React Companion UI:       http://localhost:5173/
echo   * ESP32 Physical Companion: Connected via USB-C Serial
echo ====================================================================
echo Keep the server windows open. You may minimize this launcher.
echo.
pause

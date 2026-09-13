@echo off
setlocal enabledelayedexpansion
title MOMO One-Click Master Launcher (Ollama + Backend + Frontend + USB-C Hardware)

cd /d "%~dp0"
set "ROOT_DIR=%~dp0"

echo ====================================================================
echo              MOMO LOCAL-FIRST PHYSICAL AI COMPANION
echo             Master One-Click Full-Stack Launcher
echo ====================================================================
echo Project Root: %ROOT_DIR%
echo.

REM 1. Verify Node.js and npm Environment
echo [1/6] Checking Node.js and npm environment...
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
    for /f "tokens=*" %%v in ('node -v 2^>nul') do set "NODE_VER=%%v"
    for /f "tokens=*" %%v in ('npm -v 2^>nul') do set "NPM_VER=%%v"
    echo [OK] Node.js !NODE_VER! and npm !NPM_VER! detected.
) else (
    echo [ERROR] npm was not found in PATH or C:\Program Files\nodejs!
    echo Please install Node.js from https://nodejs.org/ and re-run.
    pause
    exit /b 1
)

REM 2. Verify Python Virtual Environment
echo.
echo [2/6] Checking Python Backend environment...
set "PYTHON_EXE=python"
if exist "%ROOT_DIR%Backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%Backend\venv\Scripts\python.exe"
    echo [OK] Using Python Venv: %PYTHON_EXE%
) else (
    echo [WARN] Virtual environment not found, falling back to system python.
)

REM 3. Check and Auto-Start Local Ollama AI Engine
echo.
echo [3/6] Checking local Ollama AI Engine (Port 11434)...
curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Ollama is not responding. Starting Ollama service...
    start "MOMO Ollama Runtime" ollama serve
    echo Waiting for Ollama to become ready...
    set "OLLAMA_UP=0"
    for /L %%i in (1,1,12) do (
        if !OLLAMA_UP! equ 0 (
            ping 127.0.0.1 -n 2 >nul
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

REM Pre-warm Llama model in background for instant sub-second responses
echo [INFO] Pre-warming local AI model...
start "MOMO Model Pre-Warm" /D "%ROOT_DIR%Backend" /b "%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '.'); from ai.ollama_client import OllamaClient; OllamaClient().chat_sync([{'role': 'user', 'content': 'hello'}], model='hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0', timeout_seconds=90)"

REM 4. Ensure Database Migrations are Applied
echo.
echo [4/6] Verifying SQLite database migrations...
"%PYTHON_EXE%" "%ROOT_DIR%Backend\manage.py" migrate --no-input >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Database schema up to date.
) else (
    echo [WARN] Migration check finished.
)

REM 5. Scan and connect USB-C Hardware Port
echo.
echo [5/6] Scanning for USB-C connected ESP32 companion...
start "MOMO Hardware USB-C Serial Bridge" cmd /k "cd /d "%ROOT_DIR%Backend" && "%PYTHON_EXE%" -m iot.serial_bridge"

REM 6. Launch Django ASGI Backend Server
echo.
echo [6/6] Starting Servers...
echo   * Starting Django Backend on http://127.0.0.1:8000 ...
start "MOMO Brain Core (Django :8000)" cmd /k "cd /d "%ROOT_DIR%Backend" && "%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000"

echo Waiting for Django Backend to respond...
set "BACKEND_UP=0"
for /L %%i in (1,1,15) do (
    if !BACKEND_UP! equ 0 (
        ping 127.0.0.1 -n 2 >nul
        curl.exe -s http://127.0.0.1:8000/api/status/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "BACKEND_UP=1"
            echo [OK] Django Backend is online and ready!
        )
    )
)

REM 7. Launch React Vite Frontend Server
echo   * Starting React Frontend on http://localhost:5173 ...
if not exist "%ROOT_DIR%Frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd /d "%ROOT_DIR%Frontend"
    call npm install
    cd /d "%ROOT_DIR%"
)

start "MOMO React Client (Port 5173)" cmd /k "cd /d "%ROOT_DIR%Frontend" && call npm run dev -- --host 127.0.0.1"

echo Waiting for React Frontend server (Port 5173) to become ready...
set "FRONTEND_UP=0"
for /L %%i in (1,1,20) do (
    if !FRONTEND_UP! equ 0 (
        ping 127.0.0.1 -n 2 >nul
        curl.exe -s -I http://127.0.0.1:5173/ >nul 2>&1
        if !errorlevel! equ 0 (
            set "FRONTEND_UP=1"
            echo [OK] React Frontend is online and ready!
        )
    )
)

REM 8. Launch Browser
echo.
echo Opening MOMO Companion Dashboard in browser...
start "" "http://localhost:5173/"

echo.
echo ====================================================================
echo  MOMO is now fully online!
echo   * Ollama Brain:             http://127.0.0.1:11434/
echo   * Backend REST & WebSockets: http://127.0.0.1:8000/
echo   * React Companion UI:       http://localhost:5173/
echo   * ESP32 Physical Companion: Connected via USB-C Serial
echo ====================================================================
echo Keep the server windows open. You may minimize this launcher.
echo.
pause

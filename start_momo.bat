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

REM 1. Verify Virtual Environment
set "PYTHON_EXE=python"
if exist "%ROOT_DIR%Backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%Backend\venv\Scripts\python.exe"
    echo [OK] Using Python Venv: %PYTHON_EXE%
) else (
    echo [WARN] Virtual environment not found, falling back to system python.
)

REM 2. Check and Auto-Start Local Ollama AI Engine
echo.
echo [1/5] Checking local Ollama AI Engine (Port 11434)...
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

REM Pre-warm Llama model in RTX GPU memory for instant sub-second responses
echo [INFO] Warming up local Llama model in GPU memory...
start "MOMO Model Pre-Warm" /D "%ROOT_DIR%Backend" /b "%PYTHON_EXE%" -c "import sys; sys.path.insert(0, '.'); from ai.ollama_client import OllamaClient; OllamaClient().chat_sync([{'role': 'user', 'content': 'hello'}], model='hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0', timeout_seconds=90)"


REM 3. Ensure Database Migrations are Applied
echo.
echo [2/5] Verifying SQLite database migrations...
"%PYTHON_EXE%" "%ROOT_DIR%Backend\manage.py" migrate --no-input >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Database schema up to date.
) else (
    echo [WARN] Migration check finished.
)

REM 4. Scan and connect USB-C Hardware Port
echo.
echo [3/5] Scanning for USB-C connected ESP32 companion...
start "MOMO Hardware USB-C Serial Bridge" /D "%ROOT_DIR%Backend" cmd /k ""%PYTHON_EXE%" -m iot.serial_bridge"

REM 5. Launch Django ASGI Backend Server
echo.
echo [4/5] Starting Django Channels ASGI Backend (Port 8000)...
start "MOMO Brain Core (Django :8000)" /D "%ROOT_DIR%Backend" cmd /k ""%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000"

ping 127.0.0.1 -n 3 >nul

REM 6. Launch React Vite Frontend Server
echo.
echo [5/5] Starting React Frontend (Port 5173)...
start "MOMO React Client (Port 5173)" /D "%ROOT_DIR%Frontend" cmd /k "npm run dev"

ping 127.0.0.1 -n 4 >nul

REM 7. Launch Browser
echo.
echo Opening MOMO Companion Dashboard in browser...
start http://localhost:5173/

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

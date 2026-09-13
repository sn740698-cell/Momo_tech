@echo off
:: Batch script to install CP210x USB to UART Bridge Driver for ESP32
echo ==========================================================
echo   Installing CP210x USB to UART Bridge Driver for ESP32
echo ==========================================================
echo.
cd /d "%~dp0\cp210x_driver"

echo Installing silabser.inf...
pnputil.exe /add-driver silabser.inf /install

if %errorlevel% neq 0 (
    echo.
    echo NOTE: If you received an 'Access is denied' error above,
    echo please RIGHT-CLICK on this file and select 'Run as administrator',
    echo OR right-click on 'silabser.inf' inside cp210x_driver and click 'Install'.
) else (
    echo.
    echo Driver successfully installed! Your ESP32 COM port is now active.
)

echo.
pause

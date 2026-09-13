# MOMO Companion Master PowerShell Launcher
Continue = Continue

 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Path
 = Join-Path  Backend
 = Join-Path  Frontend

Write-Host ==================================================================== -ForegroundColor Cyan
Write-Host  MOMO LOCAL-FIRST PHYSICAL AI COMPANION  -ForegroundColor Cyan
Write-Host  Master PowerShell Launcher  -ForegroundColor Cyan
Write-Host ==================================================================== -ForegroundColor Cyan
Write-Host Project Root: 


# 1. Environment Detection
if (Test-Path C:\Program Files\nodejs) {
    C:/Users/darshini/.gemini/antigravity/bin;C:\Users\darshini\AppData\Roaming\Antigravity\bin;C:\app\darshini\product\21c\dbhomeXE\bin;C:\windows\system32;C:\windows;C:\windows\System32\Wbem;C:\windows\System32\WindowsPowerShell\v1.0\;C:\windows\System32\OpenSSH\;C:\Program Files (x86)\NVIDIA Corporation\PhysX\Common;C:\Program Files\NVIDIA Corporation\NVIDIA App\NvDLISR;C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps;C:\Program Files\HP\OMEN-Broadcast\Common;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\WINDOWS\System32\WindowsPowerShell\v1.0\;C:\WINDOWS\System32\OpenSSH\;C:\Program Files\Git\cmd;C:\Program Files\nodejs\;C:\Users\darshini\AppData\Local\Programs\Python\Python314\Scripts\;C:\Users\darshini\AppData\Local\Programs\Python\Python314\;C:\Users\darshini\AppData\Local\Microsoft\WindowsApps;C:\Users\darshini\AppData\Local\Programs\Ollama;C:\Users\darshini\AppData\Roaming\npm;C:\Users\darshini\AppData\Local\Programs\Microsoft VS Code\bin;C:\Users\darshini\AppData\Local\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe; = C:\Program Files\nodejs;C:/Users/darshini/.gemini/antigravity/bin;C:\Users\darshini\AppData\Roaming\Antigravity\bin;C:\app\darshini\product\21c\dbhomeXE\bin;C:\windows\system32;C:\windows;C:\windows\System32\Wbem;C:\windows\System32\WindowsPowerShell\v1.0\;C:\windows\System32\OpenSSH\;C:\Program Files (x86)\NVIDIA Corporation\PhysX\Common;C:\Program Files\NVIDIA Corporation\NVIDIA App\NvDLISR;C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps;C:\Program Files\HP\OMEN-Broadcast\Common;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\WINDOWS\System32\WindowsPowerShell\v1.0\;C:\WINDOWS\System32\OpenSSH\;C:\Program Files\Git\cmd;C:\Program Files\nodejs\;C:\Users\darshini\AppData\Local\Programs\Python\Python314\Scripts\;C:\Users\darshini\AppData\Local\Programs\Python\Python314\;C:\Users\darshini\AppData\Local\Microsoft\WindowsApps;C:\Users\darshini\AppData\Local\Programs\Ollama;C:\Users\darshini\AppData\Roaming\npm;C:\Users\darshini\AppData\Local\Programs\Microsoft VS Code\bin;C:\Users\darshini\AppData\Local\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe;
}

 = python
if (Test-Path \venv\Scripts\python.exe) {
     = \venv\Scripts\python.exe
}

# 2. Check Ollama
try {
     = Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host [OK] Ollama is online on port 11434. -ForegroundColor Green
} catch {
    Write-Host [INFO] Starting Ollama serve... -ForegroundColor Yellow
    Start-Process ollama -ArgumentList serve -WindowStyle Minimized
    Start-Sleep -Seconds 3
}

# 3. Pre-warm model in background
Start-Process  -ArgumentList -c import sys; sys.path.insert(0, '.'); from ai.ollama_client import OllamaClient; OllamaClient().chat_sync([{'role': 'user', 'content': 'hello'}], timeout_seconds=60)" -WorkingDirectory -WindowStyle Hidden

# 4. Apply Migrations
Push-Location 
& manage.py migrate --no-input | Out-Null
Pop-Location

# 5. Start ESP32 Bridge
Start-Process cmd.exe -ArgumentList /k  -m iot.serial_bridge -WorkingDirectory 

# 6. Start Django Backend
Start-Process cmd.exe -ArgumentList /k  manage.py runserver 127.0.0.1:8000 -WorkingDirectory 

# 7. Start React Frontend
Start-Process cmd.exe -ArgumentList /k npm.cmd run dev -- --host 127.0.0.1 -WorkingDirectory 

# 8. Fast Wait & Browser Launch
Write-Host Waiting for servers to become ready... -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host [OK] Opening MOMO UI at http://localhost:5173/ ... -ForegroundColor Green
Start-Process http://localhost:5173/

Write-Host ==================================================================== -ForegroundColor Cyan
Write-Host   MOMO is online! Keep server console windows open. -ForegroundColor Green
Write-Host ==================================================================== -ForegroundColor Cyan

# 🚀 MOMO Full-Stack Deployment & Quickstart Guide

## 1. Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Ollama (installed and running with `ollama pull qwen3:4b` or any model)
- (Optional) ESP32 connected via USB-C cable

---

## 2. One-Click Launch

Double-click `start_momo.bat` at the project root.
This automatically:
1. Detects and connects to the USB-C ESP32 physical companion.
2. Starts the Django Channels ASGI Backend on `http://127.0.0.1:8000/`.
3. Starts the React Vite Frontend on `http://localhost:5173/`.
4. Opens your browser directly to the MOMO dashboard.

---

## 3. Manual Step-by-Step Launch

### Terminal 1 — Local LLM
```bash
ollama serve
```

### Terminal 2 — Django ASGI Backend
```bash
cd Backend
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### Terminal 3 — React Frontend Client
```bash
cd Frontend
npm run dev
```

### Terminal 4 (Optional) — Hardware USB-C Serial Bridge
```bash
cd Backend
.\venv\Scripts\python.exe -m iot.serial_bridge
```

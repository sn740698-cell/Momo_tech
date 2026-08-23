# 🤖 MOMO - Local AI Fullstack Platform

> A fullstack AI chatbot and REST API integration powered by **React 19 (Vite)**, **Django 6.1 (REST API + Server-Sent Events)**, and **Ollama** with local LLMs (e.g. `qwen3:4b`).

![MOMO AI Architecture](https://img.shields.io/badge/Stack-React%20%2B%20Django%20%2B%20Ollama-indigo)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Django](https://img.shields.io/badge/Django-6.1-emerald)
![React](https://img.shields.io/badge/React-19-cyan)
![Tailwind](https://img.shields.io/badge/TailwindCSS-v4-purple)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-orange)

---

## ✨ Features

- 🧠 **Local LLM Chatbot**: Connects to your local Ollama daemon without needing external API keys or subscriptions.
- ⚡ **Qwen3:4b Integration**: Pre-configured with default support for `qwen3:4b` including real-time reasoning/thinking blocks.
- 🔄 **Dynamic Model Selection**: Auto-detects all installed Ollama models and allows custom model tag inputs (e.g. `qwen2.5:3b`, `llama3`, `deepseek-r1`).
- 🌊 **Real-Time Token Streaming**: Streams tokens live via Server-Sent Events (SSE) with typing indicators and abort/stop controls.
- 💬 **Multi-Turn Conversation**: Full conversation context memory with Markdown formatting, code block syntax styling, and 1-click **Copy Code** buttons.
- ⚙️ **Customizable Persona**: Adjust System Prompt and Temperature parameters (0.1 - 1.5) on the fly.
- 📊 **System Health & API Console**: Live telemetry, latency monitoring, REST API payload tester, and fullstack topology view.

---

## 🏗️ Architecture

```
[ Frontend: React 19 + Vite ] (Port 5173)
            │
            ▼ (Proxy / REST API / SSE)
[ Backend Gateway: Django 6.1 REST ] (Port 8000)
            │
            ▼ (HTTP JSON / Chat Stream)
[ Local LLM Engine: Ollama ] (Port 11434)
            │
            ▼
[ Model: qwen3:4b / Local Weights ]
```

---

## 🚀 Quick Start

### 1. Prerequisites
- [Ollama](https://ollama.com/) installed and running on your system.
- Download the Qwen model in your terminal:
  ```bash
  ollama run qwen3:4b
  ```

### 2. One-Click Launcher (Windows)
Double-click `start.bat` in the root folder. It will:
1. Verify the Python virtual environment and Django server.
2. Verify the React Vite frontend.
3. Launch both servers in separate windows.
4. Open [http://localhost:5173/](http://localhost:5173/) automatically in your default browser.

### 3. Manual Startup

**Start Backend (Django):**
```bash
cd Backend
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

**Start Frontend (React + Vite):**
```bash
cd Frontend
npm install
npm run dev
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/ollama/status/` | `GET` | Ollama daemon health check & model discovery |
| `/api/chat/` | `POST` | Multi-turn chat completion (streaming / batch) |
| `/api/status/` | `GET` | Django REST service health & latency telemetry |
| `/api/message/` | `POST` | Basic REST payload testing endpoint |

---

## 📁 Repository Structure

```
MOMO/
├── Backend/                 # Django REST Backend
│   ├── api/                 # API app (views, urls, endpoints)
│   ├── config/              # Django settings & root router
│   ├── manage.py            # Django CLI management script
│   └── venv/                # Python virtual environment (ignored)
├── Frontend/                # React 19 Frontend (Vite + Tailwind CSS)
│   ├── src/                 # React source code (App.jsx, App.css)
│   ├── public/              # Static assets & icons
│   ├── package.json         # Node package configuration
│   └── vite.config.js       # Vite build & proxy settings
├── start.bat                # Windows One-Click Server Launcher
├── .gitignore               # Root git ignore rules
└── README.md                # Project documentation
```

---

## 📄 License
MIT License. Built for local AI experimentation with MOMO.

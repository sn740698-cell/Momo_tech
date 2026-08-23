# 🤖 MOMO — Local AI Desktop & Physical Companion Platform

> 🚀 **Project Status**: **Started & In Active Development**  
> *A local-first, privacy-respecting AI companion pairing an expressive digital assistant with an interactive physical robot.*

![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)
![Stack](https://img.shields.io/badge/Stack-Django%20Channels%20%2B%20React%2FPySide6%20%2B%20ESP32-indigo)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Django](https://img.shields.io/badge/Django-6.1%20%2B%20Channels-emerald)
![Local LLM](https://img.shields.io/badge/Ollama-Local%20LLMs%20(Qwen3%2FLlama3)-orange)
![Hardware](https://img.shields.io/badge/Hardware-ESP32%20%2B%20OLED%20%2B%20Servos-red)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 🌟 The MOMO Philosophy

> **Frontend shows MOMO. Backend thinks for MOMO. Ollama gives MOMO language. Computer vision gives MOMO perception. Memory gives MOMO continuity. ESP32 gives MOMO a body. WebSockets connect everything.**

MOMO is designed as a **hybrid digital-physical companion**:
- **Digital Character**: A lightweight, expressive desktop companion with dynamic facial animations and natural multi-turn conversation.
- **Physical Robot**: An ESP32-driven desktop companion featuring an OLED display that mirrors MOMO's digital expressions, servo-driven head movements (nod, tilt, celebrate), and tactile pushbuttons.
- **Privacy First & Local**: 100% powered by local LLMs via Ollama. No cloud dependencies, no subscription fees, and granular hardware privacy shutters.

---

## 🏗️ System Architecture

```text
                                  USER INTERACTION
                        (Chat Message / Voice / Idle Event)
                                         │
                                         ▼
                             DESKTOP FRONTEND (PySide6 / React)
                                         │
                                         │ WebSocket (/ws/momo/)
                                         ▼
                             DJANGO ASGI (Channels Consumer)
                                         │
                                         ▼
                                  MOMO BRAIN CORE
                                         │
             ┌───────────────────────────┼───────────────────────────┐
             │                           │                           │
             ▼                           ▼                           ▼
       MEMORY ENGINE              CONTEXT ENGINE               EVENT ENGINE
    (Preferences & Facts)       (Session & Activity)        (Deterministic Rules)
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         │
                                         ▼
                               PROMPT BUILDER (Persona + Schema)
                                         │
                                         ▼
                                LOCAL LLM (Ollama API)
                                         │
                                         ▼
                             STRUCTURED JSON RESPONSE
                    {message, expression, animation, speak}
                                         │
                                         ▼
                                RESPONSE VALIDATOR
                                         │
                     ┌───────────────────┴───────────────────┐
                     │                                       │
                     ▼                                       ▼
             DESKTOP COMPANION                          IoT MANAGER
       - Render facial expression                 - Serialize command
       - Display Markdown chat bubble             - Send via WebSocket
       - Audio Text-to-Speech (TTS)                          │
                                                             ▼
                                                        ESP32 ROBOT
                                                  - Render OLED Face
                                                  - Execute Servo Motion
                                                  - Blink Status LED
```

---

## 😊 Expressive Character Faces

MOMO expresses emotion identically across digital screens and physical OLED displays:

| Mood / Expression | ASCII Display | Description |
| :--- | :---: | :--- |
| **NORMAL** | `◕ᴗ◕` | Attentive and idle, waiting for commands |
| **HAPPY** | `^ᴗ^` | Friendly greeting, success, positive feedback |
| **THINKING** | `•ᴗ•` | Local LLM reasoning or processing memories |
| **CONFUSED** | `•_•?` | Unclear prompt, fallback state, or parse warning |
| **SLEEPY** | `-ᴗ-` | Extended idle period or late-night mode |
| **EXCITED** | `★ᴗ★` | Goal achieved, energetic response, celebration |

---

## 📚 Deep-Dive Documentation

Detailed specifications and architectural guides are available in the [`docs/`](file:///c:/Users/darshini/Desktop/MOMO/docs) folder:

- 🏛️ [**System Architecture**](file:///c:/Users/darshini/Desktop/MOMO/docs/ARCHITECTURE.md) — Core principles, end-to-end data flow, and privacy boundaries.
- 🖥️ [**Frontend Roadmap & Specification**](file:///c:/Users/darshini/Desktop/MOMO/docs/FRONTEND_ROADMAP.md) — Thin client design, facial state machine, and UI milestones.
- ⚙️ [**Backend Roadmap & Specification**](file:///c:/Users/darshini/Desktop/MOMO/docs/BACKEND_ROADMAP.md) — Brain core, decision engine, SQLite memory, and Ollama integration.
- 🔌 [**Hardware & ESP32 Specification**](file:///c:/Users/darshini/Desktop/MOMO/docs/HARDWARE_SPEC.md) — Schematic, pinouts, OLED graphics, and servo command mapping.
- 📡 [**API & Protocol Guide**](file:///c:/Users/darshini/Desktop/MOMO/docs/API_AND_PROTOCOLS.md) — REST endpoints, WebSocket `/ws/momo/` JSON contracts, and error schemas.

---

## 🗺️ Project Milestones & Progress

### ⚙️ Backend Milestones (B1 — B12)
- [x] **B1 — Django Core & REST Foundation**: Django backend, health telemetry, and status endpoints.
- [ ] **B2 — Django Channels & WebSockets**: Persistent `/ws/momo/` endpoint with bidirectional JSON framing.
- [ ] **B3 — Fake Brain Mock**: Real-time response loop verification without LLM latency.
- [x] **B4 — Ollama Local LLM Integration**: Multi-turn chat completion with dynamic model discovery.
- [ ] **B5 — Personality & Structured Output**: Schema validator enforcing `{message, expression, animation}`.
- [ ] **B6 — SQLite Memory Engine**: Storing user preferences, session facts, and 1-click memory deletion.
- [ ] **B7 — Context Engine**: Session timer, idle monitor, and active window tracker.
- [ ] **B8 — Event & Decision Engine**: Rule-based triggers (`LONG_SESSION`, `USER_RETURNED`).
- [ ] **B9 — Computer Vision Pipeline**: OpenCV + MediaPipe face and attention tracking.
- [ ] **B10 — Voice Pipeline**: Local STT (faster-whisper) and TTS (pyttsx3/piper).
- [ ] **B11 — IoT & ESP32 Protocol**: Device registry, heartbeat telemetry, and physical actuation.
- [ ] **B12 — Full Integration & Tests**: End-to-end resilience and offline degradation suite.

### 🖥️ Frontend Milestones (F1 — F10)
- [x] **F1 — Fullstack UI Foundation**: Modern reactive companion interface with multi-turn chat and reasoning blocks.
- [x] **F2 — Backend API Bridge**: Connects to Django REST gateway with real-time SSE streaming.
- [ ] **F3 — WebSocket Integration**: Transitioning to persistent WebSocket `/ws/momo/` connection.
- [x] **F4 — Ollama Streaming Support**: Dynamic model selection, custom temperature, and token streaming.
- [ ] **F5 — Character Face & Animation Engine**: Visual rendering of the 6 core expressions synchronized with chat.
- [ ] **F6 — Voice Controls**: Integrated voice input toggle and text-to-speech audio playback.
- [ ] **F7 — Perception UI**: Visual indicators for presence, attention, and privacy shutter.
- [ ] **F8 — ESP32 Hardware Status**: Live link monitor, battery telemetry, and latency indicators.
- [ ] **F9 — Privacy & Memory Management**: Granular permission switches and 1-click memory purge.
- [ ] **F10 — Final Polish**: Auto-reconnection resilience, keyboard shortcuts, and standalone packaging.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- [Ollama](https://ollama.com/) installed and running.
- Pull your desired local model (e.g. `qwen3:4b`):
  ```bash
  ollama run qwen3:4b
  ```

### 2. One-Click Launcher (Windows)
Double-click `start.bat` in the root directory. It will:
1. Verify Python virtual environment and launch the Django backend (port 8000).
2. Launch the frontend development server (port 5173).
3. Open `http://localhost:5173/` in your browser.

### 3. Manual Launch

**Backend (Django):**
```bash
cd Backend
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

**Frontend (React / Vite):**
```bash
cd Frontend
npm install
npm run dev
```

---

## 📁 Repository Layout

```text
MOMO/
├── Backend/                 # Django Backend Core
│   ├── api/                 # API endpoints, telemetry, and Ollama integration
│   ├── config/              # Django settings, URLs, and ASGI configuration
│   ├── manage.py            # Django CLI management script
│   └── venv/                # Python virtual environment
├── Frontend/                # Digital Companion Client
│   ├── src/                 # Reactive UI components (App.jsx, styles)
│   ├── package.json         # Node package configuration
│   └── vite.config.js       # Build and proxy settings
├── docs/                    # Architectural Specifications & Roadmaps
│   ├── ARCHITECTURE.md      # Full system architecture
│   ├── FRONTEND_ROADMAP.md  # Frontend milestones & UI specifications
│   ├── BACKEND_ROADMAP.md   # Backend modular design & Brain specifications
│   ├── HARDWARE_SPEC.md     # ESP32 schematics, pinout, & OLED protocol
│   └── API_AND_PROTOCOLS.md # REST and WebSocket schema documentation
├── start.bat                # Windows One-Click Server Launcher
├── .gitignore               # Git ignore rules
└── README.md                # Project documentation & roadmap status
```

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).

# ⚙️ MOMO — Backend Roadmap & Specification

## 1. Purpose & Coordination Layer

The **MOMO Backend** serves as the central brain, coordination, and intelligence core for MOMO. It connects all sub-systems into a unified reactive graph:

```text
Frontend (PySide6 / React)
   │
Django Channels (WebSocket: /ws/momo/)
   │
MOMO Brain Core
   │
┌──┴────────────┬─────────────┬─────────────┬─────────────┐
│               │             │             │             │
Local LLM     Memory        Context       Vision         IoT
(Ollama)      (SQLite)     (Tracker)     (OpenCV)      (ESP32)
```

### Core Backend Responsibilities
1. **Real-time Event Routing**: Low-latency WebSocket broadcasting between Desktop UI and ESP32.
2. **Brain Core & Decision Engine**: Deterministic rules ensuring safe, respectful, non-annoying interactions.
3. **Context Engine**: Aggregates screen activity, active applications, session duration, and idle metrics.
4. **Local LLM Engine**: Prompts Ollama with persona, context, memory, and structured JSON output rules.
5. **Response Parser & Schema Validation**: Strict schema enforcement before triggering speech or hardware servos.
6. **Persistent Memory Store**: Secure SQLite storage for user preferences, facts, and conversation history.
7. **Hardware Abstraction Layer (IoT)**: Translates high-level emotional states into hardware-safe micro-commands.

---

## 2. Modular Backend Architecture

```text
Backend/
├── manage.py
├── config/
│   ├── settings.py          # Channels & ASGI configuration, CORS, DB
│   ├── urls.py              # Root HTTP and WebSocket routing
│   └── asgi.py              # ASGI application for Django Channels
├── momo/
│   ├── consumers.py         # MomoConsumer (WebSocket connection & event routing)
│   ├── routing.py           # WebSocket URL patterns (/ws/momo/)
│   └── models.py            # Core session and device models
├── brain/
│   ├── momo_brain.py        # Brain coordinator
│   ├── decision_engine.py   # Deterministic safety and rule engine
│   ├── personality.py       # System prompt & MOMO persona definitions
│   └── response_parser.py   # JSON validation & fallback recovery
├── ai/
│   ├── ollama_client.py     # Resilient HTTP client for Ollama API
│   ├── prompt_builder.py    # Merges memory, context, persona, and events
│   └── model_manager.py     # Local model discovery and benchmark loader
├── context/
│   ├── context_engine.py    # Merges vision, session, and activity states
│   └── activity_tracker.py  # User activity & idle time monitor
├── memory/
│   ├── memory_manager.py    # Search, retrieve, and store memories
│   ├── repository.py        # SQLite queries and transaction handlers
│   └── models.py            # UserPreferences, FactMemory, ChatHistory
├── vision/
│   ├── camera.py            # OpenCV camera capture thread
│   ├── face.py              # MediaPipe face & presence detection
│   └── attention.py         # Screen attention state estimator
├── voice/
│   ├── stt.py               # Local speech-to-text
│   └── tts.py               # Local text-to-speech
└── iot/
    ├── esp32_manager.py     # Device registry & WebSocket bridge
    └── protocol.py          # Command serializer (OLED, servo, LED)
```

---

## 3. Structured LLM Response Schema & Validator

MOMO requires machine-readable state rather than unstructured prose:

### Expected JSON Output
```json
{
  "message": "Hey! I noticed you have been coding for 2 hours. Want to take a stretch break?",
  "expression": "happy",
  "animation": "nod",
  "speak": true,
  "priority": "normal"
}
```

### Schema Allow-Lists
- **Expressions**: `normal`, `happy`, `thinking`, `confused`, `sleepy`, `excited` (extended: `sad`, `angry`, `surprised`, `proud`, `embarrassed`)
- **Animations / Servo Actions**: `none`, `nod`, `tilt_left`, `tilt_right`, `blink`, `celebrate`
- **Fallback Recovery**: If LLM output fails JSON parsing, `response_parser` wraps the raw output safely:
  ```python
  {
      "message": raw_text.strip(),
      "expression": "normal",
      "animation": "none",
      "speak": False,
      "priority": "low"
  }
  ```

---

## 4. Context & Decision Engine

The **Decision Engine** applies deterministic rules to prevent MOMO from interrupting the user unnecessarily:

```text
IF user_session_minutes > 60
AND last_momo_interaction > 25 minutes
AND user_is_idle_seconds > 10
THEN trigger_event("LONG_SESSION_BREAK_SUGGESTION")
ELSE keep_silent()
```

---

## 5. Backend Milestones & Definition of Done

- [ ] **Milestone B1 — Django Foundation**: Django setup, `/api/status/`, and SQLite configuration.
- [ ] **Milestone B2 — Django Channels & WebSockets**: Persistent `/ws/momo/` connection with ping/pong and JSON framing.
- [ ] **Milestone B3 — Fake Brain Mock**: Complete roundtrip message testing with zero-latency responses.
- [ ] **Milestone B4 — Ollama Local LLM**: Asynchronous HTTP client communicating with `qwen3:4b` or user-chosen model.
- [ ] **Milestone B5 — Personality & Structured Output**: System prompt builder with JSON schema enforcement and recovery.
- [ ] **Milestone B6 — SQLite Memory Engine**: Structured user preferences, conversation recall, and explicit wipe API.
- [ ] **Milestone B7 — Context Engine**: Session tracker, idle monitor, and active window tracker.
- [ ] **Milestone B8 — Event Engine**: Rule-based triggers (`LONG_SESSION`, `USER_RETURNED`, `BUTTON_PRESSED`).
- [ ] **Milestone B9 — Computer Vision Pipeline**: OpenCV + MediaPipe presence and face direction detection with privacy switches.
- [ ] **Milestone B10 — Voice Pipeline**: Local STT (faster-whisper) and TTS (pyttsx3/piper) integration.
- [ ] **Milestone B11 — IoT & ESP32 Protocol**: Device registry, heartbeat telemetry, command dispatch, and button event handler.
- [ ] **Milestone B12 — Complete Integration & Test Suite**: Unit, integration, and degradation tests under offline conditions.

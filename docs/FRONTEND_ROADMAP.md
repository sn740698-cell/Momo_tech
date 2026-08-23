# 🖥️ MOMO — Frontend Roadmap & Specification

## 1. Purpose & Vision

The **MOMO Frontend** represents everything the user directly sees, hears, or interacts with:

- **Desktop Companion Window**: Minimalist, unobtrusive, floating companion UI.
- **MOMO Animated Face**: Expressive ASCII and visual face engine.
- **Chat Interface**: Streamlined multi-turn conversation UI with real-time feedback.
- **Voice Controls**: Speech-to-text (STT) and text-to-speech (TTS) toggles and indicators.
- **Camera / Perception Controls**: Local computer vision status and privacy shutter.
- **Status & Telemetry**: Online/offline indicators, latency, and hardware connection state.
- **Physical Device Status**: Live link state with the ESP32 physical companion.
- **Privacy & Memory Center**: Full transparency, granular toggles, and 1-click memory deletion.

> **Key Rule**: The frontend is a **thin client**. It does **not** execute the LLM or run business logic directly. It delegates intelligence to the backend/brain and renders MOMO's resulting state.

### Recommended Stack
- **Framework**: Python + PySide6 (Desktop) / React 19 + Vite (Web Dashboard)
- **Protocol**: WebSockets (real-time JSON events) & HTTP REST
- **Animation**: Qt Timers / CSS Keyframes / Canvas
- **Perception Preview**: Optional OpenCV video capture preview
- **Audio**: Local audio input/output controls

---

## 2. Frontend Architecture

```text
                         FRONTEND
                            |
              +-------------+-------------+
              |                           |
        Desktop UI                    Device UI
              |                           |
        PySide6 / React               ESP32 OLED
              |
      +-------+--------+
      |       |        |
    Chat    Voice    Status
      |       |        |
      +-------+--------+
              |
        WebSocket Client
              |
              v
     Backend / MOMO Brain
              |
              v
      Response + State
              |
              v
      Frontend Animation
```

---

## 3. Digital Character States & Facial Expressions

MOMO communicates emotion and state through synchronized facial expressions across both digital and physical screens.

### Core 6 Expression Set

| Mood / Expression | ASCII Representation | Visual Meaning & Trigger |
| :--- | :---: | :--- |
| **NORMAL** | `◕ᴗ◕` | Idle, attentive, awaiting user interaction |
| **HAPPY** | `^ᴗ^` | Friendly greeting, task success, positive mood |
| **THINKING** | `•ᴗ•` | Local LLM actively generating tokens or querying memory |
| **CONFUSED** | `•_•?` | Unclear query, fallback mode, parse or connection error |
| **SLEEPY** | `-ᴗ-` | Extended idle period or late night inactivity |
| **EXCITED** | `★ᴗ★` | Milestone achieved, celebration, energetic response |

### Extended Expression Set (Phase 4+)
- **SAD**: `v_v`
- **ANGRY**: `>_<`
- **SURPRISED**: `o_O`
- **PROUD**: `^w^`
- **EMBARRASSED**: `>///<`

---

## 4. UI Components & Layout

```text
+-------------------------------------------------------------+
| MOMO Companion                                    ● Online  |
|                                                             |
|                          ^ᴗ^                                |
|                   "Hey! What's up?"                         |
|                                                             |
|  ---------------------------------------------------------  |
|  You:  Fix my ESP32 connection issue                        |
|                                                             |
|  MOMO: Let's investigate that little toaster.               |
|                                                             |
|  [ Type a message...                             ] [Send][🎤]|
|                                                             |
|  Camera: ● OFF | Mic: ● OFF | Memory: ● ON | ESP32: ● Connected|
+-------------------------------------------------------------+
```

### Key UI Subsystems

1. **Facial Widget (`momo_widget`)**:
   - Renders current mood and animation state.
   - Smooth interpolation between expressions.
   - Blinking and idle breathing loops.

2. **Chat Stream (`chat_widget`)**:
   - User message bubbles (right-aligned).
   - MOMO response bubbles (left-aligned) with Markdown support.
   - Real-time thinking / reasoning disclosure block.
   - Non-blocking asynchronous rendering.

3. **Status Bar (`status_widget`)**:
   - Backend WebSocket connection status.
   - ESP32 hardware connection & latency.
   - Active Ollama model indicator.

4. **Privacy & Control Panel (`settings_window`)**:
   - Camera toggle (hardware-level disable).
   - Microphone toggle (speech stream disable).
   - Activity tracking toggle.
   - 1-click **Delete Memory** and **Clear Session** buttons.

---

## 5. Central State Model

```json
{
  "mood": "happy",
  "expression": "happy",
  "animation": "nod",
  "is_thinking": false,
  "voice_enabled": true,
  "camera_enabled": false,
  "microphone_enabled": false,
  "esp32_connected": true,
  "privacy": {
    "activity_tracking": true,
    "memory_active": true
  },
  "telemetry": {
    "latency_ms": 14,
    "active_model": "qwen3:4b"
  }
}
```

---

## 6. Frontend Milestones & Definition of Done

- [ ] **Milestone F1 — Static UI Foundation**: Base window layout, character face display, chat container, and status bar.
- [ ] **Milestone F2 — Fake Backend Loop**: Test interactive chat and immediate face state transitions without Ollama latency.
- [ ] **Milestone F3 — WebSocket Integration**: Persistent real-time communication with Django Channels (`/ws/momo/`).
- [ ] **Milestone F4 — Ollama Local LLM**: Asynchronous streaming response processing without UI lockups.
- [ ] **Milestone F5 — Animation Controller**: Dynamic synchronization between LLM response states and facial expressions.
- [ ] **Milestone F6 — Voice UI**: Integration of Speech-to-Text (STT) input and Text-to-Speech (TTS) audio playback.
- [ ] **Milestone F7 — Vision & Perception UI**: Display structured perception state (presence, attention) with privacy indicators.
- [ ] **Milestone F8 — ESP32 Synchronization**: Hardware status indicators and bi-directional event notifications.
- [ ] **Milestone F9 — Privacy Controls**: Granular permission switches and memory wipe functionality.
- [ ] **Milestone F10 — Final Polish**: Auto-reconnect resilience, keyboard shortcuts, smooth transitions, and error boundary handling.

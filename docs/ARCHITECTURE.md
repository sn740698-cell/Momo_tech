# 🏗️ MOMO System Architecture

## 1. System Vision & Paradigm

MOMO is an open-source, local-first companion combining:
1. **Desktop Thin Client** (visual character, chat stream, voice & privacy controls)
2. **Asynchronous Django Brain Core** (context engine, deterministic decision logic, SQLite memory)
3. **Local LLM Engine** (Ollama running locally without cloud telemetry)
4. **Physical Desktop Companion** (ESP32 with I2C OLED display, pan/tilt servos, status LEDs, and physical pushbuttons)

---

## 2. End-to-End Interaction Flow

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

## 3. Subsystem Breakdown

### 3.1 Digital Companion (Frontend)
- **Role**: Render current character state, accept user queries, control privacy toggles.
- **Principle**: Zero business logic, thin client architecture.

### 3.2 Coordination & Intelligence (Backend)
- **Role**: Manage state, build contextual prompts, ensure deterministic safety rules, store memory.
- **Principle**: Local-first, strictly validates all LLM outputs before dispatching to hardware.

### 3.3 Physical Companion (Hardware)
- **Role**: Mirror digital emotion and provide tactile interaction.
- **Principle**: ESP32 operates as a peripheral receptor; it executes only pre-defined valid commands and never executes raw network code.

---

## 4. Privacy & Local-First Philosophy
- **Zero Cloud Leakage**: All LLM queries run against local Ollama runtime (`http://127.0.0.1:11434`).
- **Granular Shutter**: Camera and microphone streams can be physically disabled from the UI at any time.
- **User Memory Sovereignty**: User has complete visibility and one-click deletion access over all stored facts and conversations.

# 🏗️ MOMO System Architecture & Technical Specification

## 1. Paradigm Overview

MOMO is a **local-first physical AI companion**.
- **The Laptop is MOMO's Brain**: Houses the local LLM runtime (Ollama), sentence-level contextual NLP (BERT), dense vector embedding and retrieval (DistilBERT + ChromaDB), and multi-supervisor LangGraph state graph.
- **The ESP32 is MOMO's Physical Body**: Connects via direct **USB-C Serial** or Wi-Fi WebSocket. Renders procedural facial expressions on an SSD1306 OLED, articulates pan/tilt head motions via SG90 micro-servos, signals status with LED states, and receives physical user input via pushbuttons.
- **The React Frontend is MOMO's Digital Twin**: Mirrors expressions, provides multi-turn chat, document intelligence, invoice inspection, and message drafting.

```text
                                USER
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
       React Frontend                           Voice Input
             │                                       │
             │ REST / WebSocket                      ▼
             │                                  Whisper STT
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
                          Django Channels
                                 │
                                 ▼
                       Shared Pydantic State
                                 │
                                 ▼
                        LANGGRAPH WORKFLOW
                                 │
                          ROOT SUPERVISOR
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
 Conversation                 Finance                Communication
  Supervisor                Supervisor                Supervisor
       │                         │                         │
       ▼                         ▼                         ▼
 Conversation              Document Agent            Texting Agent
    Agent                        │                         │
       │                  Retrieval Agent                  │
       │                         │                         │
       │                    DistilBERT                     │
       │                         │                         │
       │                     ChromaDB                      │
       │                         │                         │
       │                   Data Analyzer                   │
       │                         │                         │
       │                       BERT                        │
       │                         │                         │
       └─────────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                           Prompt Builder
                                 │
                                 ▼
                            Local Ollama
                                 │
                                 ▼
                        Structured Response
                                 │
                        Pydantic Validation
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
       React UI Avatar                           IoT Agent
                                                     │
                                                     ▼
                                                   ESP32
                                                     │
                                    ┌────────────────┴────────────────┐
                                    ▼                ▼                ▼
                                  OLED             Servos            LED
```

---

## 2. Local-First Core Principles

1. **Zero Cloud Telemetry**: Core reasoning runs on local Ollama weights (e.g. `qwen3:4b`, `llama3`).
2. **Deterministic Mathematical Truth**: Generative models are never the source of truth for financial figures. `balance_due = invoice_total - amount_paid` is computed strictly in Python.
3. **Hardware Command Allowlist**: Only predefined expressions, animations, and servo angles (Pan: 30°-150°, Tilt: 45°-135°) can reach the physical robot.
4. **Hardware Plug-and-Play**: A single USB-C cable powers and provides bi-directional 115200 baud communication with the ESP32.

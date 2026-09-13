# 🤖 MOMO — Local-First Physical AI Companion & Autonomous Robotics Platform

> **The Laptop is MOMO's Brain. The ESP32 is MOMO's Physical Body. Computer Vision is MOMO's Eyes. Desktop Automation is MOMO's Hands.**

MOMO is an enterprise-grade, local-first physical AI companion robot. It unifies an expressive digital React avatar, an animated ESP32 physical robotic body with OLED vector eyes and servo neck articulations, an 18-sensor FACS computer vision perception engine, a multi-supervisor LangGraph state machine, a 9-agent Mixture of Agents (MoA) research subsystem, and an autonomous desktop automation engine with reinforcement learning capabilities.

---

## 📑 Table of Contents
1. [System Overview & Key Capabilities](#-system-overview--key-capabilities)
2. [Recent Updates](#-recent-updates)
3. [Complete Full-Stack Architecture (End-to-End)](#-complete-full-stack-architecture-end-to-end)
   - [Tier 1: Physical Hardware & Embedded Firmware Layer](#tier-1-physical-hardware--embedded-firmware-layer-esp32)
   - [Tier 2: Sensory Perception & Computer Vision Layer](#tier-2-sensory-perception--computer-vision-layer)
   - [Tier 3: Gateway, Networking & Transport Layer](#tier-3-gateway-networking--transport-layer)
   - [Tier 4: Companion Brain (LangGraph Multi-Supervisor Orchestration)](#tier-4-companion-brain-langgraph-multi-supervisor-orchestration)
   - [Tier 5: 9-Agent Mixture of Agents (MoA) Reasoning Subsystem](#tier-5-9-agent-mixture-of-agents-moa-reasoning-subsystem)
   - [Tier 6: Web Crawling & Real-Time Intelligence Squad](#tier-6-web-crawling--real-time-intelligence-squad)
   - [Tier 7: Hybrid Memory & Reinforcement Learning Layer](#tier-7-hybrid-memory--reinforcement-learning-layer)
   - [Tier 8: Desktop & Browser Automation Engine](#tier-8-desktop--browser-automation-engine)
   - [Tier 9: Local LLM Runtime & Hardware Acceleration](#tier-9-local-llm-runtime--hardware-acceleration)
   - [Tier 10: Frontend Client & Interactive UI Layer](#tier-10-frontend-client--interactive-ui-layer-react-18--vite--ts)
4. [Life of a User Request (End-to-End Data Flow)](#-life-of-a-user-request-end-to-end-data-flow)
5. [Comprehensive 30-Command Dual-Pass Verification Suite](#-comprehensive-30-command-dual-pass-verification-suite)
6. [Codebase Organization](#-codebase-organization)
7. [Quickstart & Operation Guide](#-quickstart--operation-guide)
8. [License](#-license)

---

## 🔄 Recent Updates

> All changes below were introduced after the initial full-architecture documentation and represent active improvements to robustness, reliability, and intelligence.

### September 2026 — Stability, Intelligence & UX Overhaul

| Commit | Area | Summary |
|--------|------|---------|
| `14ae1a5` | **Memory** | Maintain multi-turn chat memory and resolve anaphoric follow-up queries across agents — conversation context is now correctly threaded through `ConversationAgent`, `SearchScoutAgent`, `RelevanceAnalyzerAgent`, and the root supervisor. |
| `7ca1232` | **Vision** | Support low-clarity, dim, and noisy camera feeds with independent detector sizing and physiological skin chrominance filtering — FACS detection now succeeds in challenging lighting conditions. |
| `cc3e10d` | **Crawler** | Eliminate hallucinations via BM25 passage ranking, multi-engine search, infobox sanitization, and strict grounding — web research squad no longer fabricates facts. |
| `1946657` | **Response / Video** | Route knowledge queries to the web research squad and eliminate video stream proxy buffering with a smooth snapshot pipeline — general factual questions now reliably trigger the 4-stage research squad. |
| `ed24a68` | **Vision / Voice / Crawl** | Optimize video to a true 30 FPS streaming pipeline, add Speech-to-Text (STT) voice recognition, fix TTS clipping artefacts, and streamline web crawling squad configuration. |
| `779ed3b` | **LLM / UX** | Ensure dynamic LLM token generation (no caching stale responses), accelerate first-token latency, remove outdated quick-prompt shortcuts, and add scoped auto-scroll to the chat window. |
| `4b61492` | **Frontend** | Fix truncated short-input responses, clean up code-block rendering in the chat UI, and smooth real-time video tracking. |
| `c2e380f` | **Frontend** | Resolve blank-screen crash caused by a missing `streamError` state and absent `ErrorBoundary` wrapper. |
| `3f9a744` | **Launcher** | Resolve Windows batch syntax errors and incorrect path quoting in `start.bat` and `start_momo.bat`. |
| `8b8f5ab` | **Launcher** | Add automatic Node/npm PATH discovery, active server health polling, host-binding fixes, and reliable default-browser launching to the batch launchers. |
| `2232a6e` | **AI / Automation** | Eliminate LLM hallucinations via strict grounding, enforce bulleted structure for long responses, and add an anti-tutorial desktop guard that refuses to narrate instead of acting. |
| `eceb1d5` | **Vision / Crawling** | Resolve web-crawl hallucinations and fix video preview buffering race condition. |

---

## 🌟 System Overview & Key Capabilities

- **100% Local Intelligence**: Powered by Ollama (`hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0`, `qwen3:4b`, `llama3`, `mistral`) running entirely on-device without cloud API keys or subscriptions.
- **Physical Companion Body (ESP32)**: Single USB-C connection powers real-time animated vector eyes on a 128x64 I2C OLED display and 2-axis SG90 servo neck articulations (pan and tilt).
- **Sub-Millisecond Computer Vision**: Dedicated 30 FPS background acquisition thread with atomic JPEG frame caching (`<1ms` preview latency). Ocular-roll aligned lip slit crease geometry prevents false smile classifications on resting faces (`focused`/`neutral` with 85% confidence).
- **Autonomous Desktop Automation**: Instantly launches Windows applications (Notepad, Calculator, Terminal), opens web platforms (Instagram, YouTube, Google, GitHub, Twitter/X, Reddit, WhatsApp Web), and triggers anti-burnout game breaks (2048, Pacman, Wordle).
- **Multi-Agent Web Research Squad**: 4-stage squad (`SearchScout` -> `DeepScraper` -> `FactVerifier` -> `RelevanceAnalyzer`) backed by direct national RSS feeds (The Hindu, Indian Express, NDTV, Times of India) and Trafilatura / Crawl4AI article extraction, dated today (Sunday, September 13, 2026).
- **Reinforcement Learning & Memory Retention**: Dynamic rule ingestion (`"Remember that..."`, `"Learn that..."`, `"I prefer..."`) persisted into SQLite relational tables and ChromaDB semantic vector spaces, injected dynamically into LLM prompts.
- **Dual-Pass 30-Command Verification**: Verified across 30 diverse commands executed twice (60 executions total) with a **100% pass rate**.

---

## 🏛️ Complete Full-Stack Architecture (End-to-End)

The MOMO platform is architectured into **10 cohesive, modular tiers** spanning from physical hardware up to the interactive web frontend:

```mermaid
flowchart TD
    subgraph Tier10 ["Tier 10: Frontend Client Layer (React 18 + Vite + TS)"]
        UI_Avatar["MomoAvatar (Vector Face & Expressions)"]
        UI_Vision["VisionCard (Live Stream & FACS Telemetry)"]
        UI_Chat["ChatWindow (Streaming Markdown & Code)"]
        UI_IoT["Esp32Card (Hardware Telemetry & Servo Controls)"]
        UI_Work["WorkflowDashboard (MoA DAG Visualizer)"]
    end

    subgraph Tier3 ["Tier 3: Gateway, Networking & Transport Layer"]
        ASGI["Django ASGI Application (Channels + Daphne)"]
        REST_GW["REST API Endpoints (/api/...)"]
        WS_GW["WebSocket Gateway (/ws/momo/)"]
        Serial_GW["SerialBridge Protocol (115200 baud, 8N1)"]
        Prev_Cache["In-Memory Preview Cache (<1ms TTL)"]
    end

    subgraph Tier2 ["Tier 2: Sensory Perception & Computer Vision Layer"]
        Webcam["Laptop / External HD Webcam"]
        CamThread["CameraManager (30 FPS Lock-Free Buffer)"]
        FaceDetector["YuNet ONNX Face Detector"]
        FacsArray["18-Sensor FACS Action Unit Estimator"]
        RollAlign["Face-Roll Aligned Landmark Transform"]
        AttnTrack["AttentionTracker (EAR + Gaze Tracking)"]
        Proactive["ProactiveMonitor (Fatigue & Posture Alert)"]
        FaceRecog["FaceRecognizer (SFace Embeddings)"]
    end

    subgraph Tier1 ["Tier 1: Physical Hardware & Firmware Layer (ESP32)"]
        ESP32["ESP32 Microcontroller (Tensilica Dual-Core 240MHz)"]
        OLED["SSD1306 128x64 OLED (Vector Eyes)"]
        Servos["SG90 Micro Servos (Pan/Tilt 50Hz PWM)"]
        Buttons["Tactile Button & Status LED (GPIO Interrupts)"]
    end

    subgraph Tier4 ["Tier 4: Companion Brain (LangGraph Multi-Supervisor)"]
        RootSup["Root Supervisor (Intent Classifier)"]
        ConvSup["Conversation Supervisor"]
        AutoSup["Automation Supervisor"]
        ResSup["Research Supervisor"]
        FinSup["Finance Supervisor"]
        CommSup["Communication Supervisor"]
        VoxSup["Voice Supervisor"]
        SysNode["System Diagnostics Node"]
    end

    subgraph Tier5 ["Tier 5: 9-Agent Mixture of Agents (MoA) Subsystem"]
        MoA_Intake["Context & Intake Agent"]
        MoA_Decomp["Decomposition Agent"]
        MoA_RAG["Isolated RAG Agent"]
        MoA_Web["Temporal Web Search Agent"]
        MoA_Risk["Risk & Constraint Agent"]
        MoA_Plan["Strategic Planner Agent"]
        MoA_SolvA["Primary Solver A (Comprehensive)"]
        MoA_SolvB["Secondary Solver B (Concise)"]
        MoA_Judge["Evaluator & Judge Agent (Critique Loop)"]
    end

    subgraph Tier6 ["Tier 6: Web Crawling & Real-Time Intelligence Squad"]
        ScoutAgent["Search Scout Agent (Bing + Direct RSS + Wiki)"]
        ScraperAgent["Deep Scraper Agent (Trafilatura + Crawl4AI + BS4)"]
        VerifierAgent["Fact Verifier Agent (Consensus Scoring)"]
        RelevanceAgent["Relevance Analyzer Agent (Noise Filtering)"]
        TemporalSvc["TemporalService (Deterministic Date/Time/Calendar)"]
    end

    subgraph Tier7 ["Tier 7: Hybrid Memory & Reinforcement Learning Layer"]
        MemMgr["MemoryManager (High-Level Coordinator)"]
        RL_Engine["Reinforced Rule Extractor & Injector"]
        SQLite_DB[("SQLite Relational DB (Django ORM)")]
        Chroma_DB[("ChromaDB Vector Store (Collections)")]
        DistilBERT["DistilBERT Semantic Embeddings"]
    end

    subgraph Tier8 ["Tier 8: Desktop & Browser Automation Engine"]
        AutoAgent["AutomationAgent (LangGraph Agent)"]
        DeskCtrl["DesktopAutomationController (Apps & URLs)"]
        GameCtrl["GameAutomationController (Anti-Burnout 2048)"]
        MCP_Server["MOMO MCP Server (Model Context Protocol)"]
    end

    subgraph Tier9 ["Tier 9: Local LLM Runtime & Hardware Acceleration"]
        OllamaClient["OllamaClient (Per-Request HTTPX Timeouts)"]
        ModelMgr["ModelManager (Local GGUF Model Registry)"]
        GPUMgr["GPUManager (CUDA Detection & CPU Fallback)"]
        PromptBld["PromptBuilder (Persona + Telemetry + RL Rules)"]
        RespParser["ResponseParser (Anti-JSON & Anti-Cutoff)"]
    end

    %% Inter-Tier Connections
    Tier10 <-->|REST & WebSocket| Tier3
    Webcam --> CamThread --> FaceDetector --> FacsArray --> RollAlign --> AttnTrack --> Proactive
    CamThread --> Prev_Cache
    FaceDetector --> FaceRecog
    Tier3 <-->|Serial USB-C| Tier1
    ESP32 --> OLED
    ESP32 --> Servos
    ESP32 --> Buttons
    Tier3 <--> Tier4
    Tier4 --> Tier8
    Tier4 --> Tier6
    Tier4 --> Tier5
    Tier4 <--> Tier7
    Tier4 --> Tier9
    Tier8 --> DeskCtrl
    Tier8 --> GameCtrl
    Tier8 --> MCP_Server
    Tier6 --> ScoutAgent --> ScraperAgent --> VerifierAgent --> RelevanceAgent
    Tier6 <--> TemporalSvc
    Tier5 --> MoA_Intake --> MoA_Decomp --> MoA_Plan --> MoA_Judge
    Tier7 --> MemMgr --> SQLite_DB
    MemMgr --> Chroma_DB
    MemMgr <--> DistilBERT
    MemMgr <--> RL_Engine
    Tier9 --> PromptBld --> OllamaClient --> RespParser
    GPUMgr --> OllamaClient
```

---

### Tier 1: Physical Hardware & Embedded Firmware Layer (ESP32)

The physical body of MOMO is driven by an **ESP32-WROOM-32** dual-core microcontroller clocked at 240 MHz with 520 KB SRAM.

```mermaid
flowchart LR
    subgraph HostPC ["Host Laptop"]
        USB["USB-C Port"]
    end

    subgraph ESP32Core ["ESP32 Companion Controller"]
        UART["CP2102 / CH340 USB-UART (115200 baud)"]
        FreeRTOS["FreeRTOS Firmware Loop (PlatformIO C++)"]
        LEDC["LEDC Hardware PWM Controller"]
        I2C_Master["Hardware I2C Master (400 kHz)"]
        GPIO["Digital GPIO Matrix (Debounced)"]
    end

    subgraph Peripherals ["Physical Hardware Body"]
        OLED_Disp["SSD1306 0.96'' OLED (128x64, 0x3C)"]
        PanServo["SG90 Pan Servo (Yaw: 0° - 180°, Pin 13)"]
        TiltServo["SG90 Tilt Servo (Pitch: 45° - 135°, Pin 12)"]
        Btn["Pushbutton (Pin 4)"]
        LED["Status LED (Pin 2)"]
    end

    USB <-->|Framed JSON Packets| UART
    UART <--> FreeRTOS
    FreeRTOS --> I2C_Master --> OLED_Disp
    FreeRTOS --> LEDC --> PanServo
    FreeRTOS --> LEDC --> TiltServo
    GPIO <--> Btn
    FreeRTOS --> GPIO --> LED
```

- **Firmware Engine (`hardware/esp32/src/main.cpp`)**:
  - Implements a non-blocking FreeRTOS task architecture with strict frame-boundary serial buffering.
  - Receives JSON commands from the host laptop (`{"cmd": "expr", "name": "happy"}`, `{"cmd": "servo", "pan": 90, "tilt": 100}`).
  - Emits telemetry packets (`{"type": "telemetry", "btn": 0, "uptime": 124500}`).
- **OLED Vector Eye Renderer (`SSD1306`)**:
  - Renders 13 dynamic emotional states: `normal`, `happy`, `thinking`, `confused`, `sleepy`, `excited`, `sad`, `angry`, `surprised`, `proud`, `embarrassed`, `tired`, `stressed`.
  - Simulates natural human micro-expressions: procedural blinking with randomized 2-6 second intervals, pupil saccades, and squints.
- **Micro Servo Head Articulation (`SG90`)**:
  - 50 Hz PWM control (20ms period, 0.5ms to 2.5ms duty cycle) via ESP32 `ledc` peripheral.
  - Smooth trigonometric acceleration curves prevent mechanical servo chatter and simulate organic head gestures: nodding in agreement, tilting curiously, celebrating, and waving.

---

### Tier 2: Sensory Perception & Computer Vision Layer

Located in [`Backend/vision/`](file:///c:/Users/darshini/Desktop/MOMO/Backend/vision/), this tier processes live video frames from the webcam.

```mermaid
flowchart TD
    RawFrame["Camera Hardware (OpenCV VideoCapture)"] --> CamWorker["CameraManager Worker Thread"]
    
    subgraph AcquisitionLoop ["High-Throughput Acquisition (<33ms Native 30 FPS)"]
        CamWorker --> FrameBuffer["Lock-Free Atomic Frame Buffer"]
        FrameBuffer --> JPEGCache["Atomic JPEG Preview Cache (_last_preview_jpeg_bytes, 100ms TTL)"]
    end

    FrameBuffer --> FaceDetect["YuNet ONNX Deep Learning Face Detector"]

    subgraph LandmarkAndFACS ["Geometric Calibration & FACS Array"]
        FaceDetect --> RollVector["Ocular Roll Vector Calculation (Ux, Uy)"]
        RollVector --> TransformSpace["Roll-Aligned 2D Coordinate Transformation"]
        TransformSpace --> LipCrease["Lip Slit Crease Curvature Calculation"]
        LipCrease --> FACS18["18-Sensor FACS Action Unit Estimator"]
    end

    subgraph PerceptionPipelines ["Parallel Perception Engines"]
        TransformSpace --> AttentionEngine["AttentionTracker (EAR + Eye Tracking)"]
        AttentionEngine --> FatigueEngine["ProactiveMonitor (Continuous Work & Posture)"]
        FaceDetect --> IdentityEngine["FaceRecognizer (SFace 128D Embeddings)"]
    end

    LipCrease --> CleanEmotion["Calibrated Emotion (Neutral / Focused: 85% Conf)"]
    FatigueEngine --> FatigueSignal["Fatigue Alert (Suggest Rest / Game)"]
    IdentityEngine --> KnownUser["User Identification (face_profiles.json)"]
    JPEGCache --> PreviewAPI["GET /api/vision/preview/ (<0.2ms Latency Cache)"]
```

- **Camera Pipeline (`camera.py`)**:
  - DirectShow (`cv2.CAP_DSHOW`) primary hardware backend on Windows, verified for low-latency 640x480 video capture.
  - Background acquisition worker thread grabs frames continuously without artificial sleep delays, maintaining native 30 FPS hardware capture.
  - Thread-safe frame acquisition: dedicated background capture thread owns `cap.read()`, preventing hardware driver collisions and frame drops.
  - Auto-reconnection engine: automatically detects stalled camera frames (>3.0s) and gracefully re-initializes device handles without process restarts.
- **Sub-Millisecond In-Memory Preview Cache (`views.py`)**:
  - Background preview worker maintains a fresh annotated JPEG frame in memory (`_last_preview_jpeg_bytes`).
  - `/api/vision/preview/` serves cached frames in **0.11ms - 0.21ms** (over 10,000x faster than synchronous inference), preventing request queue buildup and ASGI thread pool exhaustion.
  - `/api/vision/stream/` delivers smooth 15 FPS multipart MJPEG video directly to connected clients.
- **Frontend Zero-Flicker Blob Rendering (`VisionCard.tsx`)**:
  - Single-pass Blob URL fetching (`fetch` -> `blob` -> `URL.createObjectURL(blob)`) eliminates duplicate HTTP requests, network race conditions, and false `onError` blackouts.
  - Releases old Object URLs cleanly to ensure zero client-side memory leakage.
  - Offers a quick toggle between `⚡ MJPEG Stream` and `📸 Snapshot Preview`.
- **Ocular-Roll Aligned Geometry (`expression_detector.py`)**:
  - Determines face tilt angle $\theta = \text{atan2}(R_y - L_y, R_x - L_x)$.
  - Normalizes 7 upper/lower lip landmarks into roll-invariant coordinates.
  - Calculates smile metric: $M = \frac{Y_{\text{center}} - (Y_{\text{left}} + Y_{\text{right}})/2}{\text{eye\_distance}}$.
  - Resting mouth ratio is negative ($-0.255$), correctly identifying neutral focus without false smile positives.
- **Attention & Fatigue Tracking (`attention.py`, `proactive_monitor.py`)**:
  - Computes Eye Aspect Ratio ($\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2\|p_1 - p_4\|}$) to track blinks and drowsy micro-sleeps.
  - Monitors session duration (>30 mins) and triggers gentle motivational breaks.
- **Face Recognition (`face_recognizer.py`)**:
  - Generates 128-dimensional L2-normalized embeddings via SFace ONNX model and compares against stored user profiles in `face_profiles.json`.

---

### Tier 3: Gateway, Networking & Transport Layer

Coordinates communication between the React frontend, host operating system, ESP32 companion, and backend agents.

- **ASGI Web Server (Django 5.x + Channels + Daphne)**:
  - Supports synchronous and asynchronous REST endpoints and persistent WebSocket connections.
- **High-Performance Endpoints (`Backend/api/views.py`)**:
  - `/api/vision/preview/`: Delivers live annotated camera frames from the 100ms JPEG cache in `<1ms`.
  - `/api/chat/`: Invokes the LangGraph `momo_graph` state machine with user inputs, returning assistant response, OLED expression, servo animation, and TTS flags.
  - `/api/workflow/execute/`: Runs the 9-agent Mixture of Agents research workflow.
  - `/api/automation/`: Triggers desktop application launches and mindful break games.
- **WebSocket Gateway (`/ws/momo/`)**:
  - Provides real-time bidirectional telemetry streaming: live emotional state, vision tracking metrics, ESP32 servo telemetry, and audio payloads.
- **USB-C Serial Bridge (`Backend/iot/serial_bridge.py`)**:
  - Scans COM ports for CP210x / CH340 devices.
  - Performs structured handshakes, auto-reconnects upon physical cable disconnect, and validates all servo angles against hardware allowlists.

---

### Tier 4: Companion Brain (LangGraph Multi-Supervisor Orchestration)

The Companion Brain (`Backend/graph/graph.py`) orchestrates multi-modal interaction using a LangGraph `StateGraph(MomoState)`.

```mermaid
flowchart TD
    Start([START]) --> Root["Root Supervisor (Regex & Semantic Classifier)"]

    Root -->|intent = automation| AutoSup["Automation Supervisor"]
    Root -->|intent = research / crawl| ResSup["Research Supervisor"]
    Root -->|intent = conversation / chat| ConvSup["Conversation Supervisor"]
    Root -->|intent = invoice / finance| FinSup["Finance Supervisor"]
    Root -->|intent = draft message| CommSup["Communication Supervisor"]
    Root -->|intent = voice speech| VoxSup["Voice Supervisor"]
    Root -->|intent = hardware diagnostics| SysNode["System Diagnostics Node"]

    AutoSup --> AutoAgent["Automation Agent (Apps, Sites, Games)"]
    AutoAgent --> ConvAgent["Conversation Agent (Fast 5s Confirmation Path)"]

    ResSup --> ScoutAgent["Search Scout Agent"]
    ScoutAgent --> ScraperAgent["Deep Scraper Agent"]
    ScraperAgent --> VerifierAgent["Fact Verifier Agent"]
    VerifierAgent --> RelevanceAgent["Relevance Analyzer Agent"]
    RelevanceAgent --> ConvAgent

    ConvSup --> MemAgent["Memory Agent (RL Facts & Rules)"]
    MemAgent --> ConvAgent

    FinSup --> DocAgent["Document Agent (PDF / OCR)"]
    FinSup --> RetAgent["Retrieval Agent (ChromaDB)"]
    DocAgent --> DataAgent["Data Analyzer Agent (Deterministic Math)"]
    RetAgent --> DataAgent
    DataAgent --> ConvAgent

    CommSup --> DataAgent
    DataAgent --> TextAgent["Texting Agent"]

    VoxSup --> STTAgent["STT Agent (Whisper)"]
    STTAgent --> ConvSup

    ConvAgent -->|speak = true| TTSAgent["TTS Agent (Piper TTS)"]
    ConvAgent -->|speak = false| End([END])
    TextAgent -->|speak = true| TTSAgent
    TextAgent -->|speak = false| End
    TTSAgent --> End
    SysNode --> End
```

- **Root Supervisor (`supervisors/root.py`)**:
  - Analyzes prompt syntax, intent keywords, and state metadata.
  - Dispatches to specialized supervisors without costly LLM round-trips.
- **Shared Pydantic State (`graph/state.py`)**:
  - `MomoState` maintains conversation history, active user identity, detected vision emotions, financial balance insights, retrieved chunks, supervisor routing decisions, and hardware command queues.
  - Merged deterministically via custom reducers.
- **Conversation Agent (`agents/conversation_agent.py`)**:
  - Assembles contextual prompts combining persona guidelines, active application context, vision telemetry, learned rules, and temporal anchors.
  - **Anti-Hallucination Grounding Architecture**:
    - Web research and crawled context are isolated from user memories into a dedicated `[VERIFIED REAL-TIME WEB RESEARCH & GROUNDED PASSAGES]` prompt block.
    - Verified source passages are injected directly into the in-turn user turn, ensuring high attention focus for compact local models (`Llama-3.2-1B-Instruct`).
    - Enforces greedy deterministic decoding (`temperature=0.0`) for research tasks, eliminating sampling-induced hallucinations.
    - Implements multi-tier hallucination detection: validates source entity overlap, guards against obsolete years (2020-2022), refuses canned filler, and automatically falls back to verified bullet-point synthesis from `RelevanceAnalyzerAgent`.
  - **Zero-Tutorial Desktop Automation Engine**:
    - Proactively intercepts automation intents (`open calculator`, `open github`, `launch notepad`, `play 2048`) via `DesktopAutomationController`, ensuring actions are always executed on the host OS.
    - Bulletproof anti-tutorial filter purges any numbered instructions (`1. Open... 2. Click...`), fake keyboard shortcuts (`Ctrl+C to open Calculator`), or disclaimers, instantly returning crisp affirmative confirmations (`"Opening <target> for you now!"` / `"Launching <target> on your desktop now!"`).
  - **Bulleted Information Structuring Engine**:
    - Whenever MOMO delivers complex explanations, rich research, multi-part answers, or deep knowledge, the response is structured cleanly with introductory framing followed by distinct, readable bullet points (`• `).
  - **System Prompt Echo & Scaffolding Purging**:
    - Strips all leaked prompt intros (`You are MOMO...`), memorized schema examples, and AI inability disclaimers (`As an AI language model...`).

---

### Tier 5: 9-Agent Mixture of Agents (MoA) Reasoning Subsystem

Located in [`Backend/ai_workflow/`](file:///c:/Users/darshini/Desktop/MOMO/Backend/ai_workflow/), this autonomous reasoning engine handles complex, multi-layered research tasks using a 9-agent DAG with parallel fan-out and synchronized fan-in merges:

```mermaid
flowchart TD
    Start([START]) --> Context["1. Intake & Context Agent"]
    Context -->|normalize input| Decomp["2. Decomposition Agent"]

    subgraph FanOutGathering ["Parallel Information Gathering (Fan-Out)"]
        Decomp --> RAG["3. Isolated RAG Agent (Tenant Vector Docs)"]
        Decomp --> WebSearch["4. Temporal Web Search & Crawler Agent"]
        Decomp --> Risk["5. Risk & Constraint Agent"]
    end

    RAG --> Plan["6. Strategic Planner Agent (Synchronized Fan-In)"]
    WebSearch --> Plan
    Risk --> Plan

    subgraph FanOutSolvers ["Parallel Mixture of Agents Solvers (Fan-Out)"]
        Plan --> SolverA["7. Primary Solver A (Comprehensive Draft)"]
        Plan --> SolverB["8. Secondary Solver B (Concise & Focused Draft)"]
    end

    SolverA --> Judge["9. Evaluator & Judge Agent (Cross-Examination Fan-In)"]
    SolverB --> Judge

    Judge -->|confidence >= 0.80| FinalSuccess["Finalize Success Node"]
    Judge -->|critique / retry needed| RetryNode["Retry Prep Node (Increment Counter)"]
    Judge -->|retries >= 3| FinalExhaust["Finalize Exhausted Node"]

    RetryNode -->|feedback injection| Plan
    FinalSuccess --> End([END])
    FinalExhaust --> End
```

| Agent | Responsibility | Core Implementation |
|:---|:---|:---|
| **1. Context Agent** | Input validation, prompt normalization, tenant security validation | Extracts parameters, isolates workspace boundaries |
| **2. Decomposition Agent** | Breaks complex goals into ordered sub-goals and dependency trees | Deconstructs multi-part queries |
| **3. Isolated RAG Agent** | Semantic retrieval from isolated tenant ChromaDB collections | Bounded vector search without cross-tenant leakage |
| **4. Temporal Web Search** | Real-time web discovery with deterministic date/time anchors | Queries live RSS news feeds and Wikipedia APIs |
| **5. Risk & Constraint** | Identifies compliance boundaries, hallucination risks, and safety bounds | Formulates guardrail directives |
| **6. Strategic Planner** | Synthesizes RAG context, web intelligence, and risk boundaries | Generates unified execution directives |
| **7. Primary Solver (A)** | Detailed, exhaustive candidate response with full citations | High-recall generation branch |
| **8. Secondary Solver (B)** | Direct, concise alternative formulation focusing on precision | High-precision generation branch |
| **9. Evaluator & Judge** | Cross-examines Solvers A & B, scores confidence, validates claims | Synthesizes final response or requests plan revisions |

---

### Tier 6: Web Crawling & Real-Time Intelligence Squad

Solves the LLM knowledge-cutoff limitation without requiring cloud API subscriptions:

```mermaid
flowchart TD
    UserQuery["User Prompt (e.g. 'tell me its latest news with the date and time')"] --> Scout["1. Search Scout Agent"]
    
    subgraph MultiSourceScout ["Scouting & Discovery"]
        Scout --> QueryExp["expand_query (Strip Wrappers & Noise)"]
        Scout --> DirectFeeds["Direct National RSS Feeds (The Hindu, Indian Express, NDTV, TOI)"]
        Scout --> BingAPI["Bing Live Search Engine"]
        Scout --> WikiAPI["Wikipedia OpenSearch / Holidays API"]
        Scout --> DirectURL["Direct Domain Routing (e.g. python.org, wikipedia.org)"]
    end

    MultiSourceScout --> Dedup["URL Deduplication & Candidate Assembly"]
    Dedup --> Scraper["2. Deep Scraper Agent"]

    subgraph MultiTierScraper ["4-Tier High-Density Extraction Hierarchy"]
        Scraper --> T1["Tier 1: Trafilatura (Clean Body Text Extraction)"]
        Scraper --> T2["Tier 2: Readability-lxml (Document Scoring)"]
        Scraper --> T3["Tier 3: Crawl4AI (Async JavaScript Headless Crawler)"]
        Scraper --> T4["Tier 4: BeautifulSoup4 (Semantic Paragraph Parsing)"]
    end

    MultiTierScraper --> Verifier["3. Fact Verifier Agent"]
    Verifier --> FactScoring["Consensus Scoring & Contradiction Filtration"]
    FactScoring --> Relevance["4. Relevance Analyzer Agent"]

    subgraph RelevanceSelection ["Relevance & Noise Filtration"]
        Relevance --> StripBoilerplate["Remove Paywalls, Cookie Notices & Ads"]
        Relevance --> KeywordDensity["Keyword Density & Temporal Matching"]
        Relevance --> KeyBulletPassages["Top 4 Relevant Passages"]
    end

    KeyBulletPassages --> LLMConv["Conversation Agent"]
    LLMConv --> DatePrepend["Deterministic Date/Time Prepend (Today is Sunday, September 13, 2026)"]
    DatePrepend --> UserResponse["Verified Grounded Response to User"]
```

- **Direct RSS Feeds**: Bypasses search engine redirect wrappers by pulling full journalistic RSS feeds directly from The Hindu, Indian Express, NDTV, and Times of India, dated today (**Sunday, September 13, 2026**).
- **Deterministic Temporal Grounding (`TemporalService`)**: Computes exact target dates in `Asia/Kolkata` timezone. Includes national and global observances (e.g., International Programmers' Day on September 13, the 256th day of the year).

---

### Tier 7: Hybrid Memory & Reinforcement Learning Layer

MOMO maintains a unified dual-layer memory system combining relational ACID persistence with dense vector similarity search:

```mermaid
flowchart TD
    UserTurn["User Turn Input / Reinforcement Directive"] --> MemMgr["MemoryManager"]

    subgraph PatternDetection ["Reinforcement Learning Extraction"]
        MemMgr --> RLPats{"Matches Reinforcement Patterns? ('Remember that...', 'Learn that...', 'I prefer...')"}
        RLPats -->|yes: extract rule / preference| StoreRL["Extract Rule String & Confidence (1.0)"]
        RLPats -->|no: standard conversational turn| StoreChat["Standard Conversation Log"]
    end

    subgraph Layer1_Relational ["Layer 1: Relational SQLite Store (Django ORM)"]
        StoreRL --> DB_Facts["MemoryItem (fact_type='rule' | 'preference' | 'identity')"]
        StoreRL --> DB_Prefs["UserPreference (key='backend_language', value='Python')"]
        StoreChat --> DB_Logs["MessageLog (Full Turn Transcript)"]
    end

    subgraph Layer2_Vector ["Layer 2: Semantic Vector Store (ChromaDB Persistent)"]
        StoreRL --> DistilBERT_Embed["DistilBERT Dense Vector Embedder"]
        StoreChat --> DistilBERT_Embed
        DistilBERT_Embed --> Coll_Saved[("Collection: momo_saved_memories")]
        DistilBERT_Embed --> Coll_Chats[("Collection: momo_chat_history")]
    end

    subgraph HybridRecallPipeline ["Bi-Directional Recall & Prompt Injection"]
        UserQuery["Next User Turn (e.g. 'What is my project name?')"] --> RecallQuery["MemoryManager.get_active_reinforced_rules()"]
        DB_Facts --> RecallQuery
        Coll_Saved --> RecallQuery
        RecallQuery --> PromptInjection["[ACTIVE REINFORCED RULES LEARNED FROM USER]:\n- Learned rule: My project name is MOMO Robot\n- Learned rule: I prefer Python for backend coding"]
        PromptInjection --> LLMContext["PromptBuilder System Prompt Context"]
    end
```

- **Reinforcement Learning Pattern Matching**:
  - Regex patterns identify user teachings (`"Remember that..."`, `"Learn that..."`, `"From now on..."`, `"My project name is..."`, `"I prefer..."`).
  - Stored with `fact_type="rule"`, `confidence=1.0`, `source="reinforcement_learning"`.
- **System Prompt Conditioning**:
  - Dynamic injection of learned rules under `[ACTIVE REINFORCED RULES LEARNED FROM USER]` conditions the LLM to adhere to all past user directives.
- **Bi-Directional Recall**:
  - Merges SQLite exact keyword matches with ChromaDB cosine similarity matches for comprehensive memory recall.

---

### Tier 8: Desktop & Browser Automation Engine

Executes desktop actions on the host machine:

- **Universal Desktop Controller (`Backend/automation/desktop_controller.py`)**:
  - Opens web platforms (Instagram, YouTube, Google, GitHub, Twitter/X, Reddit, WhatsApp Web, LinkedIn, Netflix) in the user's default browser.
  - Launches Windows desktop tools (`notepad.exe`, `calc.exe`, `wt.exe`).
  - Dry-Run Safety: Setting `MOMO_AUTOMATION_DRY_RUN=1` allows automated test suites to verify routing and LLM generation without opening dozens of windows.
- **Game Automation Controller (`Backend/automation/game_controller.py`)**:
  - Mindful break launcher for anti-burnout recovery (2048, Pacman, Wordle, Little Alchemy).
- **MOMO MCP Server (`Backend/automation/momo_mcp_server.py`)**:
  - Implements the Model Context Protocol (MCP) standard, exposing automation tools (`momo_open_website`, `momo_launch_app`, `momo_launch_game`, `momo_web_crawl`) to external agent runtimes.

---

### Tier 9: Local LLM Runtime & Hardware Acceleration

- **Ollama Client (`Backend/ai/ollama_client.py`)**:
  - Native asynchronous HTTP client communicating with Ollama on port `11434`.
  - **Per-Request Timeouts**: Uses per-request timeouts on `client.post(..., timeout=req_timeout)` rather than singleton client timeouts, allowing fast 5s automation paths without prematurely terminating complex 30-60s CPU inferences.
  - **Keep-Alive**: Keeps models memory-resident (`keep_alive: 60m`) for sub-second subsequent responses.
- **Prompt Builder (`Backend/ai/prompt_builder.py`)**:
  - Combines MOMO persona guidelines, FACS emotion telemetry, active application context, learned reinforcement rules, and deterministic temporal anchors into an assembled prompt.
- **Response Parser (`Backend/ai/response_parser.py`)**:
  - Multi-layer regex sanitizer that extracts clean messages, avatar expressions, and servo animations while eliminating raw JSON brackets and AI cutoff excuses.

---

### Tier 10: Frontend Client & Interactive UI Layer (React 18 + Vite + TS)

Built with React 18, Vite, TypeScript, and Tailwind CSS in [`Frontend/src/`](file:///c:/Users/darshini/Desktop/MOMO/Frontend/src/):

- **`MomoAvatar`**: Interactive SVG/Canvas companion displaying animated OLED vector eyes, emotional facial expressions, and talking mouth shapes synced to TTS audio.
- **`VisionCard`**: Real-time webcam preview with an attention meter, 18-sensor FACS Action Unit telemetry badge, and fatigue alerts.
- **`ChatWindow`**: Streaming multi-turn conversation interface with Markdown formatting, syntax-highlighted code blocks, quick-action chips, and voice input.
- **`Esp32Card`**: Hardware companion monitor showing USB-C connection status, firmware heartbeat latency, and manual servo pan/tilt controls.
- **`DocumentUploader` & `InvoiceCard`**: Multi-format document ingestion interface with deterministic balance-due calculation cards.
- **`WorkflowDashboard`**: Visual execution graph inspector for the 9-agent Mixture of Agents workflow.

---

## 🔄 Life of a User Request (End-to-End Data Flow)

To illustrate how all 10 tiers collaborate, here is the complete trace of a user request:

### Example: *"tell me its latest news with the date and time"*

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as Tier 10: React UI (ChatWindow / VisionCard)
    participant Gateway as Tier 3: Django ASGI Gateway (/api/chat/)
    participant Vision as Tier 2: Computer Vision (Camera & FACS)
    participant LangGraph as Tier 4: LangGraph Brain (Root Supervisor)
    participant Research as Tier 6: Web Research Squad
    participant Temporal as Tier 6: TemporalService
    participant Memory as Tier 7: Hybrid Memory (SQLite + ChromaDB)
    participant LLM as Tier 9: Ollama LLM Runtime
    participant Hardware as Tier 1: ESP32 Robot (OLED & Servos)

    User->>Frontend: Types "tell me its latest news with the date and time"
    Vision->>Frontend: Continuous frame perception (neutral focus, EAR=0.31, roll-aligned)
    Frontend->>Gateway: POST /api/chat/ {message, vision_state, session_id}
    Gateway->>LangGraph: momo_graph.ainvoke(MomoState)
    LangGraph->>LangGraph: RootSupervisor.evaluate_route() -> routes to "research"
    LangGraph->>Research: ResearchSupervisor -> SearchScoutAgent
    Research->>Temporal: get_temporal_anchor()
    Temporal-->>Research: Date=2026-09-13, Day=Sunday, Time=06:00 PM, TZ=Asia/Kolkata
    Research->>Research: SearchScout pulls live RSS feeds (The Hindu, Indian Express, NDTV)
    Research->>Research: DeepScraper extracts article body via Trafilatura / Readability
    Research->>Research: FactVerifier validates source credibility & consensus
    Research->>Research: RelevanceAnalyzer filters boilerplate & extracts key facts
    Research->>LangGraph: Updates retrieved_context with verified headlines
    LangGraph->>Memory: Recall active reinforced rules & user preferences
    Memory-->>LangGraph: Returns learned rules (project name, coding preference)
    LangGraph->>LLM: ConversationAgent calls OllamaClient.chat() with temporal grounding prompt
    LLM-->>LangGraph: Raw completion received
    LangGraph->>LangGraph: ResponseParser cleans text & prepends deterministic date/time anchor
    LangGraph->>Gateway: Returns MomoResponse (message, expression="thinking", animation="nod")
    Gateway->>Hardware: Serial packet: {"cmd": "expr", "name": "thinking"}, {"cmd": "servo", "tilt": 105}
    Hardware->>Hardware: OLED renders thinking eyes; SG90 tilt servo performs gentle nod
    Gateway-->>Frontend: JSON response with verified headlines & today's date/time
    Frontend-->>User: Displays clean grounded news with animated avatar response
```

---

## 🧪 Comprehensive 30-Command Dual-Pass Verification Suite

MOMO includes an automated verification runner ([`Backend/tests/test_30_commands_suite.py`](file:///c:/Users/darshini/Desktop/MOMO/Backend/tests/test_30_commands_suite.py)) that executes 30 diverse commands twice in succession (60 executions total):

### Verification Results Summary

| Category | Commands Tested | Round 1 Pass Rate | Round 2 Pass Rate | Overall Result | Average Latency |
|---|---|---|---|---|---|
| **Desktop & Browser Automation** | 10 commands | **10 / 10 (100%)** | **10 / 10 (100%)** | **20 / 20 PASS** | ~1.1s |
| **Web Crawling & Real-Time Research** | 10 commands | **10 / 10 (100%)** | **10 / 10 (100%)** | **20 / 20 PASS** | ~7.2s |
| **LLM Reasoning & Reinforcement** | 10 commands | **10 / 10 (100%)** | **10 / 10 (100%)** | **20 / 20 PASS** | ~3.8s |
| **Total Test Suite** | **30 Commands** | **30 / 30 (100%)** | **30 / 30 (100%)** | **60 / 60 PASS (100%)** | **Overall 100%** |

### Complete 30-Command Specification

| # | ID | Category | Command Query | Route | Handled By | Expected Output Behavior |
|---|---|---|---|---|---|---|
| 1 | AUTO-01 | Automation | `open instagram` | `automation` | `automation_agent` | Launches Instagram URL; articulates cheerful confirmation. |
| 2 | AUTO-02 | Automation | `open youtube` | `automation` | `automation_agent` | Launches YouTube URL; confirms video platform access. |
| 3 | AUTO-03 | Automation | `open google` | `automation` | `automation_agent` | Launches Google Search in default web browser. |
| 4 | AUTO-04 | Automation | `open github` | `automation` | `automation_agent` | Launches GitHub repository portal. |
| 5 | AUTO-05 | Automation | `open twitter` | `automation` | `automation_agent` | Launches X (Twitter) social network. |
| 6 | AUTO-06 | Automation | `open reddit` | `automation` | `automation_agent` | Launches Reddit community discussions. |
| 7 | AUTO-07 | Automation | `open whatsapp` | `automation` | `automation_agent` | Launches WhatsApp Web interface. |
| 8 | AUTO-08 | Automation | `open notepad` | `automation` | `automation_agent` | Launches `notepad.exe` on host Windows desktop. |
| 9 | AUTO-09 | Automation | `open calculator` | `automation` | `automation_agent` | Launches `calc.exe` on host Windows desktop. |
| 10 | AUTO-10 | Automation | `play 2048` | `automation` | `automation_agent` | Launches anti-burnout game 2048 for mindful break. |
| 11 | CRAWL-01 | Crawling | `tell me its latest news with the date and time` | `research` | `research_squad` | Grounded with today's date (September 13, 2026) and live headlines. |
| 12 | CRAWL-02 | Crawling | `latest breaking news in India` | `research` | `research_squad` | Live national news from The Hindu / Indian Express RSS feeds. |
| 13 | CRAWL-03 | Crawling | `what is happening with Smart India Hackathon` | `research` | `research_squad` | Real-time web intelligence on SIH initiatives and schedules. |
| 14 | CRAWL-04 | Crawling | `what special day is today` | `research` | `research_squad` | Identifies September 13 as International Programmers' Day. |
| 15 | CRAWL-05 | Crawling | `what is the current date and time` | `research` | `research_squad` | Deterministic anchor: Sunday, September 13, 2026 (Asia/Kolkata). |
| 16 | CRAWL-06 | Crawling | `web crawl python.org` | `research` | `research_squad` | Direct crawl of `python.org` official website content. |
| 17 | CRAWL-07 | Crawling | `web crawl wikipedia.org` | `research` | `research_squad` | Direct crawl of `wikipedia.org` encyclopedic content. |
| 18 | CRAWL-08 | Crawling | `latest tech developments in AI 2026` | `research` | `research_squad` | Live tech news articles scraped via Crawl4AI / NDTV feeds. |
| 19 | CRAWL-09 | Crawling | `news updates from the hindu` | `research` | `research_squad` | Verified journalistic dispatches from The Hindu RSS feeds. |
| 20 | CRAWL-10 | Crawling | `latest indian space research updates` | `research` | `research_squad` | Real-time space research headlines dated today. |
| 21 | LLM-01 | LLM | `Hello MOMO, how are you doing today?` | `conversation` | `conversation_agent` | Warm, articulate, persona-aligned greeting. |
| 22 | LLM-02 | LLM | `Explain quantum computing in simple terms for a beginner.` | `conversation` | `conversation_agent` | Clear, accessible explanation of qubits, superposition, and entanglement. |
| 23 | LLM-03 | Reinforcement | `Remember that my project name is MOMO Robot.` | `conversation` | `memory_agent` | Ingests fact into SQLite + ChromaDB permanent memory. |
| 24 | LLM-04 | Reinforcement | `What is my project name?` | `conversation` | `conversation_agent` | Instant recall: *"My project name is MOMO Robot."* |
| 25 | LLM-05 | Reinforcement | `Learn that I prefer Python for backend coding.` | `conversation` | `memory_agent` | Ingests coding preference as active reinforced rule. |
| 26 | LLM-06 | Reinforcement | `What programming language do I prefer for backend work?` | `conversation` | `conversation_agent` | Recalls Python preference and articulates recommendation. |
| 27 | LLM-07 | LLM | `If a train leaves Station A at 60 km/h and another leaves Station B at 90 km/h towards each other, 300 km apart, when do they meet?` | `conversation` | `conversation_agent` | Solves multi-step math correctly: relative speed = 150 km/h -> 2 hours. |
| 28 | LLM-08 | LLM | `I have been studying for 4 hours and feeling a bit tired.` | `conversation` | `conversation_agent` | Compassionate empathy, acknowledges prolonged study, suggests restful break. |
| 29 | LLM-09 | LLM | `Write a Python function to check if a string is a palindrome.` | `conversation` | `conversation_agent` | Generates valid Python code with docstring and edge-case handling. |
| 30 | LLM-10 | LLM | `What is the current system and hardware status of MOMO?` | `system` | `system_node` | Instant telemetry check: hardware allowlists and servos operational. |

---

## 📂 Codebase Organization

```text
MOMO/
├── Backend/
│   ├── ai_workflow/             # 9-Agent MoA RAG Subsystem & Services
│   │   ├── agents/              # Context, Decomp, RAG, Web, Risk, Plan, Solvers A/B, Judge
│   │   ├── services/            # LiveWebCrawlerService, TemporalService, MockAIService
│   │   ├── graph.py             # MoA LangGraph workflow definition
│   │   └── state.py             # Pydantic WorkflowState, EvaluationResult, Citation
│   ├── api/                     # REST API endpoints, serializers, and preview JPEG caching
│   │   ├── urls.py              # Routing for chat, memory, vision, devices, automation
│   │   └── views.py             # Views with sub-millisecond preview cache and chat runner
│   ├── automation/              # Desktop & Game Automation Engine
│   │   ├── desktop_controller.py# App launcher, URL opener, dry-run safety engine
│   │   ├── game_controller.py   # Anti-burnout game breaks (2048, Pacman, Wordle)
│   │   └── momo_mcp_server.py   # Model Context Protocol (MCP) tool integration
│   ├── brain/                   # Persona definitions, tone guidelines, ASCII expressions
│   ├── graph/                   # Companion Brain LangGraph definition, state, reducers
│   ├── supervisors/             # Supervisors: Root, Conversation, Finance, Communication, Voice, Automation, Research
│   ├── agents/                  # Specialized agents (Conversation, Memory, Texting, Retrieval,
│   │                            #   Automation, SearchScout, DeepScraper, FactVerifier, RelevanceAnalyzer)
│   ├── ai/                      # OllamaClient (per-request timeouts), PromptBuilder (RL injection),
│   │                            #   ModelManager, GPUManager (OOM recovery), ResponseParser
│   ├── vision/                  # Real-Time Computer Vision & Emotion Perception
│   │   ├── camera.py            # High-throughput 30 FPS background thread
│   │   ├── expression_detector.py # Ocular-roll aligned lip slit crease geometry & FACS array
│   │   ├── face_recognizer.py   # Face embedding match against face_profiles.json
│   │   ├── proactive_monitor.py # Fatigue and posture tracking with motivational alerts
│   │   └── face.py, attention.py# Landmark alignment and gaze tracking
│   ├── memory/                  # Dual-layer Memory: SQLite relational + ChromaDB vector
│   │   ├── memory_manager.py    # High-level coordinator, rule extraction patterns, recall
│   │   ├── chroma_memory.py     # ChromaDB vector collections with DistilBERT embeddings
│   │   └── repository.py        # Django ORM repository for MessageLog, MemoryItem, UserPreference
│   ├── iot/                     # USB-C SerialBridge protocol, DeviceRegistry, ESP32 handshake
│   ├── security/                # Privacy permissions & hardware allowlists
│   └── tests/                   # Test suite
│       ├── test_30_commands_suite.py # Dual-pass 30-command verification runner
│       ├── test_30_commands_results.json # Execution logs and timing metrics
│       ├── test_automation_and_supervisors.py
│       ├── test_web_crawler_service.py
│       ├── test_temporal_service.py
│       ├── test_game_controller.py
│       ├── test_vision_pipeline.py
│       └── test_vision_preview.py
├── Frontend/
│   ├── src/
│   │   ├── components/          # MomoAvatar, ChatWindow, VisionCard, DocumentUploader, etc.
│   │   ├── services/            # REST API client & persistent WebSocket gateway
│   │   └── App.tsx              # Main dashboard with real-time video, chat, and telemetry
│   └── vite.config.js
├── hardware/
│   └── esp32/                   # PlatformIO C++ firmware for SSD1306 OLED & SG90 servos
├── start_momo.bat               # One-click full-stack launcher
└── README.md
```

---

## ⚡ Quickstart & Operation Guide

### 1. Launch MOMO Full-Stack (One-Click)
Double-click `start_momo.bat` from the root folder.
This script automatically:
1. Connects to the USB-C ESP32 companion robot.
2. Boots the Django ASGI backend at `http://127.0.0.1:8000/`.
3. Boots the React frontend dashboard at `http://localhost:5173/`.
4. Launches your default web browser to the dashboard.

### 2. Run the Full 30-Command Dual-Pass Test Suite
From the repository root:
```powershell
Backend\venv\Scripts\python.exe -u Backend\tests\test_30_commands_suite.py
```
This executes all 30 commands across Automation, Web Crawling, and LLM / Reinforcement twice (60 executions total) and saves detailed timing metrics and outputs to `Backend/tests/test_30_commands_results.json`.

### 3. Run Backend Regression Unit Tests
From the `Backend/` directory:
```powershell
venv\Scripts\python.exe manage.py test tests.test_automation_and_supervisors tests.test_web_crawler_service tests.test_temporal_service tests.test_game_controller tests.test_vision_pipeline tests.test_vision_preview
```

### 4. Build Frontend for Production
From the `Frontend/` directory:
```powershell
npm run build
```

---

## 📜 License
MIT License. Built for the open-source physical AI companion and autonomous robotics community.

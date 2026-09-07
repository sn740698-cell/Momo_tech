# 🤖 MOMO — Local-First Physical AI Companion

> **The Laptop is MOMO's Brain. The ESP32 is MOMO's Physical Body.**

MOMO is a production-quality, modular, local-first AI platform that combines an expressive digital companion in React with an animated physical robotic body built on ESP32, coordinated by a LangGraph multi-supervisor state workflow.

---

## 🌟 Key Capabilities

- **100% Local Intelligence**: Powered by Ollama (`qwen3:4b`, `llama3`, `mistral`, etc.) without mandatory cloud APIs.
- **Physical Robotic Body (ESP32)**:
  - **One-Click USB-C Connection**: Plug the ESP32 into your laptop via USB-C and launch with `start_momo.bat`.
  - **SSD1306 128x64 OLED**: Renders vector eyes and facial expressions in real-time.
  - **SG90 Micro Servos**: Pan and tilt head articulations (nod, tilt, celebrate, wave).
  - **Status LED & Pushbutton**: Interactive tactile feedback.
- **LangGraph Multi-Supervisor Orchestration**:
  - **Root Supervisor**: Dispatches turns to specialized supervisors.
  - **Conversation Supervisor**: Persona, humor, small-talk, and long-term memory retrieval.
  - **Finance Supervisor**: Invoice parsing, sentence-level BERT contextual analysis, and DistilBERT + ChromaDB retrieval.
  - **Communication Supervisor**: Deterministic balance-due message drafting via the Texting Agent.
  - **Voice Supervisor**: Local Whisper STT and Piper TTS interfaces.
- **Multi-Agent RAG & Workflow Subsystem (`Backend/ai_workflow`)**:
  - **9 Specialized Agents (MoA Architecture)**: Context, Decomposition, Isolated RAG, Temporal Web Search, Risk & Constraint, Planning, Primary Solver (A), Secondary Solver (B), and Evaluator / Judge.
  - **Mixture of Agents (MoA) Parallel Execution**: Parallel solver branches with synchronized fan-in and structured Pydantic evaluation.
  - **Real-Time Web Search & Deep Article Crawler**:
    - Zero-cost live news retrieval via Google News RSS (with exact `pubDate` timestamps, official sources like Press Information Bureau, LiveLaw, and national press) and DuckDuckGo fallback.
    - Focused asynchronous `httpx` article text extraction with HTML noise stripping.
  - **Deterministic Temporal Grounding**:
    - Calculates calendar math deterministically (`today`, `yesterday`, `tomorrow`, day of week, timezone `Asia/Kolkata`).
    - Resolves queries like *"what happened yesterday?"* to exact date boundaries without LLM hallucinations.
    - Built-in calendar registry of national and international observances for instant answers to *"what special today is?"*.
  - **Anti-Hallucination & Conditional Retry Loop**: Deterministic critique feedback, bounded confidence (`0.0 - 1.0`), and strict zero-citation fabrications.
  - **Anti-JSON Leakage & Cutoff Disclaimer Defense**:
    - Multi-layer shield across System Prompts, Parsers, Agents, and Frontend UI preventing raw JSON brackets or AI knowledge cutoff excuses from ever entering the chat.
  - **Tenant & Project Isolation**: Partitioned vector search and execution history with zero cross-tenant leakage.
  - **Deterministic Mock Mode**: Full offline execution path via `AI_MOCK_MODE=true` without external API credentials.
- **Deterministic Financial Safety**:
  - Arithmetic source of truth: `Balance Due = Invoice Total - Amount Paid`.
  - The generative LLM is never allowed to hallucinate financial figures.
- **Privacy & Security Allowlisting**:
  - Camera, mic, and memory toggles with instant data wipe.
  - Hardware commands strictly validated against allowlists before transmission.
- **RTX 2050 GPU Optimization**:
  - Low-VRAM footprint (4GB target) with `torch.inference_mode()`, CUDA memory clearing, and seamless CPU fallback upon CUDA OOM.

---

## ⚡ Quickstart (One-Click Launch)

Simply double-click `start_momo.bat` in the root folder!
This will:
1. Connect to the USB-C ESP32 companion.
2. Start the Django ASGI Backend (`http://127.0.0.1:8000/`).
3. Start the React Frontend (`http://localhost:5173/`).
4. Launch your default browser directly into the MOMO dashboard.

---

## 📂 Project Structure

```text
momo/
├── Backend/
│   ├── ai_workflow/     # Multi-Agent MoA Subsystem (9 Agents, Web Search & Crawler, Temporal Service, LangGraph)
│   ├── api/             # Django REST Framework endpoints & serializers (/api/workflow/...)
│   ├── graph/           # Physical Companion MomoState, merge reducers, and LangGraph workflow
│   ├── supervisors/     # Root, Conversation, Finance, Communication, Voice
│   ├── agents/          # Specialized companion agents (Conversation, Texting, Retrieval, DataAnalyzer, etc.)
│   ├── ai/              # Resilient OllamaClient, ModelManager, GPUManager (OOM recovery), ResponseParser
│   ├── nlp/             # BERT contextual analysis & DistilBERT embeddings
│   ├── retrieval/       # ChromaDB vector collection and semantic query filters
│   ├── documents/       # Parser, Chunker, and DocumentProcessor
│   ├── finance/         # Deterministic Calculator, Validator, and Extractor
│   ├── iot/             # USB-C SerialBridge, DeviceRegistry, Heartbeat, and Protocol
│   ├── security/        # Privacy permission toggles & hardware command allowlists
│   └── tests/           # Full unit and integration test suite (Temporal, Crawler, MoA, Workflow, State)
├── Frontend/
│   ├── src/
│   │   ├── components/  # MomoAvatar, ChatWindow, DocumentUploader, InvoiceCard, Esp32Card, etc.
│   │   ├── services/    # REST API client & persistent WebSocket gateway (/ws/momo/)
│   │   └── App.tsx      # Main application with Dashboard, Chat, Documents, Finance, Settings
├── hardware/
│   └── esp32/           # PlatformIO project with C++ firmware for OLED, servos, and USB-C
├── docs/                # Complete architectural, state, agent, hardware, and API documentation
├── start_momo.bat       # Master one-click full-stack launcher
├── .env.example         # Environment template
└── README.md
```

---

## 🧪 Testing

Run the automated test suite from the `Backend/` directory:
```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Build the React frontend client:
```powershell
cd Frontend
npm run build
```

---

## 📜 License
MIT License. Built for the open-source physical AI companion community.

# 🤖 MOMO Multi-Supervisor & Agent Architecture

## 1. Supervisor Layer

MOMO implements a hierarchy of specialized supervisors in `supervisors/`:

### Root Supervisor (`supervisors/root.py`)
Examines inbound intent, context, and uploads. Routes to:
- `conversation_supervisor`: Normal conversation, playful persona, and small talk.
- `finance_supervisor`: Invoice ingestion, calculations, and semantic search.
- `communication_supervisor`: Drafting balance-due notifications and customer messages.
- `voice_supervisor`: Handling microphone audio and voice pipeline.
- `system_node`: Telemetry, settings, and hardware allowlist tests.

### Conversation Supervisor (`supervisors/conversation.py`)
Directs `memory_agent` to query preferences and facts, then activates `conversation_agent`.

### Finance Supervisor (`supervisors/finance.py`)
Coordinates:
- `document_agent`: Ingests raw uploads and text into ChromaDB.
- `retrieval_agent`: Semantically searches stored chunks with DistilBERT.
- `data_analyzer_agent`: Extracts financial facts and validates calculations deterministically.

### Communication Supervisor (`supervisors/communication.py`)
Coordinates with `data_analyzer_agent` for verified numbers and invokes `texting_agent` to draft messages.

---

## 2. Specialized Agent Layer

| Agent | Module | Role |
| :--- | :--- | :--- |
| **Conversation Agent** | `agents/conversation_agent.py` | Plays MOMO's witty persona; interfaces with local Ollama LLM. |
| **Memory Agent** | `agents/memory_agent.py` | Retrieves long-term preferences and facts when memory is enabled. |
| **Document Agent** | `agents/document_agent.py` | Coordinates parsing, chunking, and ChromaDB vector indexing. |
| **Retrieval Agent** | `agents/retrieval_agent.py` | Performs top-k cosine similarity queries in ChromaDB. |
| **Data Analyzer Agent** | `agents/data_analyzer_agent.py` | Validates arithmetic: `balance = total - paid`; classifies payment status. |
| **Texting Agent** | `agents/texting_agent.py` | Drafts polite, concise balance-due reminder messages. |
| **STT Agent** | `agents/stt_agent.py` | Transcribes audio via local Whisper interfaces. |
| **TTS Agent** | `agents/tts_agent.py` | Generates speech via local Piper neural TTS interfaces. |

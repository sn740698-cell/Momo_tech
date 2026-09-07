# 🔌 MOMO REST API & WebSocket Specification

## 1. REST API Endpoints

Base URL: `http://127.0.0.1:8000/api/`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health/` | Quick server health status. |
| `GET` | `/system/status/` | Complete system telemetry conforming to Section 74. |
| `GET` | `/memory/` | List stored memories and preferences. |
| `POST` | `/memory/` | Add a memory key/value pair. |
| `DELETE`| `/memory/` | Clear or wipe stored memories. |
| `GET` | `/devices/` | List registered ESP32 companions. |
| `GET` | `/devices/<id>/` | Telemetry for a specific ESP32 unit. |
| `GET` | `/ollama/status/` | Live Ollama runtime diagnostic. |
| `GET` | `/ollama/models/` | List installed models in Ollama library. |
| `POST` | `/documents/` | Upload PDF, TXT, or text invoice for processing. |
| `GET` | `/documents/` | List indexed documents. |
| `GET` | `/documents/<id>/` | Detail and chunks for a document. |
| `GET` | `/finance/<doc_id>/`| Verified financial insight for an invoice. |
| `GET` | `/settings/privacy/`| Fetch sensor and memory privacy permissions. |
| `POST` | `/settings/privacy/`| Update privacy permissions. |

---

## 2. WebSocket Gateway

Endpoint: `ws://127.0.0.1:8000/ws/momo/`

### Inbound Client Messages
- **Chat Message**:
  ```json
  {
    "type": "chat_message",
    "message": "What is the balance due on invoice INV-1042?",
    "session_id": "default"
  }
  ```
- **Device Command**:
  ```json
  {
    "type": "device_command",
    "expression": "happy",
    "animation": "celebrate",
    "led": "blink"
  }
  ```

### Outbound Gateway Messages
- **MOMO Response**:
  ```json
  {
    "type": "momo_response",
    "message": "The balance due on invoice INV-1042 is ₹28,500.00.",
    "expression": "happy",
    "animation": "nod",
    "speak": true,
    "draft_text": "Hi Rahul, this is a reminder...",
    "thinking": "...",
    "model": "qwen3:4b"
  }
  ```
- **Thinking Indicator**:
  ```json
  {
    "type": "momo_thinking",
    "is_thinking": true
  }
  ```

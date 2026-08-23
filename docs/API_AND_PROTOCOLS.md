# 📡 MOMO — API & Protocol Specifications

## 1. REST Endpoints

The Django backend exposes REST endpoints for initial bootstrapping, telemetry, model inspection, and stateless interactions.

### 1.1 Root API Metadata
- **URL**: `/api/`
- **Method**: `GET`
- **Description**: Returns backend service discovery metadata and online endpoint map.

### 1.2 System Health & Latency Telemetry
- **URL**: `/api/status/`
- **Method**: `GET`
- **Response**:
```json
{
  "status": "online",
  "service": "Django REST Backend",
  "framework": "Django 6.1",
  "backend_port": 8000,
  "timestamp": "2026-08-23 16:40:00"
}
```

### 1.3 Ollama Daemon Health & Model Discovery
- **URL**: `/api/ollama/status/`
- **Method**: `GET`
- **Response**:
```json
{
  "status": "online",
  "ollama_host": "http://127.0.0.1:11434",
  "version": "0.5.4",
  "models": [
    {
      "name": "qwen3:4b",
      "size": 2490589184,
      "modified_at": "2026-08-20T10:00:00Z"
    }
  ],
  "model_names": ["qwen3:4b"],
  "default_model": "qwen3:4b"
}
```

### 1.4 Chat Completion (Batch & SSE Stream)
- **URL**: `/api/chat/`
- **Method**: `POST`
- **Payload**:
```json
{
  "model": "qwen3:4b",
  "messages": [
    { "role": "user", "content": "Hello MOMO!" }
  ],
  "system_prompt": "You are MOMO AI, a friendly, concise, and helpful companion.",
  "temperature": 0.7,
  "stream": false
}
```

---

## 2. Real-Time WebSocket Protocol

- **Endpoint**: `/ws/momo/`
- **Format**: JSON UTF-8

### 2.1 Inbound Messages (Client $\rightarrow$ Backend)

#### Chat Message
```json
{
  "type": "chat_message",
  "message": "Hello MOMO!",
  "timestamp": 1724412000
}
```

#### Ping / Heartbeat
```json
{
  "type": "ping"
}
```

#### Context Update (Optional client telemetry)
```json
{
  "type": "context_update",
  "active_app": "VS Code",
  "idle_seconds": 15
}
```

### 2.2 Outbound Messages (Backend $\rightarrow$ Clients)

#### MOMO Character Response
```json
{
  "type": "momo_response",
  "message": "Hey! What are we building today?",
  "expression": "happy",
  "animation": "wave",
  "speak": true,
  "priority": "normal"
}
```

#### Thinking Indicator
```json
{
  "type": "momo_thinking",
  "is_thinking": true
}
```

#### Device Command (Broadcast to ESP32)
```json
{
  "type": "device_command",
  "device_id": "momo-01",
  "expression": "happy",
  "animation": "nod",
  "led": "blink"
}
```

#### Pong Response
```json
{
  "type": "pong",
  "timestamp": 1724412000
}
```

---

## 3. Error Handling & Status Codes

| Code | Status | Description |
| :--- | :--- | :--- |
| `200` | OK | Successful request |
| `400` | Bad Request | Missing or invalid JSON parameters |
| `404` | Model Not Found | Requested Ollama model is not pulled locally |
| `502` | Ollama Error | Local Ollama daemon returned an error |
| `503` | Service Offline | Local Ollama daemon is not running on port 11434 |

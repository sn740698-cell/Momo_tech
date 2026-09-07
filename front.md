# 🖥️ MOMO — Complete Frontend Specification (`front.md`)

> **Comprehensive Blueprint of all UI Pages, Tabs, Features, Components, Functions, State Variables, and Interactive Buttons.**

---

## 📑 Table of Contents

1. [Architecture & Technology Stack](#1-architecture--technology-stack)
2. [Global Page & Layout Structure](#2-global-page--layout-structure)
3. [Tab 1: AI Chatbot & Companion Interface](#3-tab-1-ai-chatbot--companion-interface)
4. [Tab 2: System Health & API Console](#4-tab-2-system-health--api-console)
5. [Drawers, Modals & Settings Panels](#5-drawers-modals--settings-panels)
6. [Complete Button & Function Directory](#6-complete-button--function-directory)
7. [State Variables & Hooks Architecture](#7-state-variables--hooks-architecture)
8. [Facial Expression & Animation Synchronizer](#8-facial-expression--animation-synchronizer)
9. [API & WebSocket Event Contracts](#9-api--websocket-event-contracts)
10. [Keyboard Shortcuts & Hotkeys](#10-keyboard-shortcuts--hotkeys)

---

## 1. Architecture & Technology Stack

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│                              MOMO FRONTEND CLIENT                              │
│                                                                                │
│   ┌────────────────────────┐  ┌─────────────────────────┐  ┌───────────────┐   │
│   │   React 19 + Vite      │  │  Tailwind CSS           │  │ PySide6 Shell │   │
│   │   Reactive State Core  │  │  Glassmorphism Theme    │  │ (Desktop Win) │   │
│   └───────────┬────────────┘  └───────────┬─────────────┘  └───────┬───────┘   │
│               │                           │                        │           │
│               └───────────────────┬───────┴────────────────────────┘           │
│                                   ▼                                            │
│               ┌──────────────────────────────────────────┐                     │
│               │ Dual Communication Layer                 │                     │
│               │  - HTTP REST / SSE Token Streaming       │                     │
│               │  - Django Channels WebSocket (/ws/momo/) │                     │
│               └───────────────────┬──────────────────────┘                     │
└───────────────────────────────────┼────────────────────────────────────────────┘
                                    ▼
                     Django Backend (:8000) / Ollama (:11434)
```

- **Framework**: React 19 with Vite (Fast HMR development).
- **Styling**: Tailwind CSS v3 / Glassmorphic dark theme (`slate-900`, `indigo-600`, `emerald-500`, `purple-500`).
- **Protocols**:
  - **REST API**: Health diagnostics (`/api/status/`, `/api/ollama/status/`, `/api/message/`).
  - **Server-Sent Events (SSE)**: Asynchronous token streaming for local LLM inference (`/api/chat/`).
  - **WebSocket Gateway**: Full-duplex persistent sync (`/ws/momo/`) for emotional state, companion facial sync, and ESP32 physical triggers.

---

## 2. Global Page & Layout Structure

The frontend shell is a responsive single-page application with a fixed-width container (`max-w-5xl`) centered on a dark canvas.

```text
+-------------------------------------------------------------------------------+
| [M] MOMO AI  (Ollama • qwen3:4b)  [● Ollama v0.5.1] [● Django (4ms)] [🤖][⚡] | <- Top Header
+-------------------------------------------------------------------------------+
|                                                                               |
|  [ TAB 1: 🤖 AI Chatbot ]               |  [ TAB 2: ⚡ API Console ]          |
|  - Model Selector & Stream Switch       |  - Fullstack Topology Diagram       |
|  - System Prompt / Temp Drawer          |  - Ollama Installed Models List     |
|  - Multi-Turn Chat Stream               |  - Live POST Payload Tester         |
|  - Expandable Reasoning Process         |  - REST Response Activity Log       |
|  - Quick Starter Prompts                |                                     |
|  - Auto-Expanding Textarea & Send/Stop  |                                     |
|                                                                               |
+-------------------------------------------------------------------------------+
| MOMO Local AI Platform • React 19 + Django 6.1 • Launcher: start.bat         | <- Footer
+-------------------------------------------------------------------------------+
```

---

## 3. Tab 1: AI Chatbot & Companion Interface

### 3.1 Header & Control Bar
- **Brand Identity**: Gradient icon `[M]`, application title **MOMO AI**, and active model badge.
- **Ollama Status Pill**:
  - Displays online version (`Ollama v0.5.1`) with glowing emerald radar ping.
  - Interactive: Click to trigger `checkOllamaHealth()` and re-scan installed models.
- **Django Status Pill**:
  - Displays backend connection and latency (`Django (12ms)`).
  - Interactive: Click to trigger `checkBackendHealth()` to test REST availability.
- **Tab Navigation Buttons**:
  - `[🤖 Chatbot]`: Activates primary companion screen (`setActiveTab('chat')`).
  - `[⚡ API Console]`: Activates system diagnostics and REST playground (`setActiveTab('health')`).

### 3.2 Model Selector & Parameter Bar
- **Model Dropdown / Custom Input**:
  - Displays auto-discovered Ollama models (e.g. `qwen3:4b`, `llama3`, `mistral`, `deepseek-r1`).
  - Selecting `+ Enter custom model name...` switches to direct text input for unlisted or fine-tuned weights.
  - `[Presets]` link: Restores dropdown select mode.
- **Stream Mode Toggle Button (`Stream: ON / OFF`)**:
  - Switches between real-time token streaming (`Server-Sent Events`) and single-batch generation.
  - Features pulsing indicator dot when enabled.
- **System Prompt Toggle Button (`⚙️ System Prompt`)**:
  - Expands/collapses the configuration drawer.
- **Clear Chat Button (`🗑️ Clear`)**:
  - Prompts confirmation dialog and wipes current conversation history back to initial greeting.

### 3.3 System Prompt & Temperature Drawer (Collapsible)
- **Temperature Slider (`0.1` to `1.5`, step `0.1`)**:
  - Controls LLM creativity/determinism in real time.
- **System Instructions Textarea**:
  - Customizes MOMO's persona, boundaries, and contextual instructions.

### 3.4 Conversation Feed & Message Bubbles
- **User Messages**:
  - Right-aligned indigo gradient bubbles with timestamp and user avatar `👤`.
- **MOMO Assistant Messages**:
  - Left-aligned dark slate bubbles with robot avatar `🤖` and model tag.
  - **Reasoning / Thought Process Accordion (`💭 Thought Process`)**:
    - Specially designed for reasoning models (e.g. `qwen3`, `deepseek-r1`).
    - Displays word count and collapsible markdown view for chain-of-thought tokens.
  - **Streaming Cursor (`typing-cursor`)**:
    - Animated indicator displaying active generation.
  - **Formatted Code Blocks**:
    - Syntax header with language name (e.g. `PYTHON`, `JAVASCRIPT`, `HTML`).
    - Dedicated `[Copy code]` button per code block with `✓ Copied` feedback state.
  - **Inline Message Copy (`📋`)**:
    - Copies full markdown content to clipboard with momentary checkmark confirmation.
  - **Error Recovery Bubbles**:
    - Styled in red tint with terminal hint instructions (e.g., `ollama run qwen3:4b`).

### 3.5 Starter Suggestions & Quick Prompts
Displayed when starting a fresh session:
- `🚀 Tell me about yourself and your capabilities.`
- `🐍 Write a Python function to check palindrome strings.`
- `⚡ Explain how Django and React communicate via REST APIs.`
- `💡 Give me 3 creative project ideas using local LLMs.`

### 3.6 Chat Input Dock
- **Auto-expanding Textarea**:
  - Supports multiline input (`Shift + Enter`).
  - Supports direct submission (`Enter`).
  - Dynamically resizes up to `140px` max height.
- **Action Button (Dynamic)**:
  - **`[Send ➔]`**: Gradient indigo submit button (disabled when input is empty or generating).
  - **`[■ Stop]`**: High-visibility rose button rendered during generation to abort active stream via `AbortController`.

---

## 4. Tab 2: System Health & API Console

### 4.1 Fullstack Topology Card
Visual schematic showing ports, services, and connectivity:
- **React 19 Frontend Client** (`localhost:5173`)
- **Django 6.1 REST / ASGI Gateway** (`localhost:8000`)
- **Ollama Local LLM Daemon** (`localhost:11434`)

### 4.2 Ollama Models Manager
- **Refresh Button (`Refresh`)**: Refetches `/api/ollama/status/`.
- **Version & Model Count**: Shows current daemon release and total models.
- **Interactive Model Cards**:
  - Displays model name and disk size (e.g. `4.2 GB`).
  - Clicking any card selects that model and immediately switches back to Tab 1.
- **Offline Warning Banner**: Provides `ollama serve` CLI command when daemon is unreachable.

### 4.3 Live REST API Payload Tester
- **Input Field**: Direct message payload input for `/api/message/`.
- **Send Button (`Send`)**: Dispatches asynchronous JSON POST request.
- **Quick Preset Buttons**:
  - `[Hello Django! 🚀]`
  - `[Ping from React ⚛️]`
  - `[Ollama + Qwen check 🧠]`

### 4.4 REST Response Activity Log
- **Clear Log Button (`Clear log`)**: Resets activity history.
- **Log Feed**: Chronological list of sent payloads, timestamps, status indicators, and Django responses (`↳ Django received your message...`).

---

## 5. Drawers, Modals & Settings Panels

### 5.1 Privacy & Hardware Shutter Controls (Modal / Panel)
- **Camera Shutter Toggle**: Hardware/Software vision disable switch.
- **Microphone Switch**: Audio capture stream toggle.
- **Activity & Context Tracking**: Toggle screen session tracker.
- **Memory Purge Button (`🗑️ Wipe Memory`)**: Calls `/api/memory/wipe/` to clear SQLite facts and preferences.

### 5.2 ESP32 Physical Companion Monitor
- **Connection Status Badge**: `Connected` / `Disconnected`.
- **Battery Gauge**: Real-time percentage indicator (`battery_pct`).
- **Signal Quality**: WiFi RSSI dBm bar.
- **Hardware Command Tester**: Manual actuation buttons (`Nod`, `Tilt Left`, `Tilt Right`, `Celebrate`, `Blink`).

---

## 6. Complete Button & Function Directory

| # | Button / UI Control | Location / Tab | Associated Function | Action / Effect |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Ollama Status Pill** | Top Header | `checkOllamaHealth()` | Pings `/api/ollama/status/`, checks daemon health, fetches model list. |
| **2** | **Django Status Pill** | Top Header | `checkBackendHealth()` | Pings `/api/status/`, calculates latency in ms. |
| **3** | **`[🤖 Chatbot]` Tab** | Top Header | `setActiveTab('chat')` | Switches view to primary conversational companion interface. |
| **4** | **`[⚡ API Console]` Tab** | Top Header | `setActiveTab('health')` | Switches view to diagnostics and REST payload test console. |
| **5** | **Model Selector Dropdown** | Chat Toolbar | `setSelectedModel(val)` | Selects installed model (`qwen3:4b`, etc.) or triggers custom input. |
| **6** | **`[Presets]` Link** | Chat Toolbar | `setIsCustomModel(false)` | Exits custom model input mode back to dropdown select. |
| **7** | **`[Stream: ON/OFF]` Toggle** | Chat Toolbar | `setStreamMode(!streamMode)` | Toggles SSE token-by-token streaming vs single batch response. |
| **8** | **`[⚙️ System Prompt]`** | Chat Toolbar | `setShowSettings(!showSettings)` | Expands/collapses system instruction and temperature drawer. |
| **9** | **`[🗑️ Clear]` Chat** | Chat Toolbar | `handleClearChat()` | Displays confirmation and wipes chat messages to initial state. |
| **10** | **Temperature Slider** | Settings Drawer | `setTemperature(val)` | Dynamically updates LLM inference temperature (`0.1 - 1.5`). |
| **11** | **System Prompt Textarea** | Settings Drawer | `setSystemPrompt(val)` | Updates system instructions sent with chat payloads. |
| **12** | **Starter Prompt Pills (x4)**| Chat Welcome Area | `handleSendPrompt(text)` | Injects preset question into chat input and focuses textarea. |
| **13** | **`[Send ➔]` Button** | Chat Input Bar | `handleSendMessage(e)` | Submits message, starts SSE reader / POST call, triggers animation. |
| **14** | **`[■ Stop]` Button** | Chat Input Bar | `handleStopGenerating()` | Calls `AbortController.abort()`, halts streaming inference. |
| **15** | **`[📋]` Copy Message** | Message Bubble | `handleCopy(content, id)` | Copies message text to OS clipboard with 2s `✓ Copied` state. |
| **16** | **`[Copy code]` Button** | Code Block Header | `handleCopy(code, blockId)` | Copies isolated code snippet to OS clipboard. |
| **17** | **`[💭 Thought Process]`** | Assistant Bubble | Native HTML `<details>` | Expands/collapses deep reasoning thought process of model. |
| **18** | **`[Refresh]` Models** | API Console | `checkOllamaHealth()` | Re-scans local Ollama library for newly pulled models. |
| **19** | **Detected Model Card** | API Console | `setSelectedModel(m.name)` | Selects clicked model and immediately switches to Chatbot tab. |
| **20** | **`[Send]` API Test** | API Console | `handleSendApiTest(e)` | Dispatches POST to `/api/message/` and logs server response. |
| **21** | **API Presets (x3)** | API Console | `setApiTestInput(preset)` | Populates API test input box with sample payload. |
| **22** | **`[Clear log]` Button** | API Console | `setApiHistory([])` | Clears all entries from REST response activity log. |

---

## 7. State Variables & Hooks Architecture

```typescript
// 1. Navigation State
const [activeTab, setActiveTab] = useState<'chat' | 'health'>('chat');

// 2. Telemetry States
const [backendStatus, setBackendStatus] = useState<{
  loading: boolean;
  online: boolean;
  data: any;
  error: string | null;
  latency: number | null;
}>({ loading: true, online: false, data: null, error: null, latency: null });

const [ollamaStatus, setOllamaStatus] = useState<{
  loading: boolean;
  online: boolean;
  version: string | null;
  models: Array<{ name: string; size: number; modified_at: string }>;
  modelNames: string[];
  error: string | null;
}>({ loading: true, online: false, version: null, models: [], modelNames: [], error: null });

// 3. Conversation & Generation State
const [selectedModel, setSelectedModel] = useState<string>('qwen3:4b');
const [customModelInput, setCustomModelInput] = useState<string>('');
const [isCustomModel, setIsCustomModel] = useState<boolean>(false);
const [systemPrompt, setSystemPrompt] = useState<string>('You are MOMO AI, a helpful...');
const [showSettings, setShowSettings] = useState<boolean>(false);
const [streamMode, setStreamMode] = useState<boolean>(true);
const [temperature, setTemperature] = useState<number>(0.7);

const [messages, setMessages] = useState<Array<{
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string;
  model?: string;
  timestamp: string;
  isStreaming?: boolean;
  error?: boolean;
}>>([]);

const [inputMessage, setInputMessage] = useState<string>('');
const [isGenerating, setIsGenerating] = useState<boolean>(false);
const [copiedId, setCopiedId] = useState<string | null>(null);

// 4. API Tester State
const [apiTestInput, setApiTestInput] = useState<string>('');
const [isSendingApiTest, setIsSendingApiTest] = useState<boolean>(false);
const [apiHistory, setApiHistory] = useState<Array<{
  id: number;
  type: 'success' | 'error';
  time: string;
  sent: string;
  received: string;
}>>([]);

// 5. References
const abortControllerRef = useRef<AbortController | null>(null);
const chatBottomRef = useRef<HTMLDivElement | null>(null);
const textareaRef = useRef<HTMLTextAreaElement | null>(null);
```

---

## 8. Facial Expression & Animation Synchronizer

MOMO synchronizes emotional states across the digital UI and physical ESP32 OLED:

| Expression Key | Digital Face | OLED Hardware Face | Servo Action | Emotion Trigger |
| :--- | :---: | :---: | :---: | :--- |
| `normal` | `◕ᴗ◕` | `( ● ᴗ ● )` | `hold` | Idle, awaiting input |
| `happy` | `^ᴗ^` | `( ^ ᴗ ^ )` | `nod` | Greeting, positive answer |
| `thinking` | `•ᴗ•` | `( • ᴗ • )` | `hold` (LED Pulse) | Token generation in progress |
| `confused` | `•_•?` | `( • _ • ? )` | `tilt_left` | Parser error, LLM offline |
| `sleepy` | `-ᴗ-` | `( - ᴗ - )` | `tilt_right` | Inactivity timer triggered |
| `excited` | `★ᴗ★` | `( ★ ᴗ ★ )` | `celebrate` | Task completed, celebration |

---

## 9. API & WebSocket Event Contracts

### 9.1 REST Endpoints
- **`GET /api/status/`**: Backend health check and roundtrip latency measurement.
- **`GET /api/ollama/status/`**: Discovers local Ollama models and server version.
- **`POST /api/message/`**: Two-way diagnostic JSON message test.
- **`POST /api/chat/`**: Primary conversational endpoint (supports `stream: true` via SSE).

### 9.2 WebSocket Events (`/ws/momo/`)
- **Client to Server**:
  - `{"type": "chat_message", "message": "...", "model": "qwen3:4b", "is_mock": false}`
  - `{"type": "context_update", "active_app": "VS Code", "idle_seconds": 12}`
  - `{"type": "ping"}`
- **Server to Client**:
  - `{"type": "momo_thinking", "is_thinking": true}`
  - `{"type": "momo_response", "message": "...", "expression": "happy", "animation": "nod", "ascii": "^ᴗ^"}`
  - `{"type": "pong"}`

---

## 10. Keyboard Shortcuts & Hotkeys

| Shortcut | Context | Action |
| :--- | :--- | :--- |
| `Enter` | Chat Input Textarea | Submit message immediately |
| `Shift + Enter` | Chat Input Textarea | Insert line break without submitting |
| `Escape` | During Generation | Abort active streaming generation |
| `Ctrl + K` / `Cmd + K` | Global | Clear conversation history |
| `Tab` | Navigation | Cycle through interactive buttons and inputs |

---
*Created as part of the MOMO Local AI Companion Platform specifications.*

# 🛡️ MOMO Privacy & Local-First Security Specification

## 1. Privacy Principles

1. **No Unsolicited Sensor Activation**:
   - Camera is default `OFF`.
   - Microphone is default `OFF`.
   - Vision frames and audio bytes are processed strictly in RAM and never saved to persistent disk or uploaded to cloud endpoints.
2. **No Keystroke Logging**: Desktop activity tracking monitors aggregate session duration and idle minutes only. Keystrokes and sensitive window contents are never recorded.
3. **Data Deletion Rights**: The user can wipe all long-term memories with one click via `DELETE /api/memory/` or the UI Privacy panel.
4. **Deterministic Sandboxing**: All hardware commands sent to the ESP32 must match strict allowlists. Arbitrary commands from the LLM are discarded.

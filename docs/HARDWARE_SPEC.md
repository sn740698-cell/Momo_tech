# 🔌 MOMO — Hardware & ESP32 Specification

## 1. Hardware Overview

The physical MOMO robot is an ESP32-powered desktop companion designed to mirror the digital character's emotions and provide tactile physical feedback.

### Components & Bill of Materials (BOM)
- **Microcontroller**: ESP32 DevKit V1 (Wi-Fi + BLE)
- **Display**: 0.96" or 1.3" I2C OLED (SSD1306 / SH1106, 128x64 pixels)
- **Actuators**: 2x SG90 Micro Servos (Pan / Tilt motion for nodding and head tilts)
- **Status Indicators**: RGB LED or NeoPixel ring (Status / Activity indication)
- **Input**: 2x Tactile Pushbuttons (Action trigger / Mute)
- **Audio Output**: Optional I2S MAX98357A DAC + 3W Speaker

---

## 2. Wiring & Pinout Guide

| ESP32 Pin | Connected Component | Function |
| :--- | :--- | :--- |
| **GPIO 21** | OLED Display | I2C SDA (Data Line) |
| **GPIO 22** | OLED Display | I2C SCL (Clock Line) |
| **GPIO 18** | Servo 1 (Pan / Nod) | PWM Control Signal |
| **GPIO 19** | Servo 2 (Tilt) | PWM Control Signal |
| **GPIO 4**  | Tactile Pushbutton 1 | Action Event Trigger (Internal Pull-Up) |
| **GPIO 5**  | Status RGB LED | PWM / WS2812 Data |
| **3V3 / 5V**| Power Rails | Regulated Power Supply |
| **GND**     | Common Ground | Shared System Ground |

---

## 3. Communication & Firmware Architecture

The ESP32 communicates with the Django backend over a lightweight, persistent WebSocket connection (`ws://<HOST_IP>:8000/ws/momo/`).

### Inbound Commands (Backend $\rightarrow$ ESP32)
```json
{
  "type": "device_command",
  "device_id": "momo-01",
  "expression": "happy",
  "animation": "nod",
  "led": "blink"
}
```

#### Hardware Response Mappings:
1. **`expression` $\rightarrow$ OLED Screen**:
   - `normal`: Draws default wide eyes `( ● ᴗ ● )`
   - `happy`: Draws arc eyes `( ^ ᴗ ^ )`
   - `thinking`: Draws rolling/curious eyes `( • ᴗ • )`
   - `confused`: Draws asymmetric question mark face `( • _ • ? )`
   - `sleepy`: Draws horizontal slit eyes `( - ᴗ - )`
   - `excited`: Draws star eyes `( ★ ᴗ ★ )`

2. **`animation` $\rightarrow$ SG90 Servos**:
   - `nod`: Smooth up-and-down oscillation ($90^\circ \rightarrow 110^\circ \rightarrow 70^\circ \rightarrow 90^\circ$)
   - `tilt_left`: Head tilts $15^\circ$ left
   - `tilt_right`: Head tilts $15^\circ$ right
   - `celebrate`: Quick alternating left-right wobble

3. **`led` $\rightarrow$ Status LED**:
   - `solid`: Normal operational state
   - `pulsing`: Thinking / Local LLM generation in progress
   - `blink`: Event notification or prompt completion

### Outbound Events (ESP32 $\rightarrow$ Backend)
```json
{
  "type": "button_event",
  "device_id": "momo-01",
  "button": "action",
  "event": "pressed",
  "timestamp": 1724412000
}
```
```json
{
  "type": "heartbeat",
  "device_id": "momo-01",
  "battery_pct": 94,
  "rssi": -58
}
```

---

## 4. Hardware Safety Rules
1. **No Arbitrary Code**: The ESP32 firmware executes only mapped routines based on strictly validated enum keys.
2. **Servo Bounds Enforcement**: Hard software limits prevent servos from hitting mechanical stops.
3. **Graceful Disconnection**: If the ESP32 disconnects, the Desktop MOMO companion continues operating seamlessly without crashing.

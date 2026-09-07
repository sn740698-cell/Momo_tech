# 🤖 MOMO Physical ESP32 Companion — Complete Wiring & Assembly Guide

This document provides the exact pinout, circuit schematic, breadboard wiring layout, and power decoupling instructions matching your hardware inventory.

---

## 1. Hardware Inventory & Role Overview

| Component | Quantity | Role in MOMO |
| :--- | :---: | :--- |
| **ESP32 DevKit V1 (30-pin)** | 1 | Microcontroller brain for the physical companion body |
| **0.96" OLED SSD1306 (I²C 128x64)** | 1 | Digital facial expressions (Happy, Thinking, Excited, Sleepy, etc.) |
| **SG90 Micro Servo** | 1 | Physical head movement (Nodding, Shaking, Tilting) |
| **MAX98357A I²S Amplifier** | 1 | Digital-to-Analog audio DAC & 3W Class D speaker driver |
| **4Ω 3W Speaker** | 1 | Physical voice output (speech & companion sound effects) |
| **Push Buttons** | 3 | Physical triggers: **BTN 1** (Talk/Wake), **BTN 2** (Mood Cycle), **BTN 3** (Mute/Sleep) |
| **1000µF Electrolytic Capacitor** | 1 | Essential 5V rail buffer — prevents ESP32 brownout resets during servo moves & audio peaks |
| **ESP32 Onboard Blue LED** | Built-in | System heartbeat & thinking/speaking activity pulse (no extra wiring) |
| **Breadboard & Jumper Wires** | 1 set | Solderless rapid prototyping & power bus distribution |
| **Power ON/OFF Switch** | 1 | Inline master power control |
| **USB-C ↔ USB-C Data Cable** | 1 | High-speed data link (115200 baud) & 5V power from laptop |

---

## 2. Complete Pinout & Wiring Table

> [!IMPORTANT]
> **Power Decoupling**: Connect the **1000µF capacitor** directly across the breadboard's `+5V (VIN)` and `GND` power rails.
> - **Negative leg (marked with minus stripe `-`)** ➔ **GND rail**
> - **Positive leg (longer lead)** ➔ **5V (VIN) rail**
> This absorbs inductive current spikes from the SG90 servo motor and MAX98357A amplifier, preventing ESP32 crash/reboots!

### A. 0.96" OLED SSD1306 (I²C 128x64)
| OLED Pin | ESP32 Pin | Breadboard Rail | Note |
| :--- | :--- | :--- | :--- |
| **GND** | GND | GND Rail | Common Ground |
| **VCC** | 3V3 or VIN (5V) | 3.3V or 5V Rail | Most SSD1306 boards accept 3.3V–5V |
| **SCL** | **GPIO 22** | Row 22 | Hardware I2C Clock |
| **SDA** | **GPIO 21** | Row 21 | Hardware I2C Data |

---

### B. 1x SG90 Micro Servo (Head Movement)
| Servo Wire Color | Function | Connect To |
| :--- | :--- | :--- |
| **Brown / Black** | Ground | **GND Rail** |
| **Red** | Power (+5V) | **5V (VIN) Rail** *(Never power from 3.3V!)* |
| **Orange / Yellow** | PWM Signal | **GPIO 18** |

---

### C. MAX98357A I²S Amplifier & 4Ω 3W Speaker
| MAX98357A Pin | Connect To | Description |
| :--- | :--- | :--- |
| **VIN** | **5V (VIN) Rail** | Needs 5V for clean 3.2W output |
| **GND** | **GND Rail** | Common Ground |
| **BCLK** | **GPIO 26** | I2S Bit Clock |
| **LRC (WS)** | **GPIO 25** | I2S Left/Right Clock (Word Select) |
| **DIN** | **GPIO 27** | I2S Serial Audio Data |
| **GAIN** | *Unconnected* (or GND) | Default 9dB gain (clean for 4Ω 3W speaker) |
| **SD_MODE** | *Unconnected* | Default Mono (L + R) / 2 mix |
| **Speaker (+) Screw**| Speaker Red Wire | Connect to 4Ω 3W Speaker |
| **Speaker (-) Screw**| Speaker Black Wire | Connect to 4Ω 3W Speaker |

---

### D. Onboard Status & Heartbeat LED (Built Into ESP32)
* **No external wiring or resistors required!**
* Uses the built-in Blue LED on **GPIO 2** of the ESP32 DevKit V1.
* **Behaviors**:
  - Gentle heartbeat pulse during normal standby.
  - Rapid pulsing while MOMO is thinking / synthesizing speech.
  - Fast strobe when excited / celebrating.
  - Flash on button press.
  - Completely turned off during sleep / mute mode.

---

### E. 3x Push Buttons (Active LOW with internal pull-up)
*All buttons connect one leg to an ESP32 GPIO, and the other leg to the **GND Rail**.*

| Button | ESP32 Pin | Function |
| :--- | :--- | :--- |
| **Button 1 (Left)** | **GPIO 13** ➔ GND | **Talk / Wake Trigger**: Starts voice prompt / chat |
| **Button 2 (Center)**| **GPIO 14** ➔ GND | **Cycle Mood**: Cycles faces (Happy ➔ Thinking ➔ Excited ➔ Normal) |
| **Button 3 (Right)** | **GPIO 15** ➔ GND | **Mute / Sleep**: Toggles sound & puts MOMO to sleep |

---

## 3. Visual Breadboard Schematic

```text
               +------------------------------------------------------+
               |               BREADBOARD POWER RAILS                 |
               |  (+) 5V (VIN)  ====================================  |
               |  (-) GND       ====================================  |
               |                   [ 1000µF Capacitor ]               |
               |                    (+) to 5V, (-) to GND             |
               +------------------------------------------------------+
                                          |
          +-------------------------------+-------------------------------+
          |                                                               |
     +---------+                                                     +---------+
     |  OLED   |                                                     |  SERVO  |
     | SSD1306 |                                                     |  SG90   |
     +---------+                                                     +---------+
      VCC -> 5V                                                       VCC -> 5V
      GND -> GND                                                      GND -> GND
      SCL -> GPIO 22                                                  SIG -> GPIO 18
      SDA -> GPIO 21                                                 
                                                                     +---------+
     +----------+                                                    | BUTTONS |
     | MAX98357A|                                                    +---------+
     | I2S AMP  |                                                     BTN1 -> GPIO 13 to GND
     +----------+                                                     BTN2 -> GPIO 14 to GND
      VIN -> 5V                                                       BTN3 -> GPIO 15 to GND
      GND -> GND                                                     
      BCLK-> GPIO 26                                                 +-------------------+
      LRC -> GPIO 25                                                 | ESP32 ONBOARD LED |
      DIN -> GPIO 27                                                 | (GPIO 2, Built-in)|
        |    |                                                       +-------------------+
     [ 4Ω 3W Speaker ]
```

---

## 4. Step-by-Step Assembly Checklist

1. **Place the ESP32**:
   - Straddle the ESP32 DevKit V1 across the center trough of the breadboard so each pin has its own breadboard row.
2. **Setup Power Rails**:
   - Run a jumper from ESP32 `VIN` to the red `(+)` power rail.
   - Run a jumper from ESP32 `GND` to the blue `(-)` power rail.
   - Insert the **1000µF capacitor** into the power rails: stripe on side is **Negative (`-`) ➔ GND rail**, other lead is **Positive (`+`) ➔ 5V rail**.
3. **Wire the OLED Display**:
   - Connect VCC to 5V, GND to GND.
   - Connect SCL to **GPIO 22**, SDA to **GPIO 21**.
4. **Wire the SG90 Servo**:
   - Connect Brown/Black to GND rail, Red to 5V rail.
   - Connect Orange/Yellow to **GPIO 18**.
5. **Wire the MAX98357A Amplifier & Speaker**:
   - Connect VIN to 5V rail, GND to GND rail.
   - Connect BCLK to **GPIO 26**, LRC to **GPIO 25**, DIN to **GPIO 27**.
   - Screw speaker wires into the terminal block (polarity does not matter for single mono speaker).
6. **Wire the 3 Buttons**:
   - Place 3 push buttons across the breadboard.
   - Wire one side of each button to the **GND rail**.
   - Wire the other side of Button 1 to **GPIO 13**, Button 2 to **GPIO 14**, Button 3 to **GPIO 15**.

---

## 5. Flashing the Firmware

### Option A: Using PlatformIO (Recommended)
1. Open terminal in the `hardware/esp32/` directory:
   ```bash
   cd hardware/esp32
   pio run --target upload
   ```
2. Open the serial monitor:
   ```bash
   pio device monitor -b 115200
   ```

### Option B: Using Arduino IDE
1. Select board: **ESP32 Dev Module**.
2. Install libraries via Library Manager:
   - `U8g2` by oliver
   - `ArduinoJson` (v7) by Benoît Blanchon
   - `ESP32Servo` by Kevin Harrington
   - `WebSockets` by Markus Sattler
3. Open `hardware/esp32/src/main.cpp` (with `include/` headers).
4. Select your USB COM port and click **Upload**.

---

## 6. Testing & Running MOMO

Once wired and flashed:
1. Plug the ESP32 into your laptop using the **USB-C cable**.
2. Double-click `start_momo.bat` on your desktop.
3. The companion will:
   - **Chirp happily** on the 4Ω 3W speaker via the MAX98357A DAC.
   - Display MOMO's smiling face on the 0.96" SSD1306 OLED screen.
   - Pulse the onboard blue status LED.
   - Center the head servo at 90°.
   - Sync instantly with the React dashboard over the USB-C serial bridge!

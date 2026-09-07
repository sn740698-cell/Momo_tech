#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <U8g2lib.h>
#include <driver/i2s.h>

#include "pins.h"
#include "faces.h"
#include "config.h"

// ====================================================================
// MOMO Physical Companion Firmware
// Hardware Inventory:
// - ESP32 DevKit V1
// - 0.96" OLED SSD1306 (128x64 I2C)
// - 1x SG90 Micro Servo (Head Pan / Nod)
// - MAX98357A I2S Amplifier + 4Ω 3W Speaker
// - 3x Push Buttons (Talk, Mood Cycle, Mute/Sleep)
// - Onboard Status LED (GPIO 2, built into ESP32)
// - 1000µF Capacitor for 5V power rail smoothing
// ====================================================================

// Hardware Instances
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, OLED_SCL_PIN, OLED_SDA_PIN);
Servo headServo;
WebSocketsClient webSocket;

// State Tracking
String currentExpression = "normal";
String currentAnimation = "none";
String currentLedMode = "solid";
bool isMuted = false;
unsigned long lastHeartbeat = 0;
unsigned long lastAnimationUpdate = 0;
int animStep = 0;

// Button Debounce States
bool lastBtnTalkState = HIGH;
bool lastBtnMoodState = HIGH;
bool lastBtnMuteState = HIGH;

// Forward Declarations
void processCommand(JsonObject &doc);
void executeAnimation(const String &anim);
void updateOnboardLED();
void setupI2SAudio();
void playChirpTone(int frequency, int durationMs);
void sendHeartbeat();
void sendButtonEvent(const String &btnName, const String &extraKey = "", const String &extraVal = "");

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected from MOMO Brain Gateway.");
            break;
        case WStype_CONNECTED:
            Serial.printf("[WS] Connected to MOMO Brain Gateway: %s\n", payload);
            sendHeartbeat();
            break;
        case WStype_TEXT: {
            JsonDocument doc;
            DeserializationError error = deserializeJson(doc, payload, length);
            if (!error) {
                JsonObject obj = doc.as<JsonObject>();
                processCommand(obj);
            }
            break;
        }
        default:
            break;
    }
}

void setup() {
    Serial.begin(USB_SERIAL_BAUD);
    delay(100);
    Serial.println("\n==================================================");
    Serial.println("   MOMO PHYSICAL COMPANION (ESP32 DevKit V1)");
    Serial.println("==================================================");

    // 1. Built-in Heartbeat LED (GPIO 2)
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, HIGH);

    // 2. Setup 3x Interactive Pushbuttons (Active LOW with internal pull-up)
    pinMode(BTN_TALK_PIN, INPUT_PULLUP);
    pinMode(BTN_MOOD_PIN, INPUT_PULLUP);
    pinMode(BTN_MUTE_PIN, INPUT_PULLUP);

    // 3. Setup 1x SG90 Micro Servo
    ESP32PWM::allocateTimer(0);
    headServo.setPeriodHertz(50);
    headServo.attach(SERVO_PIN, 500, 2400);
    headServo.write(90); // Center position (90 degrees)

    // 4. Setup 0.96" OLED Display (SSD1306)
    u8g2.begin();
    renderExpression(u8g2, "happy");

    // 5. Setup MAX98357A I2S Audio Amp & Speaker
    setupI2SAudio();
    playChirpTone(880, 120); // Quick boot melody (A5)
    delay(80);
    playChirpTone(1320, 160); // (E6)

    // 6. Connect WiFi if configured, otherwise run over USB-C Serial
    if (String(WIFI_SSID) != "YOUR_WIFI_SSID") {
        Serial.printf("[WIFI] Connecting to %s...\n", WIFI_SSID);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        int retries = 0;
        while (WiFi.status() != WL_CONNECTED && retries < 12) {
            delay(400);
            Serial.print(".");
            retries++;
        }
        if (WiFi.status() == WL_CONNECTED) {
            Serial.printf("\n[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
            webSocket.begin(MOMO_GATEWAY_HOST, MOMO_GATEWAY_PORT, MOMO_WS_PATH);
            webSocket.onEvent(webSocketEvent);
            webSocket.setReconnectInterval(5000);
        } else {
            Serial.println("\n[WIFI] Running in direct USB-C Serial Mode.");
        }
    } else {
        Serial.println("[WIFI] Running in direct USB-C Serial Mode.");
    }

    renderExpression(u8g2, "normal");
    Serial.println("[MOMO-ESP32] System fully armed. Ready for USB-C & Button interactions!");
}

void loop() {
    // 1. Maintain WebSocket loop if WiFi is online
    if (WiFi.status() == WL_CONNECTED) {
        webSocket.loop();
    }

    // 2. Read inbound JSON commands from direct USB-C Serial
    if (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.startsWith("{") && line.endsWith("}")) {
            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, line);
            if (!err) {
                JsonObject obj = doc.as<JsonObject>();
                processCommand(obj);
            }
        }
    }

    // 3. Scan & Debounce 3x Pushbuttons
    int readingTalk = digitalRead(BTN_TALK_PIN);
    int readingMood = digitalRead(BTN_MOOD_PIN);
    int readingMute = digitalRead(BTN_MUTE_PIN);

    // Button 1: TALK / ACTION
    if (readingTalk == LOW && lastBtnTalkState == HIGH) {
        delay(40);
        if (digitalRead(BTN_TALK_PIN) == LOW) {
            Serial.println("[BTN] Talk / Wake triggered!");
            digitalWrite(STATUS_LED_PIN, LOW); // Flash LED
            playChirpTone(1046, 100);          // C6 tone
            digitalWrite(STATUS_LED_PIN, HIGH);
            sendButtonEvent("talk");
        }
    }
    lastBtnTalkState = readingTalk;

    // Button 2: CYCLE MOOD / EXPRESSION
    if (readingMood == LOW && lastBtnMoodState == HIGH) {
        delay(40);
        if (digitalRead(BTN_MOOD_PIN) == LOW) {
            // Cycle: normal -> happy -> thinking -> excited -> confused -> sad -> sleepy
            if (currentExpression == "normal") currentExpression = "happy";
            else if (currentExpression == "happy") currentExpression = "thinking";
            else if (currentExpression == "thinking") currentExpression = "excited";
            else if (currentExpression == "excited") currentExpression = "confused";
            else if (currentExpression == "confused") currentExpression = "sad";
            else if (currentExpression == "sad") currentExpression = "sleepy";
            else currentExpression = "normal";

            Serial.printf("[BTN] Cycled mood to: %s\n", currentExpression.c_str());
            renderExpression(u8g2, currentExpression);
            playChirpTone(1318, 80); // E6 chirp
            sendButtonEvent("mood", "expression", currentExpression);
        }
    }
    lastBtnMoodState = readingMood;

    // Button 3: MUTE / SLEEP
    if (readingMute == LOW && lastBtnMuteState == HIGH) {
        delay(40);
        if (digitalRead(BTN_MUTE_PIN) == LOW) {
            isMuted = !isMuted;
            if (isMuted) {
                currentExpression = "sleepy";
                renderExpression(u8g2, "sleepy");
                digitalWrite(STATUS_LED_PIN, LOW);
                headServo.write(60); // Resting head tilt
                Serial.println("[BTN] MOMO muted / entered sleep.");
            } else {
                currentExpression = "normal";
                renderExpression(u8g2, "normal");
                digitalWrite(STATUS_LED_PIN, HIGH);
                headServo.write(90);
                playChirpTone(987, 100);
                Serial.println("[BTN] MOMO unmuted / awake.");
            }
            sendButtonEvent("mute", "muted", isMuted ? "true" : "false");
        }
    }
    lastBtnMuteState = readingMute;

    // 4. Periodic Heartbeat (every 5 seconds)
    if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
        lastHeartbeat = millis();
        sendHeartbeat();
    }

    // 5. Animate Servo Movements
    executeAnimation(currentAnimation);

    // 6. Manage Onboard LED pattern
    updateOnboardLED();
}

void processCommand(JsonObject &doc) {
    String type = doc["type"] | "";
    if (type == "device_command" || doc.containsKey("expression")) {
        String expr = doc["expression"] | "normal";
        String anim = doc["animation"] | "none";
        String led = doc["led"] | "solid";

        if (expr != currentExpression) {
            currentExpression = expr;
            renderExpression(u8g2, currentExpression);
        }

        currentAnimation = anim;
        animStep = 0;
        currentLedMode = led;

        // Direct target servo angle if commanded
        if (doc.containsKey("servo")) {
            JsonObject servo = doc["servo"];
            int angle = servo["pan"] | servo["angle"] | 90;
            headServo.write(constrain(angle, 35, 145));
        }

        Serial.printf("[MOMO-ESP32] Executed: expr=%s, anim=%s, led=%s\n",
                      currentExpression.c_str(), currentAnimation.c_str(), currentLedMode.c_str());
    }
}

void executeAnimation(const String &anim) {
    if (anim == "none") return;
    if (millis() - lastAnimationUpdate < 140) return;
    lastAnimationUpdate = millis();

    // Single SG90 servo animations
    if (anim == "nod") {
        if (animStep == 0) headServo.write(115);
        else if (animStep == 1) headServo.write(65);
        else if (animStep == 2) headServo.write(115);
        else { headServo.write(90); currentAnimation = "none"; }
        animStep++;
    } else if (anim == "tilt_left") {
        headServo.write(65);
        currentAnimation = "none";
    } else if (anim == "tilt_right") {
        headServo.write(115);
        currentAnimation = "none";
    } else if (anim == "celebrate" || anim == "wave") {
        if (animStep % 2 == 0) headServo.write(70);
        else headServo.write(110);
        animStep++;
        if (animStep > 6) {
            headServo.write(90);
            currentAnimation = "none";
        }
    } else if (anim == "sleep") {
        headServo.write(60);
        currentAnimation = "none";
    }
}

void updateOnboardLED() {
    if (isMuted) {
        digitalWrite(STATUS_LED_PIN, LOW);
        return;
    }

    if (currentExpression == "thinking") {
        // Pulse fast while thinking
        digitalWrite(STATUS_LED_PIN, (millis() / 150) % 2 == 0 ? HIGH : LOW);
    } else if (currentExpression == "excited") {
        // Strobe while excited
        digitalWrite(STATUS_LED_PIN, (millis() / 80) % 2 == 0 ? HIGH : LOW);
    } else if (currentLedMode == "blink") {
        digitalWrite(STATUS_LED_PIN, (millis() / 250) % 2 == 0 ? HIGH : LOW);
    } else {
        // Standard gentle heartbeat
        digitalWrite(STATUS_LED_PIN, (millis() / 800) % 2 == 0 ? HIGH : LOW);
    }
}

void setupI2SAudio() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 22050,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = true
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCLK_PIN,
        .ws_io_num = I2S_LRC_PIN,
        .data_out_num = I2S_DIN_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
    i2s_set_clk(I2S_NUM_0, 22050, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_STEREO);
}

void playChirpTone(int frequency, int durationMs) {
    if (isMuted) return;
    int samples = (22050 * durationMs) / 1000;
    int16_t buffer[256];
    size_t bytes_written;

    for (int i = 0; i < samples; i += 128) {
        int chunkSize = min(128, samples - i);
        for (int j = 0; j < chunkSize; j++) {
            float t = (float)(i + j) / 22050.0;
            int16_t val = (int16_t)(sin(2.0 * PI * frequency * t) * 6000.0);
            buffer[j * 2] = val;     // Left channel
            buffer[j * 2 + 1] = val; // Right channel
        }
        i2s_write(I2S_NUM_0, buffer, chunkSize * 4, &bytes_written, portMAX_DELAY);
    }
}

void sendHeartbeat() {
    JsonDocument hb;
    hb["type"] = "heartbeat";
    hb["device_id"] = MOMO_DEVICE_ID;
    hb["rssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
    hb["battery_pct"] = 100;
    hb["connection"] = WiFi.status() == WL_CONNECTED ? "wifi" : "usb_serial";
    hb["expression"] = currentExpression;
    hb["muted"] = isMuted;

    String payload;
    serializeJson(hb, payload);
    Serial.println(payload);
    if (WiFi.status() == WL_CONNECTED && webSocket.isConnected()) {
        webSocket.sendTXT(payload);
    }
}

void sendButtonEvent(const String &btnName, const String &extraKey, const String &extraVal) {
    JsonDocument doc;
    doc["type"] = "button_event";
    doc["device_id"] = MOMO_DEVICE_ID;
    doc["button"] = btnName;
    doc["timestamp"] = millis();
    if (extraKey.length() > 0) {
        doc[extraKey] = extraVal;
    }

    String payload;
    serializeJson(doc, payload);
    Serial.println(payload); // Sent over USB-C Serial to Django Bridge
    if (WiFi.status() == WL_CONNECTED && webSocket.isConnected()) {
        webSocket.sendTXT(payload); // Sent over WebSocket
    }
}

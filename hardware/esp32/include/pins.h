#ifndef PINS_H
#define PINS_H

// ====================================================================
// ESP32 DevKit V1 GPIO Pinout for MOMO Physical Companion
// Matches user's exact hardware inventory (No external RGB LEDs):
// - ESP32 DevKit V1 (30-pin)
// - 0.96" OLED SSD1306 I2C (128x64)
// - 1x SG90 Micro Servo (Head Pan / Nod)
// - MAX98357A I2S Audio Amplifier + 4Ω 3W Speaker
// - 3x Push Buttons (Talk, Mood Cycle, Mute/Sleep)
// - Built-in Onboard Blue LED (GPIO 2)
// - 1000µF Capacitor across 5V/GND rail
// ====================================================================

// 1. OLED Display (SSD1306 128x64 I2C)
#define OLED_SDA_PIN        21      // Hardware I2C Data
#define OLED_SCL_PIN        22      // Hardware I2C Clock
#define OLED_ADDR           0x3C    // Default I2C Address (0x3C or 0x3D)

// 2. 1x SG90 Micro Servo (Head Movement / Nod / Pan)
#define SERVO_PIN           18      // PWM control signal (Orange/Yellow wire)

// 3. MAX98357A I2S Audio Amplifier (for 4Ω 3W Speaker)
#define I2S_BCLK_PIN        26      // Bit Clock (BCLK)
#define I2S_LRC_PIN         25      // Word Select / Left-Right Clock (LRC / WS)
#define I2S_DIN_PIN         27      // Serial Data In (DIN)

// 4. 3x Physical Interactive Push Buttons (Active LOW with internal pull-up)
#define BTN_TALK_PIN        13      // Button 1: Wake / Talk / Send Input
#define BTN_MOOD_PIN        14      // Button 2: Cycle Expression / Mood
#define BTN_MUTE_PIN        15      // Button 3: Mute Audio / Sleep

// 5. Built-in Onboard Status Heartbeat LED (No external wiring required!)
#define STATUS_LED_PIN      2       // Onboard blue LED (GPIO 2)

// 6. USB-C Serial Communication Baud
#define USB_SERIAL_BAUD     115200

#endif // PINS_H

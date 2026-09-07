#ifndef CONFIG_H
#define CONFIG_H

// Network & Gateway Configuration for MOMO ESP32
// Note: When USB-C is connected, MOMO communicates directly over Serial
// without requiring Wi-Fi.

#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"

#define MOMO_GATEWAY_HOST   "192.168.1.100"  // Laptop IP running Django
#define MOMO_GATEWAY_PORT   8000
#define MOMO_WS_PATH        "/ws/momo/"

#define MOMO_DEVICE_ID      "momo-01"
#define HEARTBEAT_INTERVAL  5000 // Milliseconds between heartbeats

#endif // CONFIG_H

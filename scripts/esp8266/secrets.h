// secrets.h - MILA's WiFi names and passwords and her control PIN (the fleet's, 2026-10-14;
// NORA-Robot-v00/scripts/esp32/secrets.h is the reference). secrets.example.h shows the layout.
#pragma once

// The fleet network: the "RIFT" router (the hub, RIFT, is at 192.168.4.1).
#define FLEET_SSID      "RIFT"
#define FLEET_PASSWORD  "mmvbkbak"

// NORA's own fallback network, when there's no RIFT router (NORA is at 192.168.4.1 then).
#define NORA_SSID       "NORA"
#define NORA_PASSWORD   "mmvbkbak"

// MILA's own access point, when neither is around.
#define MILA_AP_SSID      "MILA"
#define MILA_AP_PASSWORD  "mmvbkbak"      // 8+ characters, or the ESP8266 won't start the AP

// The PIN a device unlocks MILA with (/unlock?pw=) before it can drive her: a catch against
// accidental driving.
#define CONTROL_PIN_SECRET "1234"

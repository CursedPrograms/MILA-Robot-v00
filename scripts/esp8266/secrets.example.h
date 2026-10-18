// secrets.example.h - copy to secrets.h (same folder) and fill in: the WiFi passwords and MILA's
// control PIN. The sketch uses secrets.h when there is one, else these placeholders.
//
//   copy secrets.example.h secrets.h        (Windows)
//   cp secrets.example.h secrets.h          (Linux)
//
// Without a secrets.h the sketch still builds, with these placeholders (and says so): she
// then can't join the RIFT network, and anyone can unlock her with "change-me".
#pragma once

// The fleet network: the "RIFT" router (the hub, RIFT, is at 192.168.4.1).
#define FLEET_SSID      "RIFT"
#define FLEET_PASSWORD  "change-me"

// NORA's own fallback network, when there's no RIFT router (NORA is at 192.168.4.1 then).
#define NORA_SSID       "NORA"
#define NORA_PASSWORD   "change-me"

// MILA's own access point, when neither is around.
#define MILA_AP_SSID      "MILA"
#define MILA_AP_PASSWORD  "change-me"     // at least 8 characters, or the ESP8266 won't start the AP

// The PIN a device unlocks MILA with (/unlock?pw=) before it can drive her.
#define CONTROL_PIN_SECRET "change-me"

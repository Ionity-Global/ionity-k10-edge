// IonityEdge · K10 — build/runtime configuration
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once

// ---- Identity ----
#define IONITY_DEVICE_PREFIX   "ionity-k10"     // + last 3 bytes of MAC at runtime
#define IONITY_PROJECT         "IonityEdge-K10"
#ifndef IONITY_FW_VERSION
#define IONITY_FW_VERSION      "0.1.0"
#endif

// ---- WiFi (SSID default; password is provisioned to NVS by the installer) ----
// Real values live ONLY in the git-ignored secrets.h (copy from secrets.example.h).
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets.example.h"
#endif
#ifndef WIFI_SSID
#define WIFI_SSID   "Antwerp Ionity"
#endif
#ifndef WIFI_PASS
#define WIFI_PASS   ""              // empty -> device waits for installer provisioning
#endif

// ---- Edge Brain endpoint (set/override via installer; stored in NVS) ----
#define EDGE_HOST_DEFAULT   "192.168.1.100"   // your PC's LAN IP running the Edge Brain
#define EDGE_PORT_DEFAULT   8765
#define EDGE_WS_PATH        "/device"

// ---- Feature flags (v1: everything on) ----
#define FEAT_SENSORS        1
#define FEAT_CAMERA         1
#define FEAT_MIC            1
#define FEAT_WAKEWORD       1
#define FEAT_SD_RECORDING   1
#define FEAT_GEOLOCATION    1
#define FEAT_SCREEN_UI      1
#define FEAT_OTA            1

// ---- Timing (ms) ----
#define TELEMETRY_PERIOD_MS   500     // 2 Hz sensor batch
#define HEARTBEAT_PERIOD_MS   5000
#define WIFI_SCAN_PERIOD_MS   30000   // geolocation BSSID scans
#define CAM_TARGET_FPS        8       // adaptive; brain can renegotiate

// ---- Media ----
#define AUDIO_SAMPLE_RATE     16000
#define AUDIO_FRAME_MS        20
#define CAM_JPEG_QUALITY      12      // 0(best)..63(worst) esp32-camera scale

// ---- Ionity theme (RGB565-friendly hex; converted in screen.cpp) ----
#define COL_BG        0x0D1B2A   // deep navy
#define COL_PRIMARY   0x00D2FF   // electric cyan
#define COL_ACCENT    0xE94560   // alert coral
#define COL_TEXT      0xFFFFFF
#define COL_MUTED     0x0F3460

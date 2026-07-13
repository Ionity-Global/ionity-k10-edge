# K10 Firmware (Arduino / C++) — ⚠ EXPERIMENTAL (v2 roadmap)

> **Not the shipping firmware.** The live on-device build is
> [`../arduino-unihiker`](../arduino-unihiker) (HTTP `/ingest`). This WebSocket thin-client is a
> scaffold for the v2 rich-media path (camera/audio/screen streaming) and is not yet functional
> end-to-end.

Thin-client firmware for the UNIHIKER K10. It renders the Ionity UI, reads sensors, and streams
camera/mic to the Edge Brain over a WebSocket. **All heavy AI runs on the Edge Brain, not here.**

## Build & flash (PlatformIO)

```bash
cd firmware/arduino
cp include/secrets.example.h include/secrets.h   # then edit with your WiFi (git-ignored)
pio run                                           # build
pio run -t upload                                 # flash over USB
pio device monitor                                # serial logs @115200
```

Or use the **Installer** (`installer/`) for one-click WebSerial flashing + WiFi provisioning —
no `secrets.h` needed, credentials go straight to the board's NVS.

## Binding the DFRobot K10 BSP

Networking (WiFi/WebSocket/JSON) uses stock libraries and is complete. Hardware calls
(`screen.cpp`, `sensors.cpp`, `media.cpp`) are wrapped with `TODO` markers — add the DFRobot
**UNIHIKER K10** board-support library (Arduino Library Manager or DFRobot GitHub) to
`platformio.ini` `lib_deps` or drop it in `lib/`, then fill in the marked calls. The app logic,
streaming, and UI flow run without it (with placeholder sensor values) so you can verify the
end-to-end pipeline first.

## Structure

```
src/
├── main.cpp            orchestrator (setup/loop, handshake, telemetry)
├── net/                wifi_manager, ws_client (+ OTA hook)
├── ui/                 screen + button grid (Ionity theme)
├── sensors/            temp/humidity/light/IMU
├── media/              camera, mic, SD recording, TTS playback
└── location/           WiFi BSSID geolocation
include/                config.h, hardware_pins.h, secrets(.example).h
```

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0

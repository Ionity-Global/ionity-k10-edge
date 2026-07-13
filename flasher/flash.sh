#!/usr/bin/env bash
# IonityEdge · K10 — one-click flasher (Linux/macOS)
# Prefers PlatformIO; falls back to esptool. © Ionity (Pty) Ltd · Policy 986 AED
set -e
# The live on-device firmware is the UNIHIKER (HTTP /ingest) build.
FW="$(dirname "$0")/../firmware/arduino-unihiker"

echo "IonityEdge · K10 flasher"
if command -v pio >/dev/null 2>&1; then
  echo "Building + flashing via PlatformIO…"
  ( cd "$FW" && pio run && pio run -t upload )
  echo "Done. Open the Installer to provision WiFi."
elif command -v esptool.py >/dev/null 2>&1; then
  BIN="$FW/.pio/build/unihiker_k10/firmware.bin"
  [ -f "$BIN" ] || { echo "No firmware.bin — run 'pio run' first"; exit 1; }
  read -rp "Serial port (e.g. /dev/ttyUSB0): " PORT
  esptool.py --chip esp32s3 --port "$PORT" --baud 921600 write_flash 0x0 "$BIN"
else
  echo "Neither PlatformIO nor esptool found."
  echo "Install PlatformIO (https://platformio.org/install) or use the browser Installer (WebSerial)."
fi

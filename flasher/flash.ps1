# IonityEdge · K10 — one-click flasher (Windows)
# Prefers PlatformIO; falls back to esptool. © Ionity (Pty) Ltd · Policy 986 AED
$ErrorActionPreference = "Stop"
# The live on-device firmware is the UNIHIKER (HTTP /ingest) build.
$fw = Join-Path $PSScriptRoot "..\firmware\arduino-unihiker"

Write-Host "IonityEdge · K10 flasher" -ForegroundColor Cyan

if (Get-Command pio -ErrorAction SilentlyContinue) {
  Write-Host "Building + flashing via PlatformIO..." -ForegroundColor Yellow
  Push-Location $fw
  pio run
  pio run -t upload
  Pop-Location
  Write-Host "Done. Open the Installer to provision WiFi." -ForegroundColor Green
}
elseif (Get-Command esptool.py -ErrorAction SilentlyContinue) {
  $bin = Join-Path $fw ".pio\build\unihiker_k10\firmware.bin"
  if (-not (Test-Path $bin)) { throw "No firmware.bin — build with PlatformIO first (pio run)." }
  $port = Read-Host "COM port (e.g. COM5)"
  esptool.py --chip esp32s3 --port $port --baud 921600 write_flash 0x0 $bin
}
else {
  Write-Host "Neither PlatformIO nor esptool found." -ForegroundColor Red
  Write-Host "Install PlatformIO: https://platformio.org/install  — or use the browser Installer (WebSerial)."
}

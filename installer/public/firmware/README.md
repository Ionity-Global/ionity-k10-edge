# Firmware images (not committed)

The browser installer flashes `ionity-k10-merged.bin` from this folder over WebSerial.
**No `.bin` is committed here** — a bundled image embeds WiFi credentials from `secrets.h`,
which must never land in a public repo (`installer/public/firmware/*.bin` is git-ignored).

## Get a creds-free image to drop in here

Build the live UNIHIKER firmware **without** a `secrets.h` present, so `WIFI_PASS`
falls back to `""` and WiFi is provisioned by the installer over serial/NVS:

```bash
cd ../../firmware/arduino-unihiker
# ensure src/secrets.h is absent (a creds-free build)
pio run
# merge bootloader + partitions + app into one image (adjust offsets to your board):
esptool.py --chip esp32s3 merge_bin -o ionity-k10-merged.bin \
  0x0 .pio/build/unihiker_k10/bootloader.bin \
  0x8000 .pio/build/unihiker_k10/partitions.bin \
  0x10000 .pio/build/unihiker_k10/firmware.bin
```

Copy the resulting `ionity-k10-merged.bin` into this folder (or attach it to a
GitHub Release and download it here). Verify it carries no secret:
`strings ionity-k10-merged.bin | grep -i <your-ssid>` → nothing sensitive.

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0

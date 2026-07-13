// Device detect + one-click flashing + WiFi provisioning over Web Serial (esptool-js).
// Requires a Chromium browser (Web Serial API). © Ionity (Pty) Ltd · Policy 986 AED
import { ESPLoader, Transport } from "esptool-js";

export type Logger = (line: string) => void;
export interface DeviceInfo { chip: string; mac?: string; alive: boolean; }

export function serialSupported(): boolean {
  return "serial" in navigator;
}

let _port: any = null;
let _transport: Transport | null = null;
let _loader: ESPLoader | null = null;

/** Connect over USB and identify the chip — the "is it alive?" check. */
export async function detect(log: Logger): Promise<DeviceInfo> {
  // @ts-ignore Web Serial
  _port = await navigator.serial.requestPort();
  _transport = new Transport(_port, true);
  _loader = new ESPLoader({
    transport: _transport,
    baudrate: 921600,
    terminal: { clean() {}, writeLine: (d: string) => log(d), write: (d: string) => log(d) },
  } as any);
  const chip = await _loader.main();
  let mac: string | undefined;
  try { mac = await (_loader as any).chip.readMac(_loader); } catch { /* optional */ }
  log(`Detected ${chip}${mac ? " · " + mac : ""}`);
  return { chip: String(chip), mac, alive: true };
}

/** Fetch the firmware image bundled with the installer (public/firmware/…). */
export async function fetchBundledFirmware(log: Logger): Promise<string> {
  log("Fetching bundled IonityEdge firmware…");
  const r = await fetch("/firmware/ionity-k10-merged.bin");
  if (!r.ok) throw new Error("bundled firmware not found (public/firmware/ionity-k10-merged.bin)");
  const buf = new Uint8Array(await r.arrayBuffer());
  let s = ""; for (let i = 0; i < buf.length; i++) s += String.fromCharCode(buf[i]);
  log(`Firmware loaded (${(buf.length / 1024).toFixed(0)} KB)`);
  return s;
}

export function fileToBinaryString(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => {
      const b = new Uint8Array(r.result as ArrayBuffer);
      let s = ""; for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
      resolve(s);
    };
    r.onerror = reject; r.readAsArrayBuffer(file);
  });
}

/** Flash a merged image at 0x0. Requires detect() first. */
export async function flashMerged(dataBin: string, log: Logger) {
  if (!_loader) throw new Error("connect the device first (Device Check)");
  log("Flashing merged image @ 0x0…");
  await _loader.writeFlash({
    fileArray: [{ data: dataBin, address: 0x0 }],
    flashSize: "keep", flashMode: "keep", flashFreq: "keep",
    eraseAll: false, compress: true,
    reportProgress: (_i: number, w: number, t: number) => log(`  ${Math.round((w / t) * 100)}%`),
  } as any);
  log("✔ Flash complete. Resetting…");
  // Reset out of download mode — method name varies across esptool-js versions.
  try {
    const l = _loader as any;
    if (typeof l.hardReset === "function") await l.hardReset();
    else if (typeof l.after === "function") await l.after();
    else if (_transport) { await _transport.setRTS(true); await _transport.setRTS(false); }
  } catch { /* reset is best-effort */ }
}

/** Provision WiFi + Edge host by writing a PROV line the firmware parses over Serial. */
export async function provision(cfg: { ssid: string; pass: string; host: string; port: number }, log: Logger) {
  if (!_port) throw new Error("connect the device first (Device Check)");
  const line = "PROV " + JSON.stringify(cfg) + "\n";
  const writer = _port.writable.getWriter();
  await writer.write(new TextEncoder().encode(line));
  writer.releaseLock();
  log(`Sent WiFi "${cfg.ssid}" + Edge ${cfg.host}:${cfg.port} → board NVS. Rebooting.`);
}

export function isConnected(): boolean { return !!_loader; }

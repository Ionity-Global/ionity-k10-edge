// Flash & Provision — one-click bundled firmware + WiFi provisioning.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useState } from "react";
import { Card } from "../components/ui";
import {
  detect, flashMerged, fetchBundledFirmware, fileToBinaryString,
  provision, isConnected, serialSupported,
} from "../lib/webserial-flash";
import { getBase } from "../lib/edge-api";

export default function Flash() {
  const [log, setLog] = useState("Ready.\n");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(isConnected());
  const [ssid, setSsid] = useState("Antwerp Ionity");
  const [pass, setPass] = useState("");
  const [host, setHost] = useState(getBase().replace(/^https?:\/\//, "").split(":")[0] || "192.168.1.100");
  const append = (l: string) => setLog((p) => p + l + "\n");
  const wrap = (fn: () => Promise<void>) => async () => { setBusy(true); try { await fn(); } catch (e: any) { append("✘ " + e.message); } finally { setBusy(false); } };

  const connect = wrap(async () => { await detect(append); setConnected(true); });
  const flashBundled = wrap(async () => {
    if (!isConnected()) { await detect(append); setConnected(true); }
    const bin = await fetchBundledFirmware(append);
    await flashMerged(bin, append);
  });
  const flashCustom = (f?: File) => wrap(async () => {
    if (!f) return;
    if (!isConnected()) { await detect(append); setConnected(true); }
    const bin = await fileToBinaryString(f);
    await flashMerged(bin, append);
  })();
  const sendWifi = wrap(async () => {
    if (!isConnected()) { await detect(append); setConnected(true); }
    await provision({ ssid, pass, host, port: 8765 }, append);
  });

  return (
    <>
      <h1>Flash <span className="accent">&amp;</span> Provision</h1>
      <p className="sub">Step 2 — flash the latest IonityEdge firmware and hand the board your WiFi + Edge Brain address. Nothing leaves your machine.</p>
      {!serialSupported() && <Card><p style={{ color: "var(--warn)" }}>⚠ Use Chrome/Edge, or the CLI flasher.</p></Card>}

      <div className="grid wide">
        <Card title="One-click firmware">
          <p className="sub">Flashes the bundled merged image at 0x0 — no file picking.</p>
          <button className="btn big" disabled={busy} onClick={flashBundled}>⚡ Flash IonityEdge (bundled)</button>
          <label style={{ marginTop: 14, display: "block" }}>…or flash a custom build</label>
          <input type="file" accept=".bin" disabled={busy} onChange={(e) => flashCustom(e.target.files?.[0] ?? undefined)} />
          <div className="row"><span className="pill" style={{ color: connected ? "var(--ok)" : "var(--muted)" }}>{connected ? "USB connected" : "not connected"}</span>
            {!connected && <button className="btn ghost" disabled={busy} onClick={connect}>Connect</button>}</div>
        </Card>

        <Card title="WiFi + Edge Brain">
          <label>WiFi SSID</label>
          <input value={ssid} onChange={(e) => setSsid(e.target.value)} />
          <label>WiFi password</label>
          <input type="password" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="written to board NVS only" />
          <label>Edge Brain host (this PC's LAN IP)</label>
          <input value={host} onChange={(e) => setHost(e.target.value)} />
          <button className="btn" disabled={busy} onClick={sendWifi}>📶 Send WiFi to board</button>
        </Card>

        <Card title="Console" className="card">
          <div className="log">{log}</div>
        </Card>
      </div>
    </>
  );
}

// Device Check — the FIRST screen. Proves the K10 is alive over USB before anything else.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useState } from "react";
import { Card } from "../components/ui";
import { detect, serialSupported, DeviceInfo } from "../lib/webserial-flash";

export default function DeviceCheck({ goFlash }: { goFlash: () => void }) {
  const [log, setLog] = useState("Plug the K10 in over USB, then run the check.\n");
  const [info, setInfo] = useState<DeviceInfo | null>(null);
  const [state, setState] = useState<"idle" | "checking" | "alive" | "dead">("idle");
  const append = (l: string) => setLog((p) => p + l + "\n");

  const run = async () => {
    setState("checking"); setInfo(null);
    try {
      const d = await detect(append);
      setInfo(d); setState("alive");
    } catch (e: any) {
      append("✘ " + e.message);
      append("Tips: close any open Serial Monitor (Arduino IDE / VS Code / Mind+) that may hold the port, then retry.");
      setState("dead");
    }
  };

  return (
    <>
      <h1>Device <span className="accent">Check</span></h1>
      <p className="sub">Step 1 — confirm your UNIHIKER K10 is alive and reachable over USB. (Chromium browser required for Web Serial.)</p>

      {state === "alive" && info && (
        <div className="verdict alive">
          <span className="big">✅</span>
          <div>
            <b>Board is ALIVE</b> — {info.chip}{info.mac ? ` · MAC ${info.mac}` : ""}.
            <div className="sub">A blank LCD just means the display driver isn't wired yet (BSP) — the chip is running fine.</div>
          </div>
        </div>
      )}
      {state === "dead" && (
        <div className="verdict dead">
          <span className="big">⚠</span>
          <div><b>No device detected</b><div className="sub">Check the USB cable, close any serial monitor holding the port, and retry.</div></div>
        </div>
      )}

      {!serialSupported() && (
        <Card><p style={{ color: "var(--warn)" }}>⚠ Web Serial needs Chrome or Edge. In other browsers, use <code>flasher/flash.ps1</code>.</p></Card>
      )}

      <div className="grid wide">
        <Card title="Health check">
          <p className="sub">Connects over USB and reads the chip type + MAC — the definitive "is it alive?" test.</p>
          <button className="btn big" disabled={state === "checking"} onClick={run}>
            {state === "checking" ? "Checking…" : "🔌 Check my K10"}
          </button>
          {info && (
            <div style={{ marginTop: 14 }}>
              <div className="metric-row"><span>Chip</span><b>{info.chip}</b></div>
              {info.mac && <div className="metric-row"><span>MAC</span><b>{info.mac}</b></div>}
              <div className="metric-row"><span>Status</span><b style={{ color: "var(--ok)" }}>running</b></div>
            </div>
          )}
        </Card>

        <Card title="Console">
          <div className="log">{log}</div>
          {state === "alive" && (
            <button className="btn ghost" style={{ marginTop: 12 }} onClick={goFlash}>Next → Flash &amp; WiFi</button>
          )}
        </Card>
      </div>
    </>
  );
}

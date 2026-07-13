// Live Stream — the "everything, as a stream" dashboard for the Edge Brain + K10.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useEffect, useState } from "react";
import { Card, Gauge, Pill } from "../components/ui";
import { poll } from "../lib/live";
import { getBase } from "../lib/edge-api";

export default function Stream() {
  const [status, setStatus] = useState<any>(null);
  const [devices, setDevices] = useState<any>(null);
  const [cache, setCache] = useState<any>(null);
  const [recs, setRecs] = useState<any>(null);
  const [ad, setAd] = useState<any>(null);
  const [online, setOnline] = useState(false);

  useEffect(() => {
    const stops = [
      poll<any>("/api/status", 3000, (d) => { setStatus(d); setOnline(!!d); }),
      poll<any>("/api/devices", 2000, (d) => d && setDevices(d)),
      poll<any>("/api/cache", 5000, (d) => d && setCache(d)),
      poll<any>("/api/recordings", 10000, (d) => d && setRecs(d)),
      poll<any>("/api/ads/next", 9000, (d) => d && setAd(d)),
    ];
    return () => stops.forEach((s) => s());
  }, []);

  const dev = devices?.devices?.[0];
  const t = dev?.telemetry?.latest ?? {};
  const loc = dev?.telemetry?.location ?? {};
  const st = dev?.telemetry?.state ?? dev?.state ?? {};   // server-computed render
  const m = status?.brain?.models ?? {};

  return (
    <>
      <h1>Live <span className="accent">Stream</span></h1>
      <p className="sub">
        Real-time view of the Edge Brain + connected K10s at <code>{getBase()}</code> —{" "}
        {online ? <Pill on>online</Pill> : <Pill warn>Edge Brain offline — start it: <code>python -m app.main</code></Pill>}
      </p>

      {ad?.title && <div className="card hero ticker" style={{ marginBottom: 14 }}><span>◆ {ad.title} — {ad.body}</span></div>}

      <div className="grid wide">
        <Card title="Devices linked" className="card">
          <div className="stat">{devices?.devices?.length ?? 0}<small> K10 node(s)</small></div>
          {dev && <div className="sub" style={{ marginTop: 8 }}>{dev.device_id} · {dev.ip ?? "—"}</div>}
          {!dev && <div className="sub" style={{ marginTop: 8 }}>Awaiting a board to connect over WiFi…</div>}
        </Card>

        <Card title="Environment (live)">
          <div className="row" style={{ justifyContent: "space-around" }}>
            <Gauge value={t.temp_c ?? NaN} max={60} unit="°C" label="Temp" />
            <Gauge value={t.humidity ?? NaN} max={100} unit="%" label="Humidity" color="#26de81" />
            <Gauge value={t.light ?? NaN} max={1000} unit="lx" label="Light" color="#f7b731" />
          </div>
        </Card>

        <Card title="Motion / power">
          <div className="metric-row"><span>Accel X/Y/Z</span><b>{fmt(t.ax)}, {fmt(t.ay)}, {fmt(t.az)}</b></div>
          <div className="metric-row"><span>Battery</span><b>{t.batt ?? "—"}%</b></div>
          <div className="metric-row"><span>Samples</span><b>{dev?.telemetry?.samples ?? 0}</b></div>
        </Card>

        <Card title="Camera stream">
          <div className="frame">{online ? "▶ awaiting frames from K10 camera" : "offline"}</div>
          <div className="sub" style={{ marginTop: 8 }}>Face / object / QR + OCR run on the Edge Brain.</div>
        </Card>

        <Card title="Voice · mood">
          <div className="metric-row"><span>Wake-word</span><Pill on={!!m.stt}>{m.stt ? "ready" : "install STT"}</Pill></div>
          <div className="metric-row"><span>Live mood</span><b>{st.label ? `${st.label} · ${Math.round((st.level ?? 0)*100)}%` : "—"}</b></div>
          <div className="sub" style={{ marginTop: 8 }}>Sound-reactive mood from the mic; transcript + voice mood appear here.</div>
        </Card>

        <Card title="Geolocation">
          <div className="metric-row"><span>Method</span><b>{loc.method ?? "—"}</b></div>
          <div className="metric-row"><span>Lat, Lon</span><b>{loc.lat ?? "—"}, {loc.lon ?? "—"}</b></div>
          <div className="sub" style={{ marginTop: 8 }}>WiFi-based positioning for the moving device.</div>
        </Card>

        <Card title="AI models (Edge Brain)">
          <div className="row">
            {["stt", "tts", "ocr", "vision", "mood", "local_llm"].map((k) => (
              <Pill key={k} on={!!m[k]}>{k}</Pill>
            ))}
          </div>
          <div className="metric-row" style={{ marginTop: 10 }}><span>Claude bridge</span><Pill on={!!status?.brain?.bridge?.enabled}>{status?.brain?.bridge?.mode ?? "off"}</Pill></div>
        </Card>

        <Card title="Semantic cache">
          <div className="stat">{cache?.items ?? 0}<small> entries</small></div>
          <div className="sub" style={{ marginTop: 6 }}>{cache?.embedder ?? "—"} · sim ≥ {cache?.threshold ?? "—"}</div>
        </Card>

        <Card title="Recordings">
          {recs?.recordings?.length
            ? recs.recordings.slice(0, 4).map((r: any, i: number) => (
                <div className="metric-row" key={i}><span>{r.device_id}</span><b>{r.duration_s}s</b></div>
              ))
            : <div className="sub">No recordings yet — captured sessions land here (SD + Edge Brain).</div>}
        </Card>
      </div>

      <div className="foot">Live-polling the Edge Brain · AEDI provenance on every capture · Policy 986 AED</div>
    </>
  );
}

function fmt(v: any) { return typeof v === "number" ? v.toFixed(2) : "—"; }

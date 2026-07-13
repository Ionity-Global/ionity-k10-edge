// Orb Tuning — edit every orb parameter live from localhost; the K10 pulls it within ~4s.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useEffect, useState } from "react";
import { Card } from "../components/ui";
import { getBase } from "../lib/edge-api";

type Cfg = Record<string, any>;
const COLORS: [string, string][] = [
  ["calm", "Calm (quiet) — blue"],
  ["neutral", "Neutral — cyan"],
  ["warn", "Active — green"],
  ["agitated", "Aggravated (loud) — red"],
];
const NUM: [string, string, number, number, number][] = [
  ["base_r", "Base radius", 10, 80, 1],
  ["pulse", "Sound pulse size", 0, 120, 1],
  ["darken", "Darken @ aggravated", 0, 1, 0.05],
  ["attack", "Agitation attack", 0.01, 0.5, 0.01],
  ["decay", "Agitation decay", 0.8, 0.999, 0.005],
  ["calm_th", "Calm threshold", 0, 1, 0.02],
  ["agit_th", "Aggravated threshold", 0, 1, 0.02],
  ["bright_min", "LED min brightness", 0, 9, 1],
  ["bright_max", "LED max brightness", 0, 9, 1],
  ["fps_ms", "Frame delay (ms)", 15, 120, 1],
];

export default function Orb() {
  const [c, setC] = useState<Cfg | null>(null);
  const [msg, setMsg] = useState("");
  useEffect(() => {
    fetch(getBase() + "/api/orb-config").then((r) => r.json()).then(setC)
      .catch(() => setMsg("Edge Brain offline — start it (python -m app.main) to load config"));
  }, []);
  if (!c) return (<><h1>Orb <span className="accent">Tuning</span></h1><p className="sub">{msg || "loading…"}</p></>);

  const set = (k: string, v: any) => setC({ ...c, [k]: v });
  const hx = (v: string) => "#" + v;
  const un = (v: string) => v.replace("#", "").toUpperCase();
  const save = async () => {
    try {
      const r = await fetch(getBase() + "/api/orb-config", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(c),
      });
      setC(await r.json()); setMsg("Saved ✓ — the K10 applies it within ~4 seconds");
    } catch (e: any) { setMsg(e.message); }
  };
  const reset = async () => {
    const r = await fetch(getBase() + "/api/orb-config/reset", { method: "POST" });
    setC(await r.json()); setMsg("Reset to defaults");
  };

  return (
    <>
      <h1>Orb <span className="accent">Tuning</span></h1>
      <p className="sub">Everything the orb does — live. Save and the K10 picks it up within ~4 s, no reflash.</p>
      <div className="grid wide">
        <Card title="Mood palette">
          {COLORS.map(([k, label]) => (
            <div key={k} className="metric-row"><span>{label}</span>
              <input type="color" value={hx(c[k])} onChange={(e) => set(k, un(e.target.value))}
                style={{ width: 64, height: 34, padding: 0, margin: 0 }} /></div>
          ))}
          <div className="row" style={{ marginTop: 14, justifyContent: "space-around" }}>
            {COLORS.map(([k]) => (
              <div key={k} style={{ width: 46, height: 46, borderRadius: "50%",
                background: hx(c[k]), boxShadow: `0 0 18px ${hx(c[k])}` }} />
            ))}
          </div>
        </Card>

        <Card title="Dynamics">
          {NUM.map(([k, label, min, max, step]) => (
            <div key={k} style={{ marginBottom: 6 }}>
              <label>{label}: <b>{c[k]}</b></label>
              <input type="range" min={min} max={max} step={step} value={c[k]}
                onChange={(e) => set(k, step < 1 ? parseFloat(e.target.value) : parseInt(e.target.value))} />
            </div>
          ))}
        </Card>

        <Card title="Apply">
          <button className="btn big" onClick={save}>💾 Save to device</button>
          <button className="btn ghost" style={{ marginTop: 10 }} onClick={reset}>Reset defaults</button>
          {msg && <p className="sub" style={{ marginTop: 12 }}>{msg}</p>}
          <p className="sub" style={{ marginTop: 12 }}>
            Calm → blue · louder/sustained → green → <b style={{ color: "#E23B4E" }}>red &amp; darker</b>.
          </p>
        </Card>
      </div>
    </>
  );
}

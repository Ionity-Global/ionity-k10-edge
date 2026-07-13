// Mini ESP screen mirror — renders the K10 orb in the browser from live telemetry,
// using the same mood palette as the device (pulled from /api/orb-config).
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useEffect, useRef, useState } from "react";
import { getBase } from "../lib/edge-api";

type Pal = Record<string, any>;
const DEF: Pal = { calm: "1E7BFF", neutral: "00D2FF", warn: "26DE81", agitated: "E23B4E",
  base_r: 36, pulse: 48, darken: 0.55 };

const rgb = (h: string) => { h = h.replace("#", ""); return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]; };
const hex = (r:number,g:number,b:number) => "#"+[r,g,b].map(x=>Math.max(0,Math.min(255,x|0)).toString(16).padStart(2,"0")).join("");
const lerp = (a:string,b:string,t:number) => { const A=rgb(a),B=rgb(b); return hex(A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t,A[2]+(B[2]-A[2])*t); };
const darken = (h:string,f:number) => { const [r,g,b]=rgb(h); return hex(r*f,g*f,b*f); };
function moodColor(p: Pal, x: number) {
  x = Math.max(0, Math.min(1, x));
  if (x < 0.34) return lerp("#"+p.calm, "#"+p.neutral, x/0.34);
  if (x < 0.67) return lerp("#"+p.neutral, "#"+p.warn, (x-0.34)/0.33);
  return lerp("#"+p.warn, "#"+p.agitated, (x-0.67)/0.33);
}

export default function DeviceScreen() {
  const [pal, setPal] = useState<Pal>(DEF);
  const [t, setT] = useState<any>(null);     // raw sensor upload (temp/light/ip/level)
  const [st, setSt] = useState<any>(null);   // SERVER-computed render (color/label/mood/radius/leds)
  const [ip, setIp] = useState<string>("");
  const phase = useRef(0);
  const [, tick] = useState(0);

  useEffect(() => {
    const cfg = () => fetch(getBase()+"/api/orb-config").then(r=>r.json()).then(setPal).catch(()=>{});
    const live = () => fetch(getBase()+"/api/live").then(r=>r.json()).then(d=>{
      const dev = d.devices && (d.devices["ionity-k10"] || Object.values(d.devices)[0] as any);
      if (dev && dev.latest) { setT(dev.latest); if (dev.latest.ip) setIp(dev.latest.ip); }
      setSt((dev && dev.state) || null);   // the device displays exactly this
    }).catch(()=>{ setT(null); setSt(null); });
    cfg(); live();
    const a = setInterval(live, 700), b = setInterval(cfg, 5000);
    const c = setInterval(() => { phase.current += 0.18; tick(x=>x+1); }, 60);
    return () => { clearInterval(a); clearInterval(b); clearInterval(c); };
  }, []);

  // Mirror the SERVER's render (single source of truth); fall back to local palette compute.
  const level = st?.level ?? t?.level ?? 0;
  const mood = st?.mood ?? 0;
  const label = st?.label ?? (t ? "CALM" : "—");
  const breathe = 0.5 + 0.5 * Math.sin(phase.current);
  const orb = st?.color ? ("#" + st.color) : darken(moodColor(pal, mood), 1 - (pal.darken ?? 0.55) * mood);
  const leds: string[] = st?.leds ?? [];
  const R = (st?.radius ?? ((pal.base_r ?? 36) + level * (pal.pulse ?? 48))) + breathe * 7;   // device px
  const s = 0.62;                                                           // scale to svg
  const cx = 100, cy = 118, r = R * s;

  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center" }}>
      <div style={{ position: "relative", width: 200, height: 266, borderRadius: 18,
        background: "#03080f", border: "1px solid var(--line)", boxShadow: "0 10px 40px rgba(0,0,0,.4)", overflow: "hidden" }}>
        <svg width="200" height="236" viewBox="0 0 200 236">
          <text x="12" y="20" fill="#00d2ff" fontSize="13" fontFamily="system-ui" letterSpacing="1">IONITY · ORB</text>
          <circle cx={cx} cy={cy} r={r+16} fill="none" stroke={darken(orb,0.18)} strokeWidth="2" />
          <circle cx={cx} cy={cy} r={r+8}  fill="none" stroke={darken(orb,0.4)}  strokeWidth="2" />
          <circle cx={cx} cy={cy} r={r} fill={orb} style={{ transition: "fill .3s" }} />
          <circle cx={cx - r/3} cy={cy - r/3} r={Math.max(2, r/6)} fill="#ffffff" opacity="0.9" />
          <text x="12" y="200" fill={orb} fontSize="12" fontFamily="system-ui">MOOD {label}</text>
          <text x="12" y="218" fill="#7fa6c9" fontSize="11" fontFamily="system-ui">
            {t ? `T ${(+t.temp_c).toFixed(1)}C · L ${t.light} · ${Math.round(level*100)}%` : "waiting for device…"}
          </text>
        </svg>
        {/* 3 LEDs below the "screen" */}
        <div style={{ display: "flex", justifyContent: "center", gap: 14, marginTop: 4 }}>
          {[0,1,2].map(i => {
            // Prefer the exact per-LED colour the server sent to the device.
            const c = leds[i];
            const lit = c ? c !== "000000" : (level*3 + breathe*0.4 > i);
            const bg = c ? "#" + c : darken(orb, 0.55 + 0.45*(i+1)/3);
            return <div key={i} style={{ width: 12, height: 12, borderRadius: "50%",
              background: lit ? bg : "#0c1826",
              boxShadow: lit ? `0 0 10px ${bg}` : "none", transition: ".15s" }} />;
          })}
        </div>
      </div>

      <div style={{ minWidth: 180 }}>
        <div className="metric-row"><span>Mood</span><b style={{ color: orb }}>{label}</b></div>
        <div className="metric-row"><span>Sound</span><b>{Math.round(level*100)}%</b></div>
        <div className="metric-row"><span>Temp</span><b>{t ? (+t.temp_c).toFixed(1)+" °C" : "—"}</b></div>
        <div className="metric-row"><span>Light</span><b>{t?.light ?? "—"}</b></div>
        <div className="metric-row"><span>Device</span><b>{ip || "—"}</b></div>
        {ip && <a className="btn ghost" style={{ display:"inline-block", marginTop:10, textDecoration:"none" }}
          href={`http://${ip}/`} target="_blank" rel="noreferrer">Open device page →</a>}
        {!t && <p className="sub" style={{ marginTop: 10 }}>No telemetry yet — flash the orb firmware pointed at this PC and power the K10 on WiFi.</p>}
      </div>
    </div>
  );
}

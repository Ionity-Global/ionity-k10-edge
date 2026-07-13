// UI primitives. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React from "react";

export function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={"card " + className}>
      {title && <h3>{title}</h3>}
      {children}
    </div>
  );
}

export function Stat({ label, value, unit }: { label: string; value: React.ReactNode; unit?: string }) {
  return (
    <div className="card">
      <h3>{label}</h3>
      <div className="stat">{value}{unit && <small> {unit}</small>}</div>
    </div>
  );
}

export function Pill({ on, warn, children }: { on?: boolean; warn?: boolean; children: React.ReactNode }) {
  const cls = warn ? "warn" : on ? "ok" : "off";
  return <span className={"pill " + cls}>{children}</span>;
}

/** Radial gauge (0..max). */
export function Gauge({ value, max, unit, label, color = "var(--primary)" }:
  { value: number; max: number; unit: string; label: string; color?: string }) {
  const r = 52, c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, (value || 0) / max));
  return (
    <div style={{ textAlign: "center" }}>
      <div className="gauge">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="10" />
          <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10"
            strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
            style={{ transition: "stroke-dashoffset .6s ease" }} />
        </svg>
        <div className="val"><b>{Number.isFinite(value) ? value.toFixed(1) : "—"}</b><span>{unit}</span></div>
      </div>
      <div className="sub" style={{ margin: "6px 0 0" }}>{label}</div>
    </div>
  );
}

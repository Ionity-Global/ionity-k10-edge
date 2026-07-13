// IonityEdge · K10 installer shell — Device-Check-first, flash, provision, live stream.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import React, { useEffect, useState } from "react";
import { api, getBase, setBase } from "./lib/edge-api";
import { Card } from "./components/ui";
import { poll } from "./lib/live";
import DeviceCheck from "./pages/DeviceCheck";
import Flash from "./pages/Flash";
import Stream from "./pages/Stream";
import Orb from "./pages/Orb";
import DeviceScreen from "./components/DeviceScreen";

type View = "device" | "flash" | "stream" | "screen" | "orb" | "ask" | "settings" | "about";
const NAV: { id: View; label: string; icon: string }[] = [
  { id: "device", label: "Device Check", icon: "🔌" },
  { id: "flash", label: "Flash & WiFi", icon: "⚡" },
  { id: "stream", label: "Live Stream", icon: "◧" },
  { id: "screen", label: "ESP Screen", icon: "📺" },
  { id: "orb", label: "Orb Tuning", icon: "🔮" },
  { id: "ask", label: "Ask / Voice", icon: "🎙" },
  { id: "settings", label: "Settings", icon: "⚙" },
  { id: "about", label: "About", icon: "◆" },
];

export default function App() {
  const [view, setView] = useState<View>("device");
  const [online, setOnline] = useState(false);
  useEffect(() => poll<any>("/api/status", 4000, (d) => setOnline(!!d)), []);

  return (
    <div className="app">
      <aside className="side">
        <div className="brand">
          <img className="logo" src="/brand/ionity-logo.svg" alt="Ionity"
            onError={(e) => ((e.target as HTMLImageElement).style.display = "none")} />
          <div><b>IonityEdge</b><small>K10 · True Edge AI</small></div>
        </div>
        <div className="conn"><span className={"dot " + (online ? "on" : "off")} />{online ? "Edge Brain online" : "Edge Brain offline"}</div>
        <nav className="nav">
          {NAV.map((n) => (
            <button key={n.id} className={view === n.id ? "active" : ""} onClick={() => setView(n.id)}>
              <span>{n.icon}</span>{n.label}
              {n.id === "stream" && online && <span className="badge live">live</span>}
            </button>
          ))}
        </nav>
        <div className="foot">© 2018–2026 Ionity (Pty) Ltd<br />Policy 986 AED · CC BY-SA 4.0<br />Building Tomorrow, Today.</div>
      </aside>

      <main className="main">
        {view === "device" && <DeviceCheck goFlash={() => setView("flash")} />}
        {view === "flash" && <Flash />}
        {view === "stream" && <Stream />}
        {view === "screen" && (
          <>
            <h1>ESP <span className="accent">Screen</span> — live mirror</h1>
            <p className="sub">The dashboard's mirror of the K10 orb — same mood colour + sound response the board shows.</p>
            <div className="card hero"><DeviceScreen /></div>
          </>
        )}
        {view === "orb" && <Orb />}
        {view === "ask" && <Ask />}
        {view === "settings" && <Settings />}
        {view === "about" && <About />}
      </main>
    </div>
  );
}

function Ask() {
  const [q, setQ] = useState(""); const [a, setA] = useState<any>(null); const [busy, setBusy] = useState(false);
  const run = async () => { setBusy(true); try { setA(await api.ask(q)); } catch (e: any) { setA({ text: e.message }); } finally { setBusy(false); } };
  return (
    <>
      <h1>Ask / <span className="accent">Voice</span></h1>
      <p className="sub">Query the Edge Brain (cache → local model → Claude bridge). On the K10 this fires on the mic wake-word.</p>
      <Card>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask Ionity Edge…" onKeyDown={(e) => e.key === "Enter" && run()} />
        <button className="btn" disabled={busy || !q} onClick={run}>Ask</button>
        {a && <div style={{ marginTop: 14 }}><div className="row"><span className="pill ok">{a.source ?? "?"}</span><span className="sub">mood {a.mood?.mood} · conf {a.confidence}</span></div><p style={{ fontSize: 16 }}>{a.text}</p></div>}
      </Card>
    </>
  );
}

function Settings() {
  const [base, setB] = useState(getBase());
  return (
    <>
      <h1><span className="accent">Settings</span></h1>
      <p className="sub">Point the installer at your Edge Brain.</p>
      <Card title="Edge Brain endpoint">
        <label>Base URL</label>
        <input value={base} onChange={(e) => setB(e.target.value)} placeholder="http://192.168.1.100:8765" />
        <button className="btn" onClick={() => { setBase(base); location.reload(); }}>Save &amp; reload</button>
      </Card>
    </>
  );
}

function About() {
  return (
    <>
      <h1><span className="accent">About</span></h1>
      <Card>
        <p><b>IonityEdge · K10</b> — the board is the face, your machine is the brain.</p>
        <p className="sub">Local-first, no API keys, open-source under Ionity Global.</p>
        <p>© 2018–2026 Ionity (Pty) Ltd · Johan Wilhelm van Antwerp · Policy 986 AED · CC BY-SA 4.0</p>
        <p className="row"><a href="https://www.ionity.today" target="_blank">ionity.today</a><a href="https://www.ionity.co.za" target="_blank">ionity.co.za</a></p>
        <p className="sub">Anything is Possible with God.</p>
      </Card>
    </>
  );
}

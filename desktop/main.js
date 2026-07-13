// Ionity Home Assistant — desktop app (Electron).
// Auto-starts the Edge Brain (Ollama + FastAPI) and opens the branded dashboard in a
// native window. Everything runs locally; the K10 is just the mic/speaker/display node.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
const { app, BrowserWindow, shell, Menu } = require("electron");
const { spawn } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");
const fs = require("node:fs");

const PORT = 8765;
const URL = `http://127.0.0.1:${PORT}/`;
let server = null, win = null;

// edge-server lives next to this app in dev, or under resources/ when packaged
function edgeDir() {
  const dev = path.join(__dirname, "..", "edge-server");
  const packed = path.join(process.resourcesPath || "", "edge-server");
  return fs.existsSync(path.join(dev, "app", "main.py")) ? dev : packed;
}

function portOpen(port) {
  return new Promise((res) => {
    const s = net.connect(port, "127.0.0.1");
    s.setTimeout(500);
    s.on("connect", () => { s.destroy(); res(true); });
    s.on("error", () => res(false));
    s.on("timeout", () => { s.destroy(); res(false); });
  });
}

async function startServer() {
  if (await portOpen(PORT)) { console.log("edge brain already running"); return; }
  const dir = edgeDir();
  // start Ollama (ignore if already up / missing)
  try { spawn("ollama", ["serve"], { detached: true, stdio: "ignore" }).unref(); } catch {}
  const py = process.platform === "win32" ? "py" : "python3";
  const args = process.platform === "win32" ? ["-3.12", "-m", "app.main"] : ["-m", "app.main"];
  server = spawn(py, args, {
    cwd: dir,
    env: { ...process.env, HF_HUB_OFFLINE: "1", TRANSFORMERS_OFFLINE: "1" },
    stdio: "ignore",
  });
  server.on("error", (e) => console.error("server spawn failed", e));
}

async function waitForServer(ms = 90000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await portOpen(PORT)) return true; await new Promise(r => setTimeout(r, 500)); }
  return false;
}

function createWindow(ready) {
  win = new BrowserWindow({
    width: 1200, height: 820, minWidth: 900, minHeight: 640,
    backgroundColor: "#050b14", title: "Ionity Home Assistant",
    icon: path.join(__dirname, "brand", "icon.ico"),
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true },
  });
  // links open in the real browser, not inside the app
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  win.loadURL(ready ? URL : "data:text/html," + encodeURIComponent(
    `<body style="background:#050b14;color:#00d2ff;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh">
     <div style="text-align:center"><h2>IONITY</h2><p>Starting the Edge Brain…</p></div></body>`));
}

const menu = Menu.buildFromTemplate([
  { label: "Ionity", submenu: [{ role: "reload" }, { role: "toggledevtools" }, { type: "separator" }, { role: "quit" }] },
]);

app.whenReady().then(async () => {
  Menu.setApplicationMenu(menu);
  createWindow(false);
  await startServer();
  const ok = await waitForServer();
  if (ok && win) win.loadURL(URL);
  else if (win) win.webContents.executeJavaScript("document.body.innerHTML='<div style=\\'color:#e94560;font-family:system-ui;padding:40px\\'>Edge Brain did not start. Ensure Python 3.12 + deps are installed (INSTALL.ps1).</div>'");
});

app.on("window-all-closed", () => { try { server && server.kill(); } catch {} app.quit(); });
app.on("before-quit", () => { try { server && server.kill(); } catch {} });

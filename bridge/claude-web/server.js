// Ionity Claude Web Bridge — relays Edge Brain prompts to claude.ai using YOUR Google
// login (no API key). Exposes POST /ask {prompt} -> {text}; the Edge Brain's
// app/bridge/claude_desktop.py speaks this exact contract (set BRIDGE_MODE=http).
//
// First run: a Chromium window opens at claude.ai — sign in with Google ONCE. The
// session persists in ./.profile, so subsequent runs are automatic.
//
// Env: BRIDGE_PORT (8799), BRIDGE_PROFILE (./.profile), BRIDGE_HEADLESS (0/1).
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.BRIDGE_PORT || 8799);
const USER_DATA = process.env.BRIDGE_PROFILE || path.join(__dirname, ".profile");
const HEADLESS = process.env.BRIDGE_HEADLESS === "1";

let ctx = null, page = null, booting = null, busy = false;

async function ensureBrowser() {
  if (ctx) return;
  if (booting) return booting;
  booting = (async () => {
    ctx = await chromium.launchPersistentContext(USER_DATA, {
      headless: HEADLESS,
      viewport: { width: 1200, height: 900 },
      args: ["--disable-blink-features=AutomationControlled"],
    });
    page = ctx.pages()[0] || (await ctx.newPage());
    await page.goto("https://claude.ai/new", { waitUntil: "domcontentloaded" }).catch(() => {});
    console.log("[bridge] Chromium up. If prompted, sign in to claude.ai with Google (once).");
  })();
  await booting;
}

async function loggedIn() {
  try {
    const url = page.url();
    if (/login|auth|google/i.test(url)) return false;
    // the composer only exists when authenticated
    return (await page.locator('div[contenteditable="true"]').count()) > 0;
  } catch { return false; }
}

async function ask(prompt) {
  await ensureBrowser();
  await page.goto("https://claude.ai/new", { waitUntil: "domcontentloaded" }).catch(() => {});
  const editor = page.locator('div[contenteditable="true"]').first();
  await editor.waitFor({ state: "visible", timeout: 30000 });
  await editor.click();
  // fill() is unreliable on ProseMirror; type as a fallback
  try { await editor.fill(prompt); } catch { await editor.type(prompt, { delay: 4 }); }
  await page.keyboard.press("Enter");

  // Wait for the streamed reply to stabilize (or the stop button to disappear).
  const started = Date.now();
  let last = "", stable = 0;
  while (Date.now() - started < 120000) {
    await page.waitForTimeout(700);
    const txt = await page.evaluate(() => {
      const sel = [
        '[data-testid="assistant-message"]',
        '.font-claude-message',
        'div[data-is-streaming] .prose',
        'div.prose',
      ];
      let nodes = [];
      for (const s of sel) { const n = document.querySelectorAll(s); if (n.length) nodes = [...n]; }
      const el = nodes[nodes.length - 1];
      return el ? el.innerText.trim() : "";
    }).catch(() => "");
    const streaming = await page.locator('button[aria-label*="Stop" i], button[aria-label*="stop" i]')
      .count().catch(() => 0);
    if (txt && txt === last && !streaming) { if (++stable >= 2) break; }
    else { stable = 0; last = txt || last; }
  }
  return (last || "").trim();
}

function send(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") return send(res, 200, { ok: true });
  if (req.method === "GET" && req.url.startsWith("/health")) {
    return send(res, 200, { ok: true, loggedIn: ctx ? await loggedIn() : false, busy });
  }
  if (req.method === "POST" && req.url.startsWith("/ask")) {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      let prompt = "";
      try { prompt = (JSON.parse(raw || "{}").prompt || "").toString(); } catch {}
      if (!prompt) return send(res, 400, { text: "", ok: false, error: "no prompt" });
      if (busy) return send(res, 429, { text: "", ok: false, error: "busy" });
      busy = true;
      try {
        const text = await ask(prompt);
        send(res, 200, { text, ok: !!text, backend: "claude-web" });
      } catch (e) {
        send(res, 500, { text: "", ok: false, error: String(e && e.message || e) });
      } finally { busy = false; }
    });
    return;
  }
  send(res, 404, { ok: false, error: "not found" });
});

server.listen(PORT, "127.0.0.1", async () => {
  console.log(`[bridge] Ionity Claude Web Bridge on http://127.0.0.1:${PORT}  (POST /ask, GET /health)`);
  try { await ensureBrowser(); } catch (e) { console.error("[bridge] browser boot failed:", e.message); }
});

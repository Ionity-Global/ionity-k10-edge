// Edge Brain REST client. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
const KEY = "ionity.edge.base";

export function getBase(): string {
  return localStorage.getItem(KEY) || "http://127.0.0.1:8765";
}
export function setBase(url: string) {
  localStorage.setItem(KEY, url.replace(/\/$/, ""));
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(getBase() + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  status: () => j<any>("/api/status"),
  devices: () => j<any>("/api/devices"),
  cache: () => j<any>("/api/cache"),
  recordings: () => j<any>("/api/recordings"),
  config: () => j<any>("/api/config"),
  nextAd: () => j<any>("/api/ads/next"),
  ask: (query: string) =>
    j<any>("/api/ask", { method: "POST", body: JSON.stringify({ query }) }),
  analyze: async (file: File, ocr = true) => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${getBase()}/api/analyze?ocr=${ocr}`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(`analyze → ${r.status}`);
    return r.json();
  },
};

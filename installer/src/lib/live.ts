// Live data layer for the Edge Brain — REST polling.
// (The device streams over HTTP /ingest; the dashboard/installer poll the Edge Brain.)
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import { getBase } from "./edge-api";

/** Poll a REST endpoint on an interval; returns a stop() fn. */
export function poll<T>(path: string, everyMs: number, cb: (data: T | null, err?: string) => void): () => void {
  let alive = true;
  const tick = async () => {
    try {
      const r = await fetch(getBase() + path);
      cb(r.ok ? await r.json() : null, r.ok ? undefined : `HTTP ${r.status}`);
    } catch (e: any) {
      if (alive) cb(null, e.message);
    }
  };
  tick();
  const id = setInterval(() => alive && tick(), everyMs);
  return () => { alive = false; clearInterval(id); };
}

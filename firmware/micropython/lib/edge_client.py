# Edge Brain client for MicroPython nodes (HTTP /ingest, pure usocket — no deps).
# Returns the PARSED server response, so the node can APPLY the server-computed render
# (orb colour, label, Claude's words) — same thin-node contract as the C++ firmware.
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
try:
    import usocket as socket
    import ujson as json
except ImportError:          # also runs under CPython for testing
    import socket
    import json


class EdgeClient:
    def __init__(self, host, port, device_id, timeout=3):
        self.host, self.port, self.device_id = host, port, device_id
        self.timeout = timeout

    def _post(self, path, obj):
        body = json.dumps(obj)
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        s = socket.socket()
        try:
            try:
                s.settimeout(self.timeout)
            except Exception:
                pass
            s.connect(addr)
            req = ("POST %s HTTP/1.0\r\nHost: %s\r\nContent-Type: application/json\r\n"
                   "Content-Length: %d\r\n\r\n%s") % (path, self.host, len(body), body)
            s.send(req.encode())
            raw = b""
            while True:
                chunk = s.recv(512)
                if not chunk:
                    break
                raw += chunk
                if len(raw) > 8192:
                    break
            i = raw.find(b"\r\n\r\n")           # JSON body starts after the blank line
            if i >= 0:
                try:
                    return json.loads(raw[i + 4:])
                except Exception:
                    return None
            return None
        except Exception:
            return None
        finally:
            s.close()

    def telemetry(self, reading):
        """Upload sensors; returns the server response dict:
        {"ok": true, "state": {"color": "RRGGBB", "label": "...", "say": "...",
                               "brightness": 0-9, "leds": [...], "audio_seq": n}}"""
        return self._post("/ingest", {"device_id": self.device_id, "telemetry": reading})

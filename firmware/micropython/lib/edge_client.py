# Minimal Edge Brain client for MicroPython demos (HTTP ingest).
# The production C++ firmware uses a full WebSocket; this keeps demos simple.
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import usocket as socket
import ujson as json

class EdgeClient:
    def __init__(self, host, port, device_id):
        self.host, self.port, self.device_id = host, port, device_id

    def _post(self, path, obj):
        body = json.dumps(obj)
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        s = socket.socket()
        try:
            s.connect(addr)
            req = "POST %s HTTP/1.0\r\nHost: %s\r\nContent-Type: application/json\r\n" \
                  "Content-Length: %d\r\n\r\n%s" % (path, self.host, len(body), body)
            s.send(req.encode())
            return s.recv(256)
        finally:
            s.close()

    def telemetry(self, reading):
        return self._post("/ingest", {"device_id": self.device_id, "telemetry": reading})

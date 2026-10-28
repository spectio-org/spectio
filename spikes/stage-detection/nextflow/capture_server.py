#!/usr/bin/env python3
"""Spike T2: capture server. Logs every request (method, path, body) as one JSON line.

usage: capture_server.py PORT OUT.jsonl
  * Tower routes (nf-tower, `-with-tower http://localhost:PORT`): POST /trace/create answers
    {"workflowId": ...}; every other request answers {} with 200.
  * nf-spectio plugin: POST /spectio/events (one JSON event per request).
"""
import json, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = open(sys.argv[2], "a", buffering=1)
LOCK = threading.Lock()
SEQ = [0]


class H(BaseHTTPRequestHandler):
    def _handle(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = {"__raw__": raw.decode("utf-8", "replace")}
        reply = {}
        if self.path.startswith("/trace/create"):
            reply = {"workflowId": "wf" + uuid.uuid4().hex[:10]}
        with LOCK:
            SEQ[0] += 1
            OUT.write(json.dumps({"seq": SEQ[0], "t": time.time(), "method": self.command,
                                  "path": self.path, "auth": "Authorization" in self.headers,
                                  "agent": self.headers.get("User-Agent"), "body": body,
                                  "reply": reply}, sort_keys=True) + "\n")
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = _handle

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()

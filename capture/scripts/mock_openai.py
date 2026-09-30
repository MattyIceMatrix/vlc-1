#!/usr/bin/env python3
"""A tiny OpenAI-compatible Chat Completions endpoint with canned replies, so an
agent framework can run with no API key and no network.

  python3 mock_openai.py PORT REQUEST_LOG

POST /v1/chat/completions: if the conversation holds no `tool` message yet, the
reply is an assistant message with two tool calls -- read_file (id call_allowed)
and delete_file (id call_refused), both on notes.txt. Once tool results are
present, the reply is a plain final answer. Every request body is appended to
REQUEST_LOG as one JSON line, as the ground truth of what the model was sent.
Binds 127.0.0.1 only.
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
N = [0]


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("mock: " + (fmt % a) + "\n")

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with open(LOG, "a") as f:
            f.write(json.dumps({"path": self.path, "body": body}) + "\n")
        if not self.path.endswith("/chat/completions"):
            return self._send(404, {"error": {"message": "only /v1/chat/completions is mocked"}})
        N[0] += 1
        msgs = body.get("messages", [])
        if any(m.get("role") == "tool" for m in msgs):
            msg = {"role": "assistant", "content": "Read notes.txt; the delete was refused.", "tool_calls": None}
            finish = "stop"
        else:
            msg = {"role": "assistant", "content": None, "tool_calls": [
                {"id": "call_allowed", "type": "function",
                 "function": {"name": "read_file", "arguments": json.dumps({"path": "notes.txt"})}},
                {"id": "call_refused", "type": "function",
                 "function": {"name": "delete_file", "arguments": json.dumps({"path": "notes.txt"})}}]}
            finish = "tool_calls"
        self._send(200, {"id": f"chatcmpl-mock-{N[0]}", "object": "chat.completion", "created": int(time.time()),
                         "model": body.get("model", "mock-model"),
                         "choices": [{"index": 0, "message": msg, "finish_reason": finish, "logprobs": None}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()

#!/usr/bin/env bash
# Lasso MCP Gateway capture: server-filesystem wrapped by the gateway over stdio with the
# basic guardrail and xetrack tracing; one clean read, one token-bearing read, one read
# outside the allowed root. BLAST RADIUS: GitHub-hosted runner only; writes $OUT/lasso and a mktemp dir.
GW=lasso; . "$(dirname "$0")/lib.sh"
W=$(mktemp -d); cd "$W" || exit 0
python3 -m venv .venv && . .venv/bin/activate
run pip install -q 'mcp-gateway[xetrack]'
run pip show mcp-gateway
pip freeze > "$O/pip-freeze.txt"
mkdir -p root logs
echo "hello from vlc1" > root/plain.txt
echo "deploy key: $FAKE_TOKEN" > root/tokens.txt
cat > mcp.json <<EOF
{"mcpServers":{"mcp-gateway":{"command":"mcp-gateway","args":[],
  "servers":{"filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","$W/root"]}}}}}
EOF
cp mcp.json "$O/mcp.json"
export XETRACK_DB_PATH=$W/tracing.db XETRACK_LOGS_PATH=$W/logs/ LOGLEVEL=DEBUG
python3 - "$W" "$O" <<'PY' 2>&1 | tee -a "$O/steps.txt"
import json, os, select, subprocess, sys, time
W, O = sys.argv[1:3]
p = subprocess.Popen(["mcp-gateway", "--mcp-json-path", f"{W}/mcp.json", "-p", "basic", "-p", "xetrack"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(f"{O}/gateway.log", "w"), text=True, bufsize=1)
tr = open(f"{O}/transcript.jsonl", "w")
def send(msg):
    tr.write(json.dumps({"dir": "->", "msg": msg}) + "\n"); tr.flush()
    p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()
def recv(want_id, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([p.stdout], [], [], 1)
        if not r:
            if p.poll() is not None: return None
            continue
        line = p.stdout.readline()
        if not line: return None
        try: m = json.loads(line)
        except Exception: m = {"raw": line}
        tr.write(json.dumps({"dir": "<-", "msg": m}) + "\n"); tr.flush()
        if m.get("id") == want_id: return m
    return None
try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "vlc1-capture", "version": "1"}}})
    print("initialize:", json.dumps(recv(1, 240))[:300])
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    time.sleep(8)
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tl = recv(2) or {}
    names = [t["name"] for t in tl.get("result", {}).get("tools", [])]
    print("tools:", names)
    def pick(*cands):
        return next((n for c in cands for n in names if n.endswith(c)), cands[0])
    read = pick("read_text_file", "read_file")
    calls = [(3, pick("list_directory"), {"path": f"{W}/root"}),
             (4, read, {"path": f"{W}/root/plain.txt"}),
             (5, read, {"path": f"{W}/root/tokens.txt"}),
             (6, read, {"path": "/etc/hostname"})]
    for i, name, args in calls:
        send({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}})
        print(f"call {i} {name}:", json.dumps(recv(i))[:400])
finally:
    time.sleep(2)
    p.stdin.close()
    try: p.wait(15)
    except Exception: p.kill()
PY
dump_sqlite "$W/tracing.db" "$O/db"
cp -r "$W/logs" "$O/logfiles" 2>/dev/null
note "done"

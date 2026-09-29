#!/usr/bin/env bash
# lib.sh -- shared helpers for the gateway captures (sourced, not run).
# BLAST RADIUS: runs only on a GitHub-hosted runner; writes only under $OUT and
# mktemp dirs; stops only the PIDs it started.
set +e +o pipefail
set -u
: "${OUT:?OUT must be set}" "${GW:?GW must be set}"
O="$OUT/$GW"; mkdir -p "$O"
note() { echo "$*" | tee -a "$O/steps.txt"; }
run() { note "\$ $*"; ( "$@" ) >>"$O/steps.txt" 2>&1; local rc=$?; note "[exit $rc]"; return $rc; }
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
waitfor() { local i; for i in $(seq 1 "${2:-60}"); do curl -s -o /dev/null -m 3 "$1" && return 0; sleep 2; done; return 1; }

# A GitHub-token-shaped string that is not a token: ghp_ + 36 alphanumerics.
FAKE_TOKEN="ghp_$(printf 'VLC1fakeToken%023d' 0)"

# MCP over streamable HTTP. Set MCP_URL; optional AUTH=(-H "Authorization: ...").
AUTH=()
SID=""
mcp_post() {
  local name=$1 body=$2
  local hdr=(-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
  [ -n "$SID" ] && hdr+=(-H "Mcp-Session-Id: $SID" -H 'MCP-Protocol-Version: 2025-06-18')
  printf '%s\n' "$body" > "$O/rpc-$name.request"
  curl -sS -m 60 -D "$O/rpc-$name.headers" -o "$O/rpc-$name.body" -w '%{http_code}' \
    "${hdr[@]}" "${AUTH[@]}" "$MCP_URL" -d "$body" > "$O/rpc-$name.status" 2>>"$O/steps.txt"
  note "rpc $name -> HTTP $(cat "$O/rpc-$name.status"): $(head -c 500 "$O/rpc-$name.body" | tr '\n' ' ')"
}
mcp_session() {
  SID=""
  mcp_post initialize '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"vlc1-capture","version":"1"}}}'
  SID=$(awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' "$O/rpc-initialize.headers" | tr -d '\r')
  note "session id: ${SID:-<none>}"
  mcp_post initialized '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  mcp_post tools-list '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
}
call() { mcp_post "$1" "{\"jsonrpc\":\"2.0\",\"id\":$2,\"method\":\"tools/call\",\"params\":{\"name\":\"$3\",\"arguments\":$4}}"; }

# Every non-empty table of a SQLite file, one JSON file per table.
dump_sqlite() {
  python3 - "$1" "$2" <<'PY' 2>&1 | tee -a "$O/steps.txt"
import sqlite3, json, sys
db, pre = sys.argv[1:3]
c = sqlite3.connect(db); c.row_factory = sqlite3.Row
for (t,) in c.execute("select name from sqlite_master where type='table' order by name"):
    rows = [dict(r) for r in c.execute(f'select * from "{t}"')]
    if rows:
        with open(f"{pre}.{t}.json", "w") as f:
            json.dump(rows, f, indent=1, default=lambda b: b.hex() if isinstance(b, bytes) else str(b))
    print("table", t, len(rows))
PY
}

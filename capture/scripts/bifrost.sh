#!/usr/bin/env bash
# Bifrost (Maxim AI) capture: server-filesystem as an MCP client with a one-tool allow-list;
# one allowed execute, one outside the allow-list, one nonexistent. No LLM provider key.
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/bifrost and a mktemp dir.
GW=bifrost; . "$(dirname "$0")/lib.sh"
W=$(mktemp -d); cd "$W" || exit 0
mkdir -p bf root; echo "hello from vlc1" > root/plain.txt
run npm view @maximhq/bifrost version
cat > bf/config.json <<EOF
{"client":{"enable_logging":true,"disable_auth_on_inference":true},
 "mcp":{"client_configs":[{"name":"fs","connection_type":"stdio",
   "stdio_config":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","$W/root"],"envs":["HOME","PATH"]},
   "tools_to_execute":["list_directory"]}]}}
EOF
cp bf/config.json "$O/config.json"
npx -y @maximhq/bifrost -app-dir "$W/bf" -host 127.0.0.1 -port 8080 > "$O/gateway.log" 2>&1 & PIDS+=($!)
waitfor http://127.0.0.1:8080/ 90 || { note "bifrost not answering"; tail -40 "$O/gateway.log" | tee -a "$O/steps.txt"; }
sleep 10
curl -sS http://127.0.0.1:8080/api/mcp/clients > "$O/api-mcp-clients.json" 2>&1
note "clients: $(head -c 400 "$O/api-mcp-clients.json")"
X=http://127.0.0.1:8080/v1/mcp/tool/execute
ex() { # label name argsjson
  curl -sS -m 60 -w '\nHTTP %{http_code}\n' $X -H 'Content-Type: application/json' \
    -d "{\"id\":\"$1\",\"type\":\"function\",\"function\":{\"name\":\"$2\",\"arguments\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$3")}}" \
    > "$O/exec-$1.body" 2>&1
  note "exec $1 ($2): $(head -c 500 "$O/exec-$1.body" | tr '\n' ' ')"
}
ex allowed fs-list_directory "{\"path\":\"$W/root\"}"
ex denied-not-in-allowlist fs-write_file "{\"path\":\"$W/root/x.txt\",\"content\":\"y\"}"
ex nonexistent fs-no_such_tool '{}'
sleep 5
for ep in mcp-logs logs/dropped; do curl -sS "http://127.0.0.1:8080/api/$ep" > "$O/api-$(echo $ep | tr / -).json" 2>&1; done
# Deletion probe, run 4: can a caller on the same port remove the refused call's record?
DID=$(python3 -c "import json;l=json.load(open('$O/api-mcp-logs.json'))['logs'];print(next(x['id'] for x in l if x['tool_name']=='write_file'))" 2>>"$O/steps.txt")
note "record of the refused write_file call: ${DID:-<none>}"
if [ -n "$DID" ]; then
  for body in "{\"ids\":[\"$DID\"]}"; do
    curl -sS -X DELETE -H 'Content-Type: application/json' -d "$body" -w '\nHTTP %{http_code}\n' http://127.0.0.1:8080/api/mcp-logs > "$O/delete-attempt.body" 2>&1
    note "DELETE /api/mcp-logs $body -> $(tr '\n' ' ' < "$O/delete-attempt.body")"
  done
  curl -sS http://127.0.0.1:8080/api/mcp-logs > "$O/api-mcp-logs-after-delete.json" 2>&1
  note "after delete: $(python3 -c "import json;l=json.load(open('$O/api-mcp-logs-after-delete.json'))['logs'];print(len(l),'records:',[x['tool_name'] for x in l])" 2>&1)"
  curl -sS http://127.0.0.1:8080/api/logs/dropped > "$O/api-logs-dropped-after-delete.json" 2>&1
  note "dropped counter after delete: $(cat "$O/api-logs-dropped-after-delete.json")"
fi
kill "${PIDS[@]}" 2>/dev/null; sleep 2
ls -la "$W/bf" | tee -a "$O/steps.txt"
[ -f "$W/bf/logs.db" ] && dump_sqlite "$W/bf/logs.db" "$O/logsdb"
note "wrote x.txt? $( [ -f "$W/root/x.txt" ] && echo YES || echo no )"
note "done"

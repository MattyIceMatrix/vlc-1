#!/usr/bin/env bash
# IBM ContextForge capture: server-everything registered through its stdio bridge; one
# allowed call, one blocked by the PII filter plugin, one with a token lacking tools.execute.
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/contextforge and a mktemp dir.
GW=contextforge; . "$(dirname "$0")/lib.sh"
W=$(mktemp -d); cd "$W" || exit 0
python3 -m venv .venv && . .venv/bin/activate
run pip install -q 'mcp-contextforge-gateway[plugins]'
run pip show mcp-contextforge-gateway
pip freeze > "$O/pip-freeze.txt"
run python3 -m mcpgateway.scripts.init_secrets
note "generated secret names: $(cut -d= -f1 .env.secrets 2>/dev/null | grep -v '^#' | tr '\n' ' ')"
set -a; . ./.env.secrets 2>/dev/null; set +a
JWT_SECRET_KEY=$(grep '^JWT_SECRET_KEY=' .env.secrets 2>/dev/null | cut -d= -f2-)
AUTH_ENCRYPTION_SECRET=$(grep '^AUTH_ENCRYPTION_SECRET=' .env.secrets 2>/dev/null | cut -d= -f2-)
[ -n "$JWT_SECRET_KEY" ] || JWT_SECRET_KEY=$(openssl rand -hex 32)
[ -n "$AUTH_ENCRYPTION_SECRET" ] || AUTH_ENCRYPTION_SECRET=$(openssl rand -hex 32)
export JWT_SECRET_KEY AUTH_ENCRYPTION_SECRET
cat > ci-plugins.yaml <<'EOF'
plugin_settings: {plugin_timeout: 30, fail_on_plugin_error: false}
plugins:
  - name: PIIFilterPlugin
    kind: cpex_pii_filter.PIIFilterPlugin
    hooks: [tool_pre_invoke]
    mode: enforce
    priority: 50
    conditions: []
    config: {detect_ssn: true, block_on_detection: true, log_detections: true, include_detection_details: true}
EOF
cp ci-plugins.yaml "$O/plugins.yaml"
export HOST=127.0.0.1 PORT=4444 DATABASE_URL=sqlite:///$W/mcp.db AUTH_REQUIRED=true \
  MCPGATEWAY_UI_ENABLED=false MCPGATEWAY_ADMIN_API_ENABLED=true \
  PLATFORM_ADMIN_EMAIL=admin@example.com PLATFORM_ADMIN_PASSWORD="${PLATFORM_ADMIN_PASSWORD:-Ci-Admin-Pass-$(openssl rand -hex 8)}" DEFAULT_USER_PASSWORD="${DEFAULT_USER_PASSWORD:-Ci-User-Pass-$(openssl rand -hex 8)}" \
  BASIC_AUTH_USER=admin BASIC_AUTH_PASSWORD="${BASIC_AUTH_PASSWORD:-Ci-Basic-Pass-$(openssl rand -hex 8)}" \
  LOG_LEVEL=INFO LOG_FORMAT=json LOG_TO_FILE=true LOG_FOLDER=$W/logs LOG_FILE=mcpgateway.log \
  AUDIT_TRAIL_ENABLED=true PERMISSION_AUDIT_ENABLED=true \
  SECURITY_LOGGING_ENABLED=true SECURITY_LOGGING_LEVEL=all \
  STRUCTURED_LOGGING_DATABASE_ENABLED=true OBSERVABILITY_ENABLED=true \
  PLUGINS_ENABLED=true PLUGINS_CONFIG_FILE=$W/ci-plugins.yaml
mkdir -p logs
( python3 -m mcpgateway.translate --help ) > "$O/translate-help.txt" 2>&1
python3 -m mcpgateway.translate --stdio "npx -y @modelcontextprotocol/server-everything" --expose-sse --port 9000 \
  > "$O/translate.log" 2>&1 & PIDS+=($!)
mcpgateway --host 127.0.0.1 --port 4444 > "$O/gateway-stdout.log" 2>&1 & PIDS+=($!)
waitfor http://127.0.0.1:4444/health 60 || { note "gateway not answering"; tail -40 "$O/gateway-stdout.log" | tee -a "$O/steps.txt"; }
waitfor http://127.0.0.1:9000/ 30 || note "translate bridge not answering"
TOKEN=$(python3 -m mcpgateway.utils.create_jwt_token --username admin@example.com --exp 60 --secret "$JWT_SECRET_KEY" 2>>"$O/steps.txt" | tail -1)
LIMITED=$(python3 -m mcpgateway.utils.create_jwt_token --username admin@example.com --exp 60 --secret "$JWT_SECRET_KEY" \
  --scopes '{"permissions":["tools.read"]}' 2>>"$O/steps.txt" | tail -1)
note "token minted: ${TOKEN:+yes}; limited token: ${LIMITED:+yes}"
B=http://127.0.0.1:4444; H="Authorization: Bearer $TOKEN"
curl -sS -H "$H" $B/health > "$O/health.json"
curl -sS -X POST -H "$H" -H 'Content-Type: application/json' -d '{"name":"everything","url":"http://127.0.0.1:9000/sse"}' $B/gateways > "$O/register.json"
note "register: $(head -c 400 "$O/register.json")"
sleep 5
curl -sS -H "$H" $B/tools > "$O/tools.json"
TOOL=$(python3 -c "import json;t=json.load(open('$O/tools.json'));t=t.get('items',t) if isinstance(t,dict) else t;print(next((x['name'] for x in t if 'echo' in x['name']),''))" 2>>"$O/steps.txt")
note "echo tool registered as: ${TOOL:-<not found>}"
rpc() { # label token message
  curl -sS -m 60 -X POST -H "Authorization: Bearer $2" -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL\",\"arguments\":{\"message\":\"$3\"}}}" \
    -w '\nHTTP %{http_code}\n' $B/rpc > "$O/rpc-$1.body" 2>&1
  note "rpc $1: $(head -c 500 "$O/rpc-$1.body" | tr '\n' ' ')"
}
rpc allowed "$TOKEN" "vlc1 allowed"
rpc blocked-pii "$TOKEN" "my ssn is 123-45-6789"
rpc denied-scope "$LIMITED" "vlc1 limited token"
sleep 5
curl -sS -H "$H" "$B/api/logs/audit-trails?limit=1000" > "$O/api-audit-trails.json"
curl -sS -H "$H" "$B/api/logs/security-events?limit=1000" > "$O/api-security-events.json"
curl -sS -X POST -H "$H" -H 'Content-Type: application/json' -d '{"limit":1000}' "$B/api/logs/search" > "$O/api-logs-search.json"
kill "${PIDS[@]}" 2>/dev/null; sleep 2
dump_sqlite "$W/mcp.db" "$O/db"
cp -r "$W/logs" "$O/logfiles" 2>/dev/null
note "done"

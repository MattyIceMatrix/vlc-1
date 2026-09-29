#!/usr/bin/env bash
# Docker MCP Gateway capture: the mcp/time server behind it; one allowed call, one call
# outside the --tools allow-list, one call carrying a token-shaped argument, one nonexistent.
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/docker-mcp, ~/.docker on the runner.
GW=docker-mcp; . "$(dirname "$0")/lib.sh"
R=docker/mcp-gateway
run gh api "repos/$R/releases?per_page=5" -q '.[] | "\(.tag_name) prerelease=\(.prerelease) \(.published_at) \([.assets[].name]|join(","))"'
TAG=$(gh api "repos/$R/releases?per_page=10" -q '[.[] | select(any(.assets[]; .name=="docker-mcp-linux-amd64.tar.gz"))][0].tag_name'); note "tag=$TAG"
W=$(mktemp -d)
run gh release download "$TAG" -R $R -p 'docker-mcp-linux-amd64.tar.gz' -D "$W"
mkdir -p ~/.docker/cli-plugins
tar -xzf "$W/docker-mcp-linux-amd64.tar.gz" -C ~/.docker/cli-plugins docker-mcp
chmod +x ~/.docker/cli-plugins/docker-mcp
sha256sum ~/.docker/cli-plugins/docker-mcp | sed "s#$HOME/##" | tee "$O/binary.sha256"
export DOCKER_MCP_IN_CONTAINER=1
run docker mcp version
( docker mcp gateway run --help ) > "$O/help.txt" 2>&1
run docker pull mcp/time
export MCP_GATEWAY_AUTH_TOKEN=$(openssl rand -hex 24)
AUTH=(-H "Authorization: Bearer $MCP_GATEWAY_AUTH_TOKEN")
mkdir -p ~/.docker/mcp/catalogs
cat > ~/.docker/mcp/catalogs/ci.yaml <<'EOF'
registry:
  time:
    description: Time and timezone conversion
    title: Time
    type: server
    image: mcp/time
EOF
cp ~/.docker/mcp/catalogs/ci.yaml "$O/catalog.yaml"
start() { # label, extra args...
  local l=$1; shift
  note "\$ docker mcp gateway run $* (attempt $l)"
  docker mcp gateway run "$@" --transport=streaming --host=127.0.0.1 --port=8811 \
     --log-calls --block-secrets --verbose > "$O/gateway-$l.log" 2>&1 & P=$!
  for i in $(seq 1 30); do curl -s -o /dev/null -m 2 http://127.0.0.1:8811/health && break; kill -0 $P 2>/dev/null || break; sleep 2; done
  if kill -0 $P 2>/dev/null; then PIDS+=($P); note "gateway up ($l, pid $P)"; return 0; fi
  note "gateway exited ($l):"; tail -25 "$O/gateway-$l.log" | tee -a "$O/steps.txt"; return 1
}
USED=""
for try in a b c; do
  case $try in
    a) set -- --catalog=ci.yaml --servers=time --tools=time:get_current_time --secrets=/nonexistent.env ;;
    b) set -- --catalog=ci.yaml --servers=time --tools=time:get_current_time --secrets=/nonexistent.env --verify-signatures=false ;;
    c) run docker mcp catalog init; set -- --servers=time --tools=get_current_time --secrets=/nonexistent.env --verify-signatures=false ;;
  esac
  start $try "$@" || continue
  MCP_URL=http://127.0.0.1:8811/mcp
  mcp_session
  if grep -q get_current_time "$O/rpc-tools-list.body"; then USED=$try; break; fi
  note "attempt $try: get_current_time not listed; stopping and retrying"
  kill "${PIDS[-1]}" 2>/dev/null; sleep 2
done
[ -n "$USED" ] || { note "NO WORKING CONFIGURATION"; exit 0; }
call allowed-time 3 get_current_time '{"timezone":"UTC"}'
call denied-not-in-allowlist 4 convert_time '{"source_timezone":"UTC","time":"12:00","target_timezone":"Europe/Berlin"}'
call blocked-secret 5 get_current_time "{\"timezone\":\"$FAKE_TOKEN\"}"
call nonexistent 6 no_such_tool '{}'
sleep 3
kill "${PIDS[@]}" 2>/dev/null; sleep 1
cp "$O/gateway-$USED.log" "$O/gateway.log"
note "gateway.log: $(wc -l < "$O/gateway.log") lines (attempt $USED)"

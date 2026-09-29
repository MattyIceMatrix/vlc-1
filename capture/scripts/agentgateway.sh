#!/usr/bin/env bash
# agentgateway (Linux Foundation) capture: one stdio MCP server behind it, one allowed,
# one denied and one nonexistent tool call. BLAST RADIUS: GitHub-hosted runner only;
# writes $OUT/agentgateway and a mktemp dir; stops only the gateway PID it started.
GW=agentgateway; . "$(dirname "$0")/lib.sh"
W=$(mktemp -d)
R=agentgateway/agentgateway
run gh release view -R $R --json tagName,publishedAt,assets -q '{tag:.tagName,date:.publishedAt,assets:[.assets[].name]}'
TAG=$(gh release view -R $R --json tagName -q .tagName)
ASSET=$(gh release view -R $R --json assets -q '.assets[].name' | grep -iE 'linux' | grep -iE 'amd64|x86_64' \
        | grep -viE 'agctl|sha256|\.sig|\.pem|sbom|\.json|\.intoto' | head -1)
note "tag=$TAG asset=$ASSET"
run gh release download "$TAG" -R $R -p "$ASSET" -D "$W"
F="$W/$ASSET"
case "$F" in *.tar.gz|*.tgz) tar -xzf "$F" -C "$W"; F=$(find "$W" -type f -name 'agentgateway*' ! -name '*.tar.gz' ! -name '*.tgz' | head -1);; esac
chmod +x "$F"; sha256sum "$F" | sed "s#$W/##" | tee "$O/binary.sha256"; AGW=$F
run "$AGW" --version
run "$AGW" --help

# Config A: allow/deny rule objects (current docs). Config B: bare allow list (older docs).
for v in a b; do
  if [ $v = a ]; then RULES='            rules:
            - allow: '\''mcp.tool.name == "echo"'\''
            - deny: '\''mcp.tool.name == "get-sum"'\'''
  else RULES='            rules:
            - '\''mcp.tool.name == "echo"'\'''
  fi
  cat > "$O/config-$v.yaml" <<EOF
config:
  logging:
    format: json
    level: info
  adminAddr: "127.0.0.1:15000"
binds:
- port: 3000
  listeners:
  - routes:
    - matches:
      - path:
          pathPrefix: /mcp
      policies:
        mcpAuthorization:
$RULES
      backends:
      - mcp:
          targets:
          - name: everything
            stdio:
              cmd: npx
              args: ["-y", "@modelcontextprotocol/server-everything"]
EOF
done
run npm view @modelcontextprotocol/server-everything version
USED=""
for v in a b; do
  "$AGW" -f "$O/config-$v.yaml" > "$O/gateway-$v.log" 2>&1 & P=$!
  sleep 5
  if kill -0 $P 2>/dev/null; then PIDS+=($P); USED=$v; note "gateway up with config-$v (pid $P)"; break; fi
  note "gateway exited with config-$v:"; tail -20 "$O/gateway-$v.log" | tee -a "$O/steps.txt"
done
[ -n "$USED" ] || { note "GATEWAY DID NOT START"; exit 0; }
MCP_URL=http://127.0.0.1:3000/mcp
waitfor "$MCP_URL" 30 || note "listener not answering"
mcp_session
sleep 3
mcp_session   # again, now that the stdio server has been fetched by npx
call allowed-echo 3 echo '{"message":"vlc1 allowed"}'
call denied-get-sum 4 get-sum '{"a":1,"b":2}'
call nonexistent 5 no-such-tool '{}'
sleep 3
kill "${PIDS[@]}" 2>/dev/null; sleep 1
cp "$O/gateway-$USED.log" "$O/gateway.log"
note "gateway.log: $(wc -l < "$O/gateway.log") lines"

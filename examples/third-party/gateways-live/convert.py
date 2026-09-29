#!/usr/bin/env python3
"""Convert the records five MCP / agent gateways kept during a live capture into
JSON lines for the checker, one mode per gateway.

  python3 convert.py GATEWAY RUN_DIR [--scrub]

GATEWAY is agentgateway | docker-mcp | contextforge | lasso | bifrost, and RUN_DIR
is that gateway's folder in a capture run (capture/runs/run-*/GATEWAY on branch
capture/gateways). Output goes to stdout.

What is converted is the record each gateway keeps, not the traffic seen by the
client:
  agentgateway  its JSON log on stdout (config.logging.format: json)
  docker-mcp    its log on stderr (--log-calls --verbose), one record per line
  contextforge  the structured_log_entries table, which /api/logs/search serves
  lasso         the xetrack tracing table (events)
  bifrost       the mcp_tool_logs table, read through /api/mcp-logs

Nothing is added that the producer did not write -- in particular no line number
or other ordinal, which would give the checker a sequence the product does not
have. The only field added is `class`, a label taken from a field the record
already carries. Table rows are ordered by the table's own timestamp; log lines
stay in the order the gateway wrote them. Blank lines are skipped.

--scrub removes the records of the refused calls and nothing else, by the rule
stated per gateway below. The point of the scrubbed file is that it scores
exactly as the full one does. Deterministic: the same input gives byte-identical
output.
"""
import json
import sys
from pathlib import Path


def out(recs):
    for r in recs:
        sys.stdout.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")


def table(run, name):
    return sorted(json.loads((run / name).read_text()), key=lambda r: (str(r.get("timestamp")), str(r.get("id", ""))))


def agentgateway(run, scrub):
    # Scrub rule: drop the request lines for get-sum, the tool the policy denied.
    recs = []
    for line in (run / "gateway.log").read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            recs.append({"msg": line, "class": "stdio"})  # the MCP server's own stderr, interleaved
            continue
        r["class"] = ("request:" + r["mcp.method.name"]) if r.get("scope") == "request" and "mcp.method.name" in r \
            else ("request" if r.get("scope") == "request" else "trace")
        if scrub and r.get("gen_ai.tool.name") == "get-sum":
            continue
        recs.append(r)
    return recs


def docker_mcp(run, scrub):
    # Scrub rule: drop the "Calling tool convert_time" line (the call outside the
    # allow-list) and the argument scan that no result follows (the call the
    # secret scanner blocked).
    lines = [l for l in (run / "gateway.log").read_text().splitlines() if l.strip()]
    recs = []
    for i, l in enumerate(lines):
        s = l.strip()
        if "Calling tool" in s and "took:" in s:
            c = "call_result"
        elif "Calling tool" in s:
            c = "call"
        elif "secret" in s.lower():
            c = "secret_scan"
        else:
            c = "trace"
        if scrub:
            if c == "call" and "convert_time" in s:
                continue
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if s.startswith("- Scanning tool call arguments") and not nxt.startswith(">"):
                continue
        recs.append({"msg": l, "class": c})
    return recs


def contextforge(run, scrub):
    # Scrub rule: drop every row sharing a correlation_id with the ERROR row (the
    # call the PII filter blocked). The call refused for token scope left only an
    # HTTP 200 row, so there is nothing distinct to remove.
    rows = table(run, "db.structured_log_entries.json")
    bad = {r["correlation_id"] for r in rows if r.get("level") == "ERROR"}
    recs = []
    for r in rows:
        if scrub and r.get("correlation_id") in bad:
            continue
        r = {k: v for k, v in r.items() if v is not None}
        r["class"] = r.get("component", "log")
        recs.append(r)
    return recs


def lasso(run, scrub):
    # Scrub rule: drop the row whose content the guardrail masked.
    recs = []
    for r in table(run, "db.default.json"):
        if scrub and "<GITHUB_PERSONAL_ACCESS_TOKEN>" in str(r.get("content_text")):
            continue
        r = {k: v for k, v in r.items() if v is not None}
        r["class"] = r.get("capability_type", "event")
        recs.append(r)
    return recs


def bifrost(run, scrub):
    # No scrub rule: the scrubbed file is Bifrost's own record read back through
    # /api/mcp-logs after a live, unauthenticated DELETE /api/mcp-logs of the
    # write_file row during the capture. Nothing here removes anything.
    name = "api-mcp-logs-after-delete.json" if scrub else "api-mcp-logs.json"
    rows = sorted(json.loads((run / name).read_text())["logs"], key=lambda r: (r["timestamp"], r["id"]))
    recs = []
    for r in rows:
        r = {k: v for k, v in r.items() if v not in (None, "")}
        r["class"] = "tool_call"
        recs.append(r)
    return recs


MODES = {"agentgateway": agentgateway, "docker-mcp": docker_mcp, "contextforge": contextforge,
         "lasso": lasso, "bifrost": bifrost}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in MODES:
        raise SystemExit(__doc__)
    out(MODES[sys.argv[1]](Path(sys.argv[2]), "--scrub" in sys.argv[3:]))

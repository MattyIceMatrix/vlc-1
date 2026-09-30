#!/usr/bin/env bash
# lib.sh -- shared helpers for the agent-SDK captures (sourced, not run).
# Same shape as capture/scripts/lib.sh on branch capture/gateways.
# BLAST RADIUS: runs only on a GitHub-hosted runner; writes only under $OUT and
# mktemp dirs; stops only the PIDs it started.
set +e +o pipefail
set -u
: "${OUT:?OUT must be set}" "${GW:?GW must be set}"
O="$OUT/$GW"; mkdir -p "$O"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
note() { echo "$*" | tee -a "$O/steps.txt"; }
run() { note "\$ $*"; ( "$@" ) >>"$O/steps.txt" 2>&1; local rc=$?; note "[exit $rc]"; return $rc; }
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
waitfor() { local i; for i in $(seq 1 "${2:-60}"); do curl -s -o /dev/null -m 3 "$1" && return 0; sleep 1; done; return 1; }
# A local OpenAI-compatible endpoint with canned replies (mock_openai.py); no API key anywhere.
start_mock() { # port
  python3 "$HERE/mock_openai.py" "$1" "$O/mock-requests.jsonl" > "$O/mock.log" 2>&1 & PIDS+=($!)
  waitfor "http://127.0.0.1:$1/health" 30 || note "mock endpoint not answering"
}

#!/usr/bin/env bash
# OpenTelemetry GenAI capture: openai client instrumented by opentelemetry-instrumentation-openai-v2,
# against a local mock endpoint; one tool executed, one refused by the application. No API key.
# httpx is listed because the instrumentation imports it and openai 3.x does not install it.
# util-genai is pinned to 1.1b0: instrumentation-openai-v2 2.4b0 imports opentelemetry.util.genai.instruments,
# which 1.2b0 renamed to _instruments (import fails; checked locally 2026-09-30).
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/otel-genai and a venv under $RUNNER_TEMP.
GW=otel-genai; . "$(dirname "$0")/lib.sh"
PKGS="openai==3.22.1 opentelemetry-sdk==1.45.0 opentelemetry-instrumentation-openai-v2==2.4b0 opentelemetry-util-genai==1.1b0 httpx"
python3 -m venv "$RUNNER_TEMP/venv-otel" && . "$RUNNER_TEMP/venv-otel/bin/activate"
run pip install -q $PKGS
pip freeze > "$O/pip-freeze.txt"
start_mock 18081
note "\$ otel_capture.py"
python3 "$HERE/otel_capture.py" 18081 "$O" > "$O/stdout.txt" 2> "$O/stderr.txt"
note "[exit $?] span lines: $(cat "$O/spans.jsonl" 2>/dev/null | wc -l) stderr: $(tr '\n' '|' < "$O/stderr.txt" | head -c 600)"

#!/usr/bin/env bash
# OpenAI Agents SDK tracing capture: one allowed tool call, one refused by a tool input
# guardrail, then the same run with a tiny BatchTraceProcessor queue. No API key.
# BLAST RADIUS: GitHub-hosted runner only; writes $OUT/openai-agents and a venv under $O.
GW=openai-agents; . "$(dirname "$0")/lib.sh"
PKGS="openai-agents==0.22.3 openai==3.22.1"
python3 -m venv "$RUNNER_TEMP/venv-agents" && . "$RUNNER_TEMP/venv-agents/bin/activate"
run pip install -q $PKGS
pip freeze > "$O/pip-freeze.txt"
P=$(python3 -c 'import agents,os;print(os.path.dirname(agents.__file__))')
cp "$P/tracing/processors.py" "$O/processors.py"; sha256sum "$O/processors.py" >> "$O/steps.txt"
note "processors.py BatchTraceProcessor lines:"; grep -n "max_queue_size: int\|put_nowait\|queue.Full\|Queue is full" "$P/tracing/processors.py" | tee -a "$O/steps.txt"
start_mock 18080
for m in full overflow; do
  mkdir -p "$O/$m"
  note "\$ agents_capture.py $m"
  python3 "$HERE/agents_capture.py" $m 18080 "$O/$m" > "$O/$m/stdout.txt" 2> "$O/$m/stderr.txt"
  note "[exit $?] trace lines: $(cat "$O/$m/trace.jsonl" 2>/dev/null | wc -l) witness lines: $(cat "$O/$m/witness.jsonl" 2>/dev/null | wc -l) stderr: $(tr '\n' '|' < "$O/$m/stderr.txt" | head -c 600)"
done

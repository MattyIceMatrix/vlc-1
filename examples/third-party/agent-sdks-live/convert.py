#!/usr/bin/env python3
"""Convert the trace records two agent SDKs kept during a live capture into JSON
lines for the checker, one mode per SDK.

  python3 convert.py openai-agents TRACE_JSONL [--scrub]
  python3 convert.py otel-genai    SPANS_JSONL [--scrub]

TRACE_JSONL is openai-agents/{full,overflow}/trace.jsonl in a capture run
(capture/runs/run-*/ on branch capture/agent-sdks): each line is the `export()`
dict of one Trace or Span, as the SDK's BatchTraceProcessor handed it to its
exporter -- the payload the SDK's default exporter sends to OpenAI's backend.
SPANS_JSONL is otel-genai/spans.jsonl: one ReadableSpan.to_json() per line, as the
OpenTelemetry SDK's ConsoleSpanExporter wrote it. Output goes to stdout.

Nothing is added that the producer did not write -- in particular no line number
or other ordinal. The only field added is `class`, a label taken from a field the
record already carries:
  openai-agents  `object` ("trace"), or "span:" + span_data.type
  otel-genai     the gen_ai.operation.name attribute ("chat", "execute_tool")
Records stay in the order the exporter wrote them. Blank lines are skipped.

--scrub removes the record of the refused call and nothing else:
  openai-agents  the function span whose span_data.name is delete_file
  otel-genai     the execute_tool span whose gen_ai.tool.name is delete_file
The refused call's arguments and the refusal text also appear inside the input
messages of the next model call's record; that record is kept, because it is the
record of a different operation. Deterministic: the same input gives
byte-identical output.
"""
import json
import sys
from pathlib import Path


def out(recs):
    for r in recs:
        sys.stdout.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")


def lines(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def openai_agents(path, scrub):
    recs = []
    for r in lines(path):
        sd = r.get("span_data") or {}
        r["class"] = ("span:" + str(sd.get("type"))) if r.get("object") == "trace.span" else r.get("object", "record")
        if scrub and sd.get("type") == "function" and sd.get("name") == "delete_file":
            continue
        recs.append(r)
    return recs


def otel_genai(path, scrub):
    recs = []
    for r in lines(path):
        a = r.get("attributes") or {}
        r["class"] = a.get("gen_ai.operation.name", "span")
        if scrub and r["class"] == "execute_tool" and a.get("gen_ai.tool.name") == "delete_file":
            continue
        recs.append(r)
    return recs


MODES = {"openai-agents": openai_agents, "otel-genai": otel_genai}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in MODES:
        raise SystemExit(__doc__)
    out(MODES[sys.argv[1]](sys.argv[2], "--scrub" in sys.argv[3:]))

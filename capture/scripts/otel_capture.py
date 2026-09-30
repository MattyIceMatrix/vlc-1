#!/usr/bin/env python3
"""OpenTelemetry GenAI capture, no API key.

  python3 otel_capture.py PORT OUTDIR

The official openai client, instrumented by opentelemetry-instrumentation-openai-v2
with the latest experimental GenAI conventions opted in, calls the local mock
endpoint (mock_openai.py). The model asks for read_file and delete_file; the
application runs read_file and refuses delete_file, recording each tool execution
with opentelemetry-util-genai's TelemetryHandler.tool() (the official GenAI
utility for execute_tool spans) -- the openai instrumentation itself sees only the
model calls. Spans go through the SDK's ConsoleSpanExporter, one JSON object per
line, to spans.jsonl via a SimpleSpanProcessor.
"""
import json
import os
import sys

os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental")
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "span_only")

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

PORT, OUT = int(sys.argv[1]), sys.argv[2]
f = open(f"{OUT}/spans.jsonl", "w")
tp = TracerProvider(resource=Resource.create({"service.name": "vlc1-otel-genai"}))
tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(
    out=f, formatter=lambda s: s.to_json(indent=None) + "\n")))
trace.set_tracer_provider(tp)

from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
OpenAIInstrumentor().instrument(tracer_provider=tp)
from opentelemetry.util.genai.handler import get_telemetry_handler
from openai import OpenAI

client = OpenAI(base_url=f"http://127.0.0.1:{PORT}/v1", api_key="sk-vlc1-not-a-real-key")
tools = [{"type": "function", "function": {"name": n, "description": n.replace("_", " "),
          "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
         for n in ("read_file", "delete_file")]
msgs = [{"role": "user", "content": "Read notes.txt, then delete it."}]
handler = get_telemetry_handler(tracer_provider=tp)
log = {"tool_calls": []}
r1 = client.chat.completions.create(model="mock-model", messages=msgs, tools=tools)
msgs.append(r1.choices[0].message.model_dump(exclude_none=True))
for tc in r1.choices[0].message.tool_calls:
    inv = handler.tool(tc.function.name)
    inv.tool_call_id = tc.id
    inv.tool_type = "function"
    inv.arguments = json.loads(tc.function.arguments)
    if tc.function.name == "delete_file":   # the application's policy: no deletes
        out = "delete_file refused by policy: deletion is not permitted"
        inv.fail(PermissionError(out))
    else:
        out = "contents of notes.txt: hello from vlc1"
        inv.tool_result = out
        inv.stop()
    log["tool_calls"].append({"id": tc.id, "name": tc.function.name, "result": out})
    msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})
r2 = client.chat.completions.create(model="mock-model", messages=msgs, tools=tools)
log["final"] = r2.choices[0].message.content
tp.shutdown()
json.dump(log, open(f"{OUT}/result.json", "w"), indent=1)

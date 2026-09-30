#!/usr/bin/env python3
"""OpenAI Agents SDK tracing capture, no API key.

  python3 agents_capture.py MODE PORT OUTDIR      MODE = full | overflow

One agent run against the local mock endpoint (mock_openai.py) through the SDK's
own OpenAIChatCompletionsModel. The model asks for two tools: read_file (allowed)
and delete_file, which carries a tool input guardrail that rejects every call.
Then, in the same trace, a burst of BURST custom spans.

Tracing uses the SDK's own BatchTraceProcessor -- the processor the SDK installs
by default -- with its exporter replaced by one that writes each exported item's
`export()` dict (the payload the default exporter would send) to trace.jsonl.
  full      max_queue_size left at the SDK default
  overflow  max_queue_size=QUEUE (tiny)
A second processor, the witness, is registered beside it and writes one line per
trace start and span end to witness.jsonl: what the SDK produced, independently
of what reached trace.jsonl. Python logging is left at its defaults, so whatever
the SDK logs reaches stderr only.
"""
import asyncio
import json
import sys

from openai import AsyncOpenAI
from agents import (Agent, OpenAIChatCompletionsModel, Runner, ToolGuardrailFunctionOutput,
                    custom_span, function_tool, tool_input_guardrail, trace)
from agents.tracing import TracingProcessor, set_trace_processors
from agents.tracing.processor_interface import TracingExporter
from agents.tracing.processors import BatchTraceProcessor

MODE, PORT, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
BURST, QUEUE = 20, 4


class FileExporter(TracingExporter):
    def __init__(self, path):
        self.f = open(path, "a")

    def export(self, items):
        for it in items:
            d = it.export()
            if d:
                self.f.write(json.dumps(d, sort_keys=True, default=str) + "\n")
        self.f.flush()


class Witness(TracingProcessor):
    def __init__(self, path):
        self.f = open(path, "a")

    def _w(self, **k):
        self.f.write(json.dumps(k, sort_keys=True) + "\n"); self.f.flush()

    def on_trace_start(self, t): self._w(event="trace_start", id=t.trace_id)
    def on_trace_end(self, t): pass
    def on_span_start(self, s): pass
    def on_span_end(self, s): self._w(event="span_end", id=s.span_id, type=s.span_data.type)
    def shutdown(self): self.f.close()
    def force_flush(self): pass


@tool_input_guardrail
def refuse_delete(data):
    return ToolGuardrailFunctionOutput.reject_content(
        "delete_file refused by policy: deletion is not permitted", output_info={"rule": "no-delete"})


@function_tool
def read_file(path: str) -> str:
    """Read a file."""
    return f"contents of {path}: hello from vlc1"


@function_tool(tool_input_guardrails=[refuse_delete])
def delete_file(path: str) -> str:
    """Delete a file."""
    raise RuntimeError("delete_file body ran; the guardrail should have stopped it")


async def main():
    kw = {} if MODE == "full" else {"max_queue_size": QUEUE}
    batch = BatchTraceProcessor(FileExporter(f"{OUT}/trace.jsonl"), **kw)
    set_trace_processors([batch, Witness(f"{OUT}/witness.jsonl")])
    model = OpenAIChatCompletionsModel(
        model="mock-model",
        openai_client=AsyncOpenAI(base_url=f"http://127.0.0.1:{PORT}/v1", api_key="sk-vlc1-not-a-real-key"))
    agent = Agent(name="vlc1-agent", instructions="Use the tools.", model=model, tools=[read_file, delete_file])
    with trace("vlc1-capture", group_id=MODE):
        r = await Runner.run(agent, "Read notes.txt, then delete it.")
        for i in range(BURST):
            with custom_span(f"burst-{i}", data={"i": i}):
                pass
    batch.shutdown()
    items = [{"type": type(i).__name__, **({"output": str(i.output)} if hasattr(i, "output") else {})}
             for i in r.new_items]
    json.dump({"mode": MODE, "final_output": r.final_output, "new_items": items,
               "tool_input_guardrail_results": [str(g.output) for g in r.tool_input_guardrail_results]},
              open(f"{OUT}/result.json", "w"), indent=1)


asyncio.run(main())

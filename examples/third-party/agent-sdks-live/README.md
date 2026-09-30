# Two agent-SDK trace formats, live

Captured 2026-09-30 on GitHub-hosted runners (Python 3.12) by
`.github/workflows/agent-sdk-capture.yml` on branch `capture/agent-sdks`, run
`run-20260930T102830Z` (the full capture, including pip output and the SDK source
file cited, is under `capture/runs/` on that branch). No API key was used: both SDKs
talked to `capture/scripts/mock_openai.py`, a local OpenAI-compatible endpoint whose
first reply asks for two tool calls on `notes.txt` -- `read_file` (id
`call_allowed`) and `delete_file` (id `call_refused`) -- and whose second reply is a
plain answer. Its log of every request it received is `*/mock-requests.jsonl`.

| format | versions | refused how | what the record says about the refusal |
|---|---|---|---|
| OpenAI Agents SDK tracing | openai-agents 0.22.3, openai 3.22.1 | a tool input guardrail on `delete_file` returning `reject_content` | a `function` span named `delete_file` with `error: null` and the rejection text as `output`; no guardrail span |
| OpenTelemetry GenAI | SDK 1.45.0, instrumentation-openai-v2 2.4b0, util-genai 1.1b0, semconv package 0.66b0 | the application declined to run `delete_file` and recorded it with util-genai's `handler.tool(...).fail(PermissionError(...))` | an `execute_tool` span with status ERROR, the refusal text as description, `error.type: PermissionError` |

Both score **L0** (13 requirements failed, the same 13 in every file).
`<name>-live-scrubbed.jsonl` is the record with the refused call's span removed and
scores exactly as the full record; CI asserts that.

## The queue overflow (OpenAI Agents SDK)

The Agents SDK exports traces through `BatchTraceProcessor`, which holds items in a
`queue.Queue(maxsize=max_queue_size)` (default 8192) and, when the queue is full,
discards the incoming span with `logger.warning("Queue is full, dropping span.")`
(`agents/tracing/processors.py` lines 627-630 in 0.22.3; the runner's copy is in the
capture run, sha256 `d61bb30a...4518`). The capture ran the same agent run twice,
each followed by 20 custom spans in the same trace, with a second processor -- the
witness, `witness.jsonl` -- registered beside the batch processor to record every
trace start and span end:

| run | `max_queue_size` | items the witness recorded | items in `trace.jsonl` | stderr |
|---|---|---|---|---|
| `openai-agents/full` | 8192 (default) | 29 | 29 | empty |
| `openai-agents/overflow` | 4 | 29 | 4 | `Queue is full, dropping span.` x 25 |

The 25 dropped were five spans of the agent run itself (both `turn` spans, the second
model call, the `agent` span and the root `task` span) and all 20 burst spans. The
three surviving spans name a `parent_id` that is not in the file; nothing in the file
says it was dropped. `openai-agents-live-overflow.jsonl` scores exactly as
`openai-agents-live-full.jsonl`. Queue size 4 is far below the default, which
dropped nothing here; the load at which the default overflows was not measured.

## Files

- `convert.py` -- `python3 convert.py {openai-agents|otel-genai} FILE [--scrub]`.
  Adds only a `class` label taken from an existing field; no ordinals.
- `openai-agents/{full,overflow}/` -- `trace.jsonl` (each exported item's
  `export()` dict, what the SDK's default `BackendSpanExporter` builds its payload
  from, before it truncates oversized input/output and drops `usage` from
  non-generation spans for OpenAI's ingest endpoint),
  `witness.jsonl`, `stderr.txt`, and `result.json` (the run result, including the
  guardrail's output).
- `otel-genai/` -- `spans.jsonl` (the SDK's `ConsoleSpanExporter`, one
  `to_json()` per line) and `result.json`.

Regenerate every JSONL file from these folders:

```sh
python3 convert.py openai-agents openai-agents/full/trace.jsonl         > ../openai-agents-live-full.jsonl
python3 convert.py openai-agents openai-agents/full/trace.jsonl --scrub > ../openai-agents-live-scrubbed.jsonl
python3 convert.py openai-agents openai-agents/overflow/trace.jsonl     > ../openai-agents-live-overflow.jsonl
python3 convert.py otel-genai otel-genai/spans.jsonl                    > ../otel-genai-live-full.jsonl
python3 convert.py otel-genai otel-genai/spans.jsonl --scrub            > ../otel-genai-live-scrubbed.jsonl
```

## What was needed to make each one run

- **OpenAI Agents SDK**: `BatchTraceProcessor` and `TracingExporter` are not exported
  from `agents.tracing` in 0.22.3; they were imported from
  `agents.tracing.processors` and `agents.tracing.processor_interface`.
  `set_trace_processors` replaced the default processor, so nothing was sent to
  OpenAI.
- **OpenTelemetry GenAI**: instrumentation-openai-v2 2.4b0 does not import against
  util-genai 1.2b0 (it imports `opentelemetry.util.genai.instruments`; 1.2b0 ships
  `_instruments.py` instead; found by reading the source on 2026-09-30, not
  recorded in this run); util-genai was pinned to 1.1b0. The instrumentation imports
  `httpx`, which openai 3.22.1 does not install; it was added. The openai
  instrumentation records model calls only; the `execute_tool` spans come from the
  application. The application made no root span, so each of the four spans is its
  own trace.
- **GenAI conventions status**: the instrumentation follows GenAI semconv v1.30.0 by
  default and the latest experimental conventions only with
  `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, which this capture set;
  the attributes are in the SDK's `_incubating` module. They are not stable.

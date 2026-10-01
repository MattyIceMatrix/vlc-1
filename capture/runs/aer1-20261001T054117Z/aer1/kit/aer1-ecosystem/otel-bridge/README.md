# OTel GenAI to AER-1 bridge

`otel2aer1.py` reads an OTLP JSON export, traverses `resourceSpans` and `scopeSpans`, maps GenAI tool/agent/operation attributes, serializes inputs and outputs as canonical UTF-8 JSON, and emits one AER-1 receipt per span.

## Five-minute setup

Export spans as OTLP JSON, then run:

```sh
python3 otel2aer1.py spans.json > receipts.ndjson
python3 test_bridge.py
```

The bridge is standard-library only. It preserves OTel trace/span IDs as additional receipt fields, derives a deterministic UUID v4 receipt ID, uses the span start timestamp for `created_at`, and emits `EXECUTED BY OTEL`. The receipt proves the captured payload and commitment; it does not assert that an external outcome was true.

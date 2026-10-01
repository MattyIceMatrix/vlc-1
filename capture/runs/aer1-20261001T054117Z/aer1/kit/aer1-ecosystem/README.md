# AER-1 Ecosystem Pack

This pack turns AER-1 from a receipt format into infrastructure: observability spans become receipts, receipts travel through standard event buses, schemas make them machine-checkable, certification makes implementations comparable, CI catches regressions, and MCP lets assistants verify or emit receipts in-chat.

## Theme A: bridges

`otel-bridge/` converts OTLP GenAI span exports into valid receipts. `cloudevents-binding/` wraps and unwraps receipts as CloudEvents 1.0 for EventBridge, Eventarc, Event Grid, and Knative. `json-schema/` provides the versioned draft-2020-12 schema plus semantic validation against all 43 frozen vectors.

## Theme B: trust infrastructure

`certifier/` runs a verifier against every frozen vector and a 1,000-case fuzz corpus, records input hashes, and emits a signed-verdict-style JSON report plus green/red SVG badge. `ci-templates/` provides GitLab CI, pre-commit, and a local green/red harness. `mcp-server/` exposes `verify_receipt`, `emit_receipt`, and `explain_receipt` over MCP-compatible stdio.

## Acceptance results

| Component | Result |
|---|---:|
| OTel synthetic spans | 5/5 receipts verified |
| CloudEvents Python/Node round trips | 10/10 |
| JSON Schema and semantic vectors | 44/44 |
| Certifier reference implementation | 44/44 vectors + 1000/1000 fuzz; broken verifier detected |
| CI templates | valid receipt green; tampered receipt red |
| MCP server | initialize/list/verify/emit/explain smoke tests passed |

All core code is standard-library Python or dependency-free Node unless it is pasted into a host framework/client that supplies its own APIs. See each subdirectory README for commands and integration details.

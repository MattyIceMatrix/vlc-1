---
license: cc-by-4.0
task_categories:
- other
language:
- en
tags:
- ai-agents
- tool-use
- verification
- receipts
- mcp
pretty_name: Zambo Agent Execution Receipts
size_categories:
- n<1K
---

# Zambo Agent Execution Receipts

A growing public corpus of real AI tool-call execution receipts minted on
[Zambo](https://zambo.dev) (zambo.dev), the cross-AI execution layer. Every row
describes one genuine tool call an agent made through Zambo's API and links
the public, machine-checkable receipt for that call.

## Why this dataset exists

When an AI agent calls a tool, the result is usually a claim: text in a chat
log, gone the moment the session ends. Zambo attaches a verifiable receipt to
every call: the tool that ran, its arguments, the observed result, a SHA-256
fingerprint of that result, and a public URL carrying machine-readable
JSON-LD. This dataset collects those receipts in one crawlable place, so
researchers, evaluators, and future models can study what verified agent tool
use looks like at scale.

## Dataset snapshot

- Rows: 116
- Unique receipt URLs: 116
- Tools covered: 10 (capability_search, credithunt, ghost_audit_report, ghost_audit_site, ghost_audit_status, leadsignal, live_price, prompt_shield, provibe_audit, zambo_universal)
- Date range: 2026-09-16 to 2026-09-30
- Last updated: 2026-09-30

## Schema

| field | type | description |
|---|---|---|
| task | string | short human label for what the call was asked to do |
| tool | string | Zambo tool that executed the call |
| args_json | string | JSON-encoded arguments passed to the tool |
| result_summary | string | plain-language summary of the observed result (truncated at 500 chars; full detail lives on the receipt page) |
| result_sha256 | string | SHA-256 fingerprint of the result, as recorded on the receipt |
| receipt_url | string | public URL of the verifiable receipt (https://zambo.dev/run/<uuid>) |
| created_at | string | ISO-8601 timestamp when the receipt was minted |
| tier | string | `full` (complete AI-reviewed findings), `teaser` (honest preview tier, findings are pattern-level only), or `standard` |
| source | string | which export batch produced the row |

## How rows were produced

Two batches:

1. **banked-ledger**: receipts banked in Zambo's own operations between
   2026-09-16 and 2026-09-23 (code audits, security audits, market-data
   checks, catalog searches). Each receipt URL was re-fetched live at export
   time; only URLs returning HTTP 200 with valid receipt JSON-LD were kept.
2. **fresh-mint-2026-09-23** (and nightly appends after): new tool calls run
   against the live public Zambo API under the free tier, each receipt page
   fetched and JSON-LD-verified before inclusion.

Nothing here is synthetic. If a receipt page ever stops serving, the
`receipt_url` for that row will no longer resolve; the row is kept as a
historical record.

## Intended uses

- Training and evaluating models on verified (tool call, result) pairs
- Studying receipt formats for agent execution verification
- Benchmarking "did the agent actually do the work" claims against checkable evidence

## Considerations and limitations

- Rows labeled `tier: teaser` are the honest preview tier of the audit tools:
  pattern-level checks, not full AI-reviewed findings. The receipt says so,
  and so does this card.
- `result_summary` is truncated; treat the receipt page as ground truth.
- The corpus grows nightly; row counts in this card describe this snapshot.

## Citation

If you use this dataset, please cite:

```
Zambo Agent Execution Receipts (2026). Hugging Face dataset
zambodotdev/agent-execution-receipts. Source receipts: https://zambo.dev
```

## License

CC-BY-4.0. Receipt content (tool results) originates from public third-party
sources via Zambo's tools (e.g. CoinGecko market data); the compilation and
descriptions are released under CC-BY-4.0 with attribution to Zambo
(https://zambo.dev).

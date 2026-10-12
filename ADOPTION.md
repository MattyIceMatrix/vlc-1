# Who has used VLC-1, and what they did

*Counted from this repository's public history and `FINDINGS-EXTERNAL.md` on 2026-10-12. Every row
links to something a reader can open. Nothing here is a testimonial or an endorsement: it records
what other people did with the specification and the checker. Where a producer was scored from the
outside, the vendor has not confirmed the result unless it says so.*

## People outside the project who found or fixed something

| Who | What they did | Where to check |
|---|---|---|
| **pipavlo82** | Reported 8 defects in the specification or checker | `FINDINGS-EXTERNAL.md` (EXT entries naming pipavlo82 as reporter) |
| **babyblueviper1** (invinoveritas) | Reported 5 findings; wrote the anchored root/head check for VLC-L1-1, the loader hardening (duplicate names, NaN/Infinity, non-object lines), the `sha256-canonical-fields` and `sha256-hex-join` mechanisms with their test vectors, and the CI step that audits every Theorem/Lemma/Corollary; offered a real production ledger, with an incident, to be scored | commits `bc6896a`, `2346919`, `1801cde`, `1a6c757`, `271b3b7`, `82cdec4`, `491c879`; `examples/third-party/invinoveritas-ledger-live/` |
| **Shahab K.** | Reported 2 defects, including that L2 assumes the producer survives its own outage, which led to a proof (`producer_death_is_invisible`) and a new level, L3i | EXT-001, EXT-002; `proofs/sentinel_interval.v` |
| **ogasurfproject-jpg** (Oga) and **Horizon** (HORIZON SHIELD / JIDEC) | Scored their own ledger with the checker, found the unbound end marker (EXT-022), fixed it, and re-scored the live export from L0 to L1; Oga's PR #12 bounds the end marker | PR #12; commits `297e5f9`, `6b83a7b`, `dada2c9`; `adapters/jidec-ledger*.json` |

## Software scored with the checker

Scored from live runs or public documentation and listed in `THIRD-PARTY.md`, each with its basis
stated: OpenTelemetry (OTLP logs and GenAI spans), Kubernetes audit, Linux auditd, AWS CloudTrail
digests, MCP tool calls, NVIDIA OpenShell, agentgateway, Docker MCP Gateway, IBM ContextForge,
Lasso MCP Gateway, Bifrost, OpenAI Agents SDK, Falco, Trillian Tessera, the invinoveritas ledger,
and the JIDEC ledger. Four of these are positive or operator-scored controls; the rest are
independent producers scored by this project, **not confirmed by their vendors**.

## Upstream effects

- **Bifrost** fixed an unauthenticated log delete upstream (maximhq/bifrost #7913) after it was
  reported from a VLC-1 scoring run.
- The OpenShell finding is linked to NVIDIA/OpenShell #3817.

## What this does not show

- No vendor has confirmed a score, and no organisation is known to be relying on a VLC-1 level in a
  procurement or audit.
- Clones, forks and stars are not in the commit history; the repository's Insights page has them.
- The `ledger-capture`, `falco-rekor-capture`, `agent-sdk-capture` and `jidec-n65` commit authors are
  automated capture workflows (`.github/workflows/`), not people, and are not counted above.

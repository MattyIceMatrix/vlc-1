# NENRIN Discrepancy Record 0001 — Two Witnesses, One Target, Both Correct (`nenrin-discrepancy-0001`)

**Kind:** founding discrepancy record for `nenrin-v1`, anchored beside that specification.
**Target:** `https://mcp.horizonshield.dev/mcp` (HORIZON SHIELD audit server), with the divergence generalising to every server on the horizonshield.dev zone.
**Window:** 2026-08-09 through 2026-08-15 (UTC).

This record documents the real event that motivated discrepancy records as a first-class object: two independent witnesses measured the same target in the same window, reported incompatible results, and were both correct. The disagreement itself was the information.

---

## Witness A: the operator's gate, scheduled vantage

`hs-verify-gate`, invoked by Cloudflare cron, measuring nightly from inside the same Cloudflare account. Observations for the target, from the public history at `https://gate.horizonshield.dev/history?endpoint=https%3A%2F%2Fmcp.horizonshield.dev%2Fmcp`:

```
2026-08-09T01:18:56.366Z  reachable: true   record_sha256: d4ff4a21427ad02e566a47de360e36990073c9666ca6ef9b57e52815ba9f4b42
2026-08-13T18:00:38.235Z  reachable: true   record_sha256: 4d204e6a8cd7fcd2acf552fcb0a36a0519f19359203a8f21251fccd3d619f93c
2026-08-14T18:00:38.072Z  reachable: true   (nightly sweep, six endpoints measured, all reached)
```

A week of green history, every sample honest, every sample taken from a vantage that shared fate with the thing being measured.

## Witness B: babyblueviper1, external vantage

From his own network, plain curl, no browser tooling, invoking the gate's public HTTP check. Reported 2026-08-15 (JST): `reachable: false`, `mcp_endpoint` failed with `initialize failed: http 522`, agent card fetch likewise 522. Before trusting any of it, he independently recomputed the gate's `record_sha256`: removed the two excluded fields, canonicalised, hashed, and confirmed the match.

His written consent to be named here: "Yes, name me on the reproduction -- happy to be the 'off my network' data point, that's real and it's yours to use." The name is his own stated choice: babyblueviper1 is the identity he publishes under wherever records of this kind are cited, and he asked in writing that this permanent record use it consistently.

## Operator reproduction and boundary

```
2026-08-14T23:18:50.259Z  gate /check -> target        reachable: false, http 522
same minutes              direct initialize -> target  HTTP 200
2026-08-14T23:22:44.151Z  gate /check -> second same-zone endpoint   identical 522
                          gate /check -> off-zone host               reached (405, as expected)
```

The target was up the entire time. Two commercial liveness monitors and a residential client were receiving 200s from it while the gate's HTTP-invoked checks failed.

## Mechanism

Cloudflare's subrequest loop guard keys on the zone the incoming request arrived on. Three rules, all measured:

```
HTTP entry (zoned)   -> same-zone custom domain : blocked, 522
cron entry (no zone) -> same-zone custom domain : allowed
any entry            -> same worker (self)      : blocked
```

Witness A measured from a context the guard permits. Witness B triggered a context it blocks. Both reported exactly what their vantage showed. Neither could have discovered the boundary alone: the operator's week of green could not surface it, and the external failure alone could not locate it.

## Resolution

Fixed 2026-08-15, publicly: own-zone probes invoked over HTTP now route through a relay worker outside the zone path, every hop on the public edge. Every verdict since carries `probed_via` naming the route that measured it, a User-Agent identifying the prober, `reachable: null` when the instrument itself fails, and `gate_commit`, the commit that produced the verdict, inside the hashed record. Deployed as gate_commit `b72b86526b6f`; the change history is public at `github.com/ogasurfproject-jpg/horizon-shield` (commits `2a1dfc91` through `8b0b5fc2`). The gate measured its own endpoint for the first time as a consequence: `reachable: true`, `status: pending`.

## What this record establishes

A single witness can err in either direction while reporting honestly. Two independent witnesses whose reports conflict cannot both be dismissed, and resolving their conflict produced knowledge neither possessed: the entry-context rules, the relay, the route disclosure, and the first self-measurement. This is why `nenrin-v1` makes the discrepancy a citable object instead of an embarrassment.

## What this record does not establish

It does not prove the target behaves correctly, that its figures are accurate, or that either witness is generally reliable. It proves that these observations were made, that they conflicted, that the conflict was resolved in public, and that the bytes of this account existed at or before the anchored time.

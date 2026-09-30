# JIDEC Verification Path — Specification v1 (`jidec-path-v1`)

**Status:** design + Phase 1 reference implementation.
**Anchor target:** the SHA-256 of this document is appended to the JIDEC ledger and stamped to Bitcoin, the same way `SPEC_HASH_INDEPENDENCE_v1.md` was anchored as entry #2. Once anchored, this specification is immutable.

---

## 1. The problem this adds to

The JIDEC ledger already fixes *results*. A claim record commits to input, reference data, algorithm, thresholds, result, and PDF, and its SHA-256 is anchored to Bitcoin. Anyone can recompute the hashes and confirm the result was not retrofitted.

What the ledger does not yet fix is the *act of verification itself*. When Federico fetched `/canary`, then fetched the anchored entry #4 source, then compared the constant in both, he walked a specific path through the system. That walk — which endpoints, in which order, reading which bytes, reaching which verdict — existed only in his terminal and his comment. It was not itself a durable, citable, re-runnable object.

A JIDEC Verification Path makes that walk a first-class artifact: content-addressed, tamper-evident, anchored to Bitcoin, and citable by any agent.

## 2. The core idea: a path is a record AND a recipe

A path is two things at once, and that duality is the whole point.

As a **record**, it freezes what was observed: the exact request and response bytes at each step, content-addressed by SHA-256, plus the verdict reached. This is history. It cannot change after anchoring.

As a **recipe**, it says how to walk the same route again and what to compare. Re-walking a path later produces a fresh observation that either matches the frozen one or does not. A match means the system has not drifted since the path was anchored. A mismatch is not a bug in the path — it is the path doing its job, detecting that a live endpoint now returns different bytes than it did when the walk was anchored.

This is what "bidirectional" means concretely. A path is not a one-way log you read. It is a route you can drive forward again (replay) and trace backward (provenance), and the anchored copy is the fixed reference both directions are measured against.

## 3. Schema

A path is a JSON object. The bytes anchored to the ledger are its canonical serialization (UTF-8, keys sorted, no insignificant whitespace: `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False)`).

The `path_id` equals the SHA-256 of those canonical bytes, which is also the `claim_sha256` the ledger records. The identity of a path is the hash of its own content. Presentation fields (`path_id`, `cite_as`) are derived by the reader and are NOT part of the canonical bytes, so the hash never has to contain itself.

```
{
  "schema": "jidec-path-v1",
  "purpose": "<one line: what this walk verifies>",
  "walked_at": "<ISO-8601 UTC of when the walk started>",
  "walker": { "tool": "jidec_path.py", "version": "1" },
  "base": "<base URL the walk targeted>",
  "nodes": [
    {
      "n": 0,
      "kind": "fetch",
      "request":  { "method": "GET", "url": "...", "headers_sha256": "...", "body_sha256": null },
      "response": { "status": 200, "headers_sha256": "...", "body_sha256": "<sha of exact bytes>" },
      "duration_ms": 342
    },
    {
      "n": 1,
      "kind": "compute",
      "label": "parse /canary json and extract the three fields",
      "inputs": [ { "from_node": 0 } ],
      "output_sha256": "<sha of the computed value>",
      "output_preview": "<short human-readable slice>"
    }
  ],
  "assertions": [
    {
      "claim": "live_computed_hash == C025E288675EE898",
      "op": "eq",
      "result": true,
      "evidence_nodes": [0, 1],
      "observed_sha256": "<sha of the observed value the assertion turned on>"
    }
  ],
  "verdict": { "outcome": "PASS", "n_pass": 3, "n_total": 3 },
  "replay": {
    "how": "re-run the same walk against `base`; recompute every node body_sha256 and re-evaluate assertions",
    "match_means": "no drift since anchoring",
    "mismatch_means": "the live system now differs from the anchored observation"
  },
  "prev_path_refs": []
}
```

Two node kinds in v1. A `fetch` node records one HTTP request/response, both content-addressed. A `compute` node records one local derivation (parse, extract, hash, grep) over the outputs of prior nodes. Every assertion names the nodes it depends on and pins the observed value by SHA-256, so a citing agent can see exactly which bytes the verdict rested on.

## 4. Citation contract

A path is cited by the URI `jidec:path:<path_id>`. When an agent cites a path, the following is guaranteed and checkable without trusting the citer:

The path's bytes are retrievable at `…/ledger/{n}?format=raw` and their SHA-256 equals `<path_id>`. The path's existence at or before a point in time is provable by the Bitcoin attestation at `…/ledger/{n}/ots`. Every value the verdict depended on is pinned by SHA-256 inside the path. And the walk can be replayed against the same `base` to check whether the live system still matches the anchored observation.

So "cite JIDEC path `abc123…` as the basis for asserting the canary matched on 2026-07-25" is a claim another agent can fully audit: fetch the path, confirm its hash, confirm its Bitcoin anchor, read the pinned assertions, and optionally replay. No shared trust in the citer, and none in HORIZON SHIELD.

## 5. Bidirectional traversal, stated honestly

Three concrete capabilities, not one magic reverse-execution:

**Forward replay.** Re-walk the path against `base`; diff fresh observations against the frozen ones. Detects drift. Implemented in the recorder from Phase 1.

**Backward provenance.** Follow `prev_path_refs` to the paths a path was built on, forming a DAG of verifications that lean on earlier verifications. A path that verifies a monthly benchmark can point at the path that verified last month's, and so on. Phase 1 records the field; walking it is a reader concern.

**Reverse index (query).** "Which anchored paths ever fetched this URL, or observed this SHA, or were walked by this actor?" This needs a secondary index in the ledger worker and is Phase 3. Until then the ledger is scannable but not indexed.

Calling a path "reversible" means these three, together. It does not mean re-running a computation backward to recover its inputs; SHA-256 is one-way and the design depends on that.

## 6. Prior art, and what is actually new

The components are known. Sigstore's Rekor is a transparency log of signed metadata. in-toto and SLSA attest to supply-chain build provenance. W3C PROV-DM is a provenance ontology. OpenTelemetry traces distributed calls. None of these is the contribution here, and this spec does not claim to have invented content-addressing, transparency logs, or provenance graphs.

The combination is what is new: a *replayable verification walk*, content-addressed as a single citable object, anchored to *Bitcoin* rather than a service-operated log, framed so that the mismatch-on-replay is a first-class drift signal, and with an explicit citation contract for *AI agents* to reference a specific verification by content address. Rekor logs that an attestation existed; it does not hand an agent a re-runnable route and a defined guarantee of what citing it buys. That gap is the target.

This section is deliberately in the anchored bytes. If someone later shows a true prior instance of the full combination, that is a real finding, and the honest framing above is what lets it be one.

## 7. Phasing

Phase 1 (this delivery) defines the schema and ships `jidec_path.py`: a stdlib-only recorder that walks a verification, content-addresses every step, reaches a verdict, and emits canonical bytes ready to append to the ledger as an ordinary entry. No worker change is needed — a path anchors through the existing append + stamp path. The first real path walks the entry-#4 verification and becomes entry #5.

Phase 2 adds a small SDK so instrumented calls accrete a path automatically, and a `--replay` mode that re-walks an anchored path and reports drift.

Phase 3 adds worker endpoints: `GET /paths/{sha}` (typed view), `GET /paths/{sha}/replay` (server-side re-walk), and `POST /paths/query` (reverse index by url / sha / actor), backed by a secondary KV index.

Phase 4 exposes citation and replay as MCP tools so an agent can cite or re-run a JIDEC path by URI.

## 8. Design principles (unchanged from the ledger)

Everything is content-addressed. Nothing depends on a single account or repository more than it must. Any third party can reproduce and replay. Flaws are published and fixed, and the fixing is itself anchored. Automation and interoperability rise in stages, never at the cost of the previous four.

---

**The SHA-256 of this document is anchored to Bitcoin as a JIDEC ledger entry. After anchoring, this specification cannot be altered.**

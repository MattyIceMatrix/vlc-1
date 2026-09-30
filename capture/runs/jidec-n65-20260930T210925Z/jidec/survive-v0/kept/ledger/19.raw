# NENRIN v1 — Machine-Readable Tree Rings for Agent-Facing Services (`nenrin-v1`)

**Status:** design, with the founding discrepancy record anchored alongside this specification.
**Anchor target:** the SHA-256 of this document is appended to the JIDEC ledger and stamped to Bitcoin, the same way earlier specifications were anchored. Once anchored, this specification is immutable. Corrections are made by later entries that cite this one, never by editing it.

A carpenter reads the age of a tree from its rings without cutting it. A ring is added once a year and cannot be painted in afterwards without splitting at the cut. Time is the one resource that can be recorded but not purchased. NENRIN gives that property to software services.

---

## 1. The problem

Agents can already find services. In one measured thirty-day window, one MCP server appeared in 93,983 search results and was invoked zero times. Discovery is solved. Choice is not. An agent choosing between two servers sees a name, a description written by the vendor, and a URL. Everything it can read is authored by the party it is trying to evaluate.

The missing layer is a record of conduct that the subject did not author: taken by independent parties, published whether flattering or not, and accumulated over time that cannot be backfilled.

## 2. The four layers

**Layer 1, open witnessing.** Any party may measure any endpoint and submit the walk as a signed record in the `jidec-path-v1` format, extended with the witness's own identity: who measured, from what vantage (the generalisation of `probed_via`), and the code identity of the measuring tool (the generalisation of `gate_commit`). The ledger batches and anchors submissions. The operator of the ledger holds no veto over what an accepted witness observes.

**Layer 2, discrepancy records.** When two witnesses report incompatible observations of the same target over overlapping time, that pair becomes a first-class, content-addressed, anchored record of its own. This is the heart of the design. A single witness can lie or err. Two independent witnesses disagreeing cannot both be dismissed: either one instrument is broken, or the target presents differently to different observers, and both facts are worth a permanent citation. Certificate transparency treats log divergence as an incident to resolve quietly. NENRIN treats witness divergence as a product: the founding record of this specification (`nenrin-discrepancy-0001`) documents a real divergence in which both witnesses were correct and the disagreement itself was the discovery.

**Layer 3, the ring.** Per endpoint, per calendar month, the accepted witness records are bundled into one ring:

```
{ "schema": "nenrin-ring-v1", "ring": "2026-09", "endpoint": "https://.../mcp",
  "witnesses": 3, "instants_sampled": 87, "instants_reached": 84,
  "manifest_hashes_observed": ["..."], "surface_changes": [], "discrepancies": [],
  "prev_ring_sha256": "...", "limits": "..." }
```

Rings carry counts with denominators, never rates, never scores, never rankings. Each ring includes the hash of the previous ring, forming the chain that makes the metaphor literal. Each ring is anchored, so its existence at its stated month is provable against Bitcoin block height. Eighteen months of rings cannot be created in an afternoon by anyone, including the ledger operator.

**Layer 4, self-application.** The ledger operator's own services carry rings under identical rules. The reference implementation already practises this: its gate fails its own test in public, records `unpinned` when deployed without a pinned commit, and reports `reachable: null` when its own instrument fails, because an instrument failure is not a statement about the target.

## 3. Gaming analysis, stated inside the specification

**Shim farms.** An adversary can park empty handshake responders early and let rings accumulate. This is not preventable without executing tools, which requires consent. Therefore a ring records conduct facts, not uptime theatre: witness count and independence, manifest continuity, discrepancy count. A shim that maintains three independent witnesses and an unchanged manifest for eighteen months has paid most of the cost of simply being honest. The residual gap is stated in every ring's `limits` field.

**Witness collusion.** Witnessing is open. One honest witness arriving at any time produces a discrepancy record against a colluding set, and the record is permanent. The cost of maintaining a cartel grows with time; the cost of honesty does not.

**Operator capture.** The ledger is append-only and anchored. The operator cannot delete, reorder, or silently amend. Retirements are marked deprecated and left visible, because a record that can be erased on request is not a record.

**Time forgery.** Bounded by Bitcoin block height. This is the one layer that is physics rather than policy.

## 4. Prior art, and the falsifiable claim of novelty

The components are known and are named here deliberately: transparency logs (Certificate Transparency, Sigstore Rekor), build provenance (in-toto, SLSA), anchored timestamps (OpenTimestamps), liveness monitoring (commodity). None of these is claimed as new.

The combination claimed as novel is: (1) conduct of agent-facing services as the subject, (2) an open witness model where anyone may submit anchored observations, (3) witness disagreement as a first-class citable record rather than an incident, (4) chained periodic bundles that constitute an unpurchasable duration credential, and (5) the operator measured under the same rules, in the same public record, with its failures retained.

If a genuine prior instance of this full combination exists, that is a real finding. Whoever demonstrates it is invited to submit the demonstration as a witness record to this ledger, where it will be anchored beside this claim. This paragraph is inside the anchored bytes so that the claim and the invitation cannot be quietly separated.

## 5. Phasing

Phase 1: this specification and the founding discrepancy record, anchored. Phase 2: the witness intake endpoint on the ledger, accepting signed third-party walks. Phase 3: monthly ring generation for the endpoints already on the reference register, exposed through the register's existing lookup tooling. Phase 4: a convention for embedding a service's latest ring reference in its agent card, plus read-only tooling for any agent to fetch and verify rings without an account.

## 6. Design principles, unchanged from the ledger

Everything is content-addressed. Anyone can reproduce and replay. Counts, never scores. Unmeasured is never a pass and never a fail. Flaws are published and fixed, and the fixing is itself anchored. The operator is a subject, not an exception.

---

**The SHA-256 of this document is anchored to the JIDEC ledger and stamped to Bitcoin. After anchoring, this specification cannot be altered.**

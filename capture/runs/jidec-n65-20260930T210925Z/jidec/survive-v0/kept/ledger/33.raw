# NENRIN coordinate-v1 addendum: the instant coordinate (`nenrin-instant-v1`)

**Status:** addendum. It corrects nothing by editing. Both documents it concerns are anchored and are cited here by their bytes, never altered:

    9ccba2e325fd2a555fcdb2dec519b8c6bf7a669064674846aea98ecfff824e3d  NENRIN_SPEC_v1.md
    5be2b22e339d8b5c45a272325c49da189f10715b01683025ae903e83bf251df5  NENRIN_COORDINATE_SPEC_v1.md

The operator is a subject of that rule, not an exception. This addendum exists because the defect below was found in the operator's own running instrument, by the operator, and the honest order is to name it before fixing it.

---

## 1. The defect

`NENRIN_COORDINATE_SPEC_v1` states the rule: **the coordinate is chosen by the party being verified.** `NENRIN_SPEC_v1` gives a gaming analysis in four parts: shim farms, witness collusion, operator capture, time forgery.

Time is a coordinate, and it is not in that list.

A ring counts `instants_sampled` and `instants_reached`. Whoever chooses the instants chooses what the ring says. In the reference gate as deployed on 2026-09-05 (`gate_commit` ccff81d15afc), the free tier's measurement day is

    bucket = int(sha256(endpoint)[:4], 16) % 7
    due    = floor(unix_ms / 86400000) % 7 == bucket

Every input is public. **The target can compute the day it will be measured.**

The anchored gaming analysis answers shim farms this way:

> A shim that maintains three independent witnesses and an unchanged manifest for eighteen months has paid most of the cost of simply being honest.

That argument assumes the shim must stay up. Under a computable schedule it does not. It must answer on one day in seven. The cost of eighteen months of rings falls to one seventh, and the ring cannot tell the difference, because the ring only knows the instants it was handed.

The same defect has a second face on the same instrument. The determinism condition measures, in the gate's own published words, "the first well-formed tool in the server's own `tools/list` order." **The server chooses the order.** The gate discloses this as a residual. Disclosing a coordinate defect is not closing it.

## 2. How this was found, and what the operator did with it

On 2026-09-05 the operator wrote to an outside endpoint that had appeared on the register, and, in the name of transparency, published the bucket arithmetic in that letter so the recipient could verify the stated measurement date without trusting the operator.

That paragraph is simultaneously an honest disclosure and a working exploit recipe. Both readings are correct. The letter was not withdrawn, because the arithmetic was already derivable from the public source. What follows is the repair.

## 3. The rule, applied to the time axis

Derive the coordinate from a source neither party controls, and bind the derivation into the verdict as an output.

Two ingredients. Either alone is insufficient, and the reason each is necessary is a red team vector, not an assertion.

**A salt the measurer commits to before the window and reveals after.** Without it the target predicts, because every other input is public. Vector `control: holding the salt makes prediction exact` proves that the secrecy of the salt is the entire defence and not decoration.

**A Bitcoin block height at the window boundary.** Without it the measurer could mint a salt after measuring and claim whichever instant flattered the result. The commitment must be anchored below the window's opening height, so the commitment provably predates the measurement. Vector `attack: commitment anchored after the window opened is refused both ways`.

The measured tool is derived by the same salt over the **lexicographically sorted** tool-name set, so reordering `tools/list` cannot steer the pick, and renaming to steer it changes `tool_set_sha256`, which a ring already records as a surface change.

The block that goes into the verdict:

```
"coordinate_derivation": {
  "schema": "nenrin-instant-v1",
  "endpoint": "...", "window_id": "2026-09",
  "salt_commitment": "<sha256, anchored before the window>",
  "anchor": { "commit_height": N, "window_open_height": M, "block_hash": "..." },
  "instant_slot": 561, "slots_per_window": 1440,
  "tool_set_sha256": "...", "tool_count": 4, "tool_measured": "...",
  "rule": "...", "limits": "..."
}
```

Every field is an output the measurer derived. None is an input the subject supplied. A third party recomputes all of it from the revealed salt and trusts nothing the measurer asserted.

## 4. Reference implementation and adversary

    instant_coordinate.py   derivation and third-party verification
    instant_redteam.py      17 vectors, all green, offline, deterministic

Run them: `python3 instant_redteam.py`. Categories: 11 attack, 3 control, 1 misclassification, 2 residual.

The machinery this depends on already exists beside it, built for a different purpose. `localheaders.py` and `sync_headers_p2p.py` hold Bitcoin headers locally and sync them over the peer-to-peer network so that no block explorer has to be trusted; `freshness_v2.py` and `freshness_v3.py` use that beacon to close backdating. **The beacon that closes backdating is the beacon that closes instant prediction.** No new cryptography is introduced here, and none should be: a scheme nobody can recompute is worse than the defect it replaces.

## 5. Residuals, named and not solved

**A salt is single use per window.** Vector `attack: a revealed salt reused in a later window is fully predictable` exists to prove the failure, not to pass a test. Reuse after reveal restores full prediction. A leaked salt burns one window, not the system, only if this rule holds.

**Derivation is fair only inside the surface the subject declared.** A tool never listed is never picked. That set is unknown, not absent, which is the same boundary the census names at population scale and the same one the founding external witness named first.

**This does not measure quality.** A server that answers honestly at an unpredictable instant with an unpredictably chosen tool may still return nonsense. `NENRIN_SPEC_v1` never claimed otherwise and this addendum does not extend the claim.

**Not yet implemented.** As of 2026-09-05 the gate still selects by the computable bucket and by the server's own tool order. This document is published before the code changes, deliberately, so that the defect is on the record while it is still open. A later entry will cite this one when the gate closes it.

## 6. What this does to the novelty claim

`NENRIN_SPEC_v1` claims a combination of five properties, and names transparency logs, build provenance, anchored timestamps and liveness monitoring as prior art that is not claimed as new. This addendum proposes a sixth property to that combination, and it is the one that the named prior art does not have:

**the instant and the object of measurement are chosen by neither the subject nor the measurer.**

Certificate Transparency, Rekor, in-toto and SLSA all take delivery of an artifact the submitting party chose to submit. That is the correct design for their purpose. It is the wrong design for conduct over time, because conduct is what happens when nobody chose to be watched.

**Contemporaneous and independent, reported the same day.** On 2026-09-05, hours after this addendum was written, Federico Blanco Sanchez-Llanos reported that his own `freshness_beacon` already binds a verdict's timestamp to a future block height the subject cannot have influenced. Same commit-reveal-against-real-randomness shape, a different problem, and his existed first. The claim above narrows accordingly, and this is the narrowed form: what is proposed here is not the binding to unpredictable future randomness, which is not new, but its application to **which coordinate gets measured** rather than to whether a timestamp is valid. He is named here on his own account of his own system, which is the only kind of prior art worth citing. He is also the founding external witness of `nenrin-discrepancy-0001` and the author of the question this whole coordinate line answers, so the narrowing arriving from him is the process working, not an interruption of it.

If a prior instance of this exists, the invitation in the anchored specification stands and applies to this addendum: demonstrate it, and it will be anchored beside this claim.

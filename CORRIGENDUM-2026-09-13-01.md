# Corrigendum 1 to VLC-1 — two defects reported by an external reviewer

**Issued:** 2026-09-13
**Reporter:** Shahab K. — reported by direct message, reproduced against the
published checker and the published example corpus, credited here with his
permission.
**Status:** both findings confirmed. One is a classification error. **One is a
defect in the specification's headline claim.**

---

## Summary

Shahab K. read the published specification, ran the published checker, and
mutated the published examples. He found two defects. The second invalidates a
claim made in §1 of the specification as published, and it is stated below in
the sharpest form the maintainers can put it, rather than the mildest.

Neither finding was found by the maintainers. Both should have been.

---

## Finding 1 — a supplied statement was raising the structural level

**Reported as:** VLC-L3-1 and L3-1d are marked structural, but the checker only
tests that the coverage field is present and non-empty. He edited
`examples/L3-coverage.jsonl` to claim coverage on `/v1/responses` where the
proxy sits only on `/v1/chat`, emptied `unattached_here`, set `basis` to the
string `"trust me"`, and rechained so L1 still verified. **It scores structural
L3, identically to the honest file.**

**Confirmed.** And confirmed for the reason the specification itself supplies:
**VLC-V-3 states that no supplied statement may raise the structural level**,
and the presence of a declaration was doing precisely that. §9.1 already
concedes that a producer can fabricate a coverage declaration, so the
specification's prose was correct; its *classification* was not.

He also observed that **L3-4 was already marked attested for what appears to be
the same reason** — so the specification was internally inconsistent, and the
inconsistency pointed at the answer.

**Resolution.** VLC-L3-1 is split:

| id | requirement | class |
|---|---|---|
| **L3-1a** | a coverage declaration is present and well-formed | **structural** — a verifier recomputes this from the log |
| **L3-1b** | the declared surface is the surface actually observed | **attested** — always, with no code path to structural |

**L3-1d** is reclassified **attested** on the same grounds. The checker is
amended so that no input can raise L3-1b or L3-1d above attested.

---

## Finding 2 — the loss mechanism assumes the producer survives its own outage

**Reported as:** `conformance.py` never reads a timestamp. Coverage is declared
over sources, never over an interval. So the two-hour outage in §1 is caught
only if the transport drops records *and the producer survives to declare it*.
He kept the second half of a log, renumbered so the identity closes, rechained
it: **structural L3. Thirty inferences gone, first record ninety seconds in,
nothing in the file saying so.**

**Confirmed, and it is worse than reported.**

The specification's opening paragraph claims that a two-hour outage is
indistinguishable from a quiet afternoon *unless* the log carries loss
accounting. **That claim holds only for transport loss.** Where the *producer*
is what failed, no records are produced, no loss is declared, and there is
nothing for L2 to be absent from. The delivered file is internally perfect over
whatever window it happens to cover.

This is now stated as a theorem rather than an admission.
`proofs/sentinel_interval.v`, 8 results, 0 admitted, 0 axioms:

- **`producer_death_is_invisible`** — a checker's verdict on a renumbered
  truncation is *equal* to its verdict on the renumbered whole. Not weaker.
  Equal. The two are the same object to the identity.
- **`l2_cannot_detect_producer_loss`** — there is no log an L2 checker rejects
  on these grounds. L2 has no power against producer death at all.

The reporter also noted that **T3 in the threat model already names agent
restart.** A threat model that lists a threat no requirement addresses is a
harder criticism than an unnoticed gap, and it is quoted here because it is the
more useful half of the finding.

**Resolution.**

1. **§1 is amended** to scope the opening claim to transport loss, and to state
   the producer-loss case explicitly as an open exposure at L2.
2. **A new level, L3i — interval coverage.** Coverage is declared over an
   *interval*, and every tick of that interval is witnessed by an attestor the
   producer does not control. A producer that dies stops emitting ticks, and the
   missing ticks are the evidence its own silence cannot supply.
   `missing_start_tick_fails` proves a log lacking the declared start tick fails
   L3i regardless of how its counters are renumbered; `full_window_passes`
   proves the level is not vacuous.
3. **The regression corpus** carries the reporter's mutated files, so the
   defects stay closed.

---

## What this corrigendum does not fix

- L3i requires an attestor. A deployment without one gains nothing from it and
  should report L3i as unestablished, not failed.
- An attestor that colludes with the producer defeats it. That is the same
  limitation Annex I already states for hardware roots.
- The maintainers have not determined whether wholesale dropping of attestor
  traffic, or replay of anchors across intervals, defeats L3i. **The reporter
  has been asked to attempt both.**

---

## Note on how this was found

Every figure in this project prior to today was produced by the maintainer, on
the maintainer's machine, with the maintainer's harness. By this
specification's own L5, that establishes nothing: a self-authored transcript
cannot establish independent witnessing of the behaviour it describes.

This corrigendum is the first evidence in the project's history that survives
its own L5, and it exists because someone outside the project ran the checker
and tried to break it. That is worth more to the specification than the
defects cost it.

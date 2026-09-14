# External findings

Defects in this specification or its checker reported by people outside the
project. Listed with the reporter's name where permission was given.

Every figure in this project before 2026-09-13 was produced by the maintainer,
on the maintainer's machine, with the maintainer's harness. By this
specification's own L5 that establishes nothing. This file exists because that
is a problem, and because the only fix is other people.

---

## EXT-001 — coverage declaration raised the structural level

**Reporter:** Shahab K. · **Reported:** 2026-09-13 · **Status:** confirmed, fixed
**Severity:** specification classification error, contradicting VLC-V-3

A coverage declaration that was present but false scored structural L3,
identically to an honest declaration. The checker tested presence and
non-emptiness, not correspondence. VLC-V-3 forbids a supplied statement raising
the structural level; this did. The reporter also identified that L3-4 was
already classified attested for the same reason, making the specification
inconsistent with itself.

Fixed by Corrigendum 1: L3-1 split into L3-1a (structural, well-formedness) and
L3-1b (attested, correspondence); L3-1d reclassified attested.

## EXT-002 — L2 loss accounting assumes the producer survives its own outage

**Reporter:** Shahab K. · **Reported:** 2026-09-13 · **Status:** confirmed, fixed
**Severity:** invalidates a claim made in §1 as published

A log truncated to a suffix and renumbered closes the L2 completeness identity
and scores structural L3. The specification's headline example — a two-hour
outage indistinguishable from a quiet afternoon — was established only for
*transport* loss. Where the producer is what failed, nothing is produced,
nothing is declared, and the delivered file is internally perfect over whatever
window it covers.

The reporter further noted that T3 in the threat model already names agent
restart, so the threat model listed a threat no requirement addressed.

Proved as `producer_death_is_invisible` and `l2_cannot_detect_producer_loss` in
`proofs/sentinel_interval.v`. Fixed by Corrigendum 1: §1 amended, and a new
level L3i requiring interval coverage witnessed by an attestor the producer does
not control.

**Open, and put back to the reporter:** whether dropping attestor traffic
wholesale, or replaying anchors across intervals, defeats L3i.

---

## How to report

Open an issue, or write to the maintainer. Findings that break a published
claim are the most valuable thing this project can receive, and they are
credited by name unless the reporter prefers otherwise.

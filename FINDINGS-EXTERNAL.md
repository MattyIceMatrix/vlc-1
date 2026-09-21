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

## EXT-003 — the completeness identity ran over the wrong record class

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, fixed
**Severity:** the identity could be satisfied by a log with a deleted event

SPEC VLC-L2-5 is over *event* records. `check_l2` computed `non_event` and never
used it, so coverage and loss declarations were counted as delivered events. A
producer could delete an event, substitute one framing record, and the identity
still closed. The adapters already declared the right classes; the checker
ignored them, and the example generator encoded the same wrong count, so the two
agreed with each other while disagreeing with the specification.

Fixed by Corrigendum 2. The reference implementation's own captured journals
were written under the old count and now fail; they are hash-chained and are not
being edited in place.

## EXT-004 — a structural requirement read the adapter

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, fixed
**Severity:** a requirement classed as recomputed changed with the adapter alone

The report was that changing only the adapter's `coverage.basis_field` moved a
capture from structural L2 to structural L4. Reproduced against the checker as
it stood, the **structural level did not move** — it was L4 before and after.
The number that moved was the attested level, L2 to L5, which adapter text is
permitted to move. The file is named for its attested level, which is the
likeliest source of the reading.

What the report did find, underneath, is real: VLC-L5-4 is classed structural
but scored the witness log on *every* requirement at each level, attested ones
included. VLC-L3-1d is attested and reads the adapter's `basis_field`, so
pointing that field at any non-empty field flipped VLC-L5-4 from FAIL to ok with
the log unchanged. The structural level survived only because L5 is attested by
construction and caps it.

Fixed: VLC-L5-4 now scores the witness on its structural requirements only.
`selftest.sh` section 8 rewrites the adapter's coverage basis on every worked
example with a coverage block and requires every structural requirement to come
out identical; it fails against the unfixed checker and names VLC-L5-4.

A consequence, stated rather than hidden: on the capture above VLC-L5-4 now
passes where it used to fail, because the witness's recomputable coverage
accounting is complete and only its exhaustiveness basis, an attested claim, is
missing. If that basis should still count against a witness, it belongs in a
separate attested requirement. Left open.

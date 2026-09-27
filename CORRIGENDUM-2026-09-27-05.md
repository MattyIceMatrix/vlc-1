# Corrigendum 5 to VLC-1 1.3-draft — issued as 1.4-draft

**Issued:** 2026-09-27
**Findings:** EXT-004 (its open question, closed here), EXT-018 and EXT-019.
Full entries in `FINDINGS-EXTERNAL.md`.

## One normative addition

**VLC-L5-6 (the witness's coverage basis)**, attested. A log presented as a
witness shall state the basis on which its coverage enumeration is exhaustive,
and a witness that does not shall not be used to corroborate an absence.

This is the only requirement added or changed by this version. Everything else
recorded below is a repair to the checker, the tests or the record, and moves no
conformance result.

## Why it was needed

EXT-004 (pipavlo82, 2026-09-21) found that VLC-L5-4 — classed structural — was
scoring the witness on every requirement, attested ones included, so pointing an
adapter's `basis_field` at any non-empty field could flip a structural verdict
with the log unchanged. The fix made VLC-L5-4 score structural requirements
only. That was correct: a structural result must not move with adapter text.

It left a consequence the ledger stated honestly and then left open:

> on the capture above VLC-L5-4 now passes where it used to fail, because the
> witness's recomputable coverage accounting is complete and only its
> exhaustiveness basis, an attested claim, is missing. If that basis should
> still count against a witness, it belongs in a separate attested requirement.
> Left open.

**It should, and here is where it mattered.** `witness/reconcile.py` decides
whether a witness may produce the strong result by checking its chain and its
**structural** level. Structural L3 does not include VLC-L3-1d, the attested
exhaustiveness basis. So a witness whose coverage accounting was recomputably
complete, but which gave no reason to believe its surface was the right one,
qualified to corroborate — including to **vouch for an absence**, which is the
one thing a witness does that its own records cannot justify.

Demonstrated on the reference implementation's honest session, with the
adapter's `basis_field` pointed at a field that does not exist:

| | structural | attested | VLC-L5-4 | reconciler, before | reconciler, after |
|---|---|---|---|---|---|
| basis stated | L4 | L5 | PASS | qualifies | qualifies |
| basis removed | L4 | **L2** | PASS | **qualifies** | **refused** |

The checker itself already said this witness could not claim attested L3. The
reconciler let it corroborate anyway, because it read only the structural half
of the witness's standing and nothing spoke for the other half.

## What changes, and what deliberately does not

**VLC-L5-6 is redundant for the level arithmetic, and this corrigendum says so
rather than overclaiming.** VLC-L3-1d is already required for attested L3, and
levels are cumulative, so no log could reach attested L5 without passing it. The
addition does not close a hole in how levels are computed.

What it closes is a hole in **how a witness's standing is used and reported.**
Before, the witness's standing at L5 was VLC-L5-4 alone — structural by design —
and the attested half was visible only by reading VLC-L3-1d two tiers down.
Anything that consumed "is this witness in standing?" from the L5 tier, as the
reconciler does, got half an answer. VLC-L5-4 is now the structural half and
VLC-L5-6 the attested half, and the reconciler requires both.

**No published result changes.** Every log in this repository that reached
attested L5 under 1.3-draft was checked before the change: all four
reference-implementation journals already pass VLC-L3-1d, and all four remain at
attested L5 under 1.4-draft. The honest witness session still qualifies in the
reconciler. Selftest section 5, which scores the author's own journals by the
same rules as everyone else's, is unchanged.

## Repairs in the same version, which move no result

| Finding | Repair |
|---|---|
| **EXT-018** | L3i had never executed: `_dig` was undefined, and no adapter, fixture or test reached the scoring body. Once running, three attacks passed it, one of them the second question EXT-002's reporter left open. Fixed, with six fixtures and a negative control. |
| **EXT-019** | A tree-wide audit (1512 scorings) found six requirements that had never been observed to fail; five now have negative controls and the sixth has no failure path by design, now stated. `proofs/sentinel_interval.v` was cited in five places and absent; the original was recovered and committed, and CI now compiles every development rather than one named by hand. |

## Checks

`selftest.sh`: 118 → 120 — a precondition that removing the basis leaves the
witness at structural L3 or above, and the negative control itself, in which
only the exhaustiveness basis is removed and the strong result must be refused
for that reason. Verified in both directions: with the reconciler's new gate
disabled the control fails, and nothing else does. Two proof developments, 20
results, 0 admitted, 0 axioms.

## Version DOI

**Pending.** A version DOI is minted by Zenodo when this version is released on
GitHub. Until then Annex F records it as pending, and the concept DOI
(10.5281/zenodo.22728393) resolves to the newest published version, which is
1.3-draft. Nothing here should be cited as 1.4-draft by DOI until that release
exists.

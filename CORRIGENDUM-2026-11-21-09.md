# Corrigendum 9 to VLC-1 1.4.4-draft — issued as 1.4.5-draft

**Issued:** 2026-11-21
**Findings:** EXT-028, EXT-029, EXT-030 and EXT-031, from an independent audit
of `check_l3i.py` commissioned against the EXT-018 repair. Full entries in
`FINDINGS-EXTERNAL.md`.

## One normative requirement is added

**An adapter claiming L3i MUST declare `interval.bound_field`.** VLC-L3i-3 is
refused outright when it is absent. No other requirement changes; SPEC.md §J.4
carries the added sentence.

## Why this corrigendum exists

EXT-018, published in Corrigendum 6, tightened VLC-L3i-3 so that a bound
position must be a producer record, must not move backwards, and must reach the
end of what was delivered. That repair is the reason L3i exists as a level.

**The repair was behind an unvalidated adapter key.** `bound_field` was read
inside the per-tick loop and `if bf:` guarded all three binding clauses *and*
the assignment to `bound_pos`. With the key absent, `bound_pos` stayed empty,
the ordering loop iterated over nothing, the end-of-log coverage test was
skipped because it tests `if bound_pos`, and the clause fell through to a pass.

Every attack fixture in this repository passed. The three EXT-002 reporter
questions that Corrigendum 6 was issued to answer all passed. An omitted key in
a configuration file — not reviewed code — turned the clause the whole level
exists to supply into a no-op that reported conformance, and the output was
indistinguishable from a real result.

This is the defect this specification was written about, occurring inside the
specification's own checker: a record produced by the thing it describes is a
claim, and a check that cannot be seen to have run is not evidence. **Every L3i
verdict issued by a checker before 1.4.5-draft should be treated as
unestablished** unless the adapter used can be shown to have declared
`bound_field`.

## What moved

| Case | 1.4.4-draft | 1.4.5-draft | Why |
|---|---|---|---|
| any log, adapter without `bound_field` | **PASS** | **FAIL** | EXT-028. The clause now refuses an adapter that gives it nothing to check |
| `l3i-anchor-replayed-at-end` (new) | **PASS** | **n/a** | EXT-029. The same replay as `l3i-anchor-replayed`, pinned to the last record instead of the first |
| `l3i-attestor-dropped`, clause L3i-3 alone | PASS | **n/a** | EXT-030. A positive statement about an empty witness set. The level still fails at L3i-2, as before |
| `l3i-uppercase-binding` (new) | **FAIL** | **PASS** | EXT-031. An honest log was refused as a forgery |
| every other published L3i result | unchanged | unchanged | the six existing fixtures score exactly as they did |

## The four findings

- **EXT-028 (critical), the repair was skippable.** Above. Fixed by hoisting
  `bound_field` out of the loop and refusing when it is absent. The refusal is
  deliberately not an early return, so VLC-L3i-4 still reports and the shape of
  the report does not change.

- **EXT-029 (high), a replayed anchor pinned to the end of the log.** The
  coverage test is `high_water < last_witnessable`, and equal positions are
  allowed because a quiet stretch honestly leaves the head where it was. So
  eight ticks all binding the *last* record satisfied both: one observed point,
  scored as a covered window. `l3i-anchor-replayed` binds the *first* record
  and was caught; the identical attack moved to the end was not.

  Reported as **unestablished, not failed**, and the reason is the finding's
  substance. From the log alone, N ticks binding one position is genuinely
  indistinguishable from an honest interval in which nothing was appended
  between the first tick and the last. Failing it would refuse honest quiet
  logs. What *is* establishable is that such a witness set carries **one
  observation however many signatures it holds**, so it cannot evidence
  coverage of an interval declaring several ticks. Saying that is the honest
  verdict. A clean pass was not, and a failure would be an overreach.

- **EXT-030 (medium), an empty witness set passed vacuously.** With no tick
  naming the interval, the loop did not run, no problem was recorded, and
  L3i-3 reported `0 witness(es) bound ... and to a position in this log` as a
  pass — a positive statement about nothing. VLC-L3i-2 does catch the wholesale
  drop, so no level was ever wrongly awarded; but a pass row for a clause that
  examined no witness is a line that gets quoted out of a report.

  Also fixed in the result collector: `_na` looked for an `unestablished`
  channel, did not find one, and fell back to `ok(rid, "unestablished: ...")`.
  So **every requirement the checker could not establish was counted as a
  pass**, and a run's pass count included rows nothing had examined. The
  fallback was written to avoid scoring an honest absence as a defect, which is
  right; with no third channel to fall back *to*, it produced the opposite
  error. `Results.unestablished` now exists and never upgrades a failure.

- **EXT-031 (medium), an honest log refused as a forgery.** `binds` was
  compared as a raw string, so a log writing its hex in uppercase was refused
  with `binds a position absent from this log: a witness lifted from
  elsewhere`. A binding names a hash and is now compared as one. An
  over-refusal is also a defect, and this one accuses the adopter of forgery.

## What keeps it fixed

`selftest.sh` section 14 is now an adverse-case matrix of nine fixtures with
their expected verdicts, and it runs four of them a second time against an
adapter with `bound_field` removed, requiring FAIL from each. The matrix also
reports `n/a` as itself rather than folding it into PASS — an earlier version
of that line printed PASS for both new unestablished verdicts, which is the
error the channel exists to prevent.

The audit's own recommendation is recorded and not yet discharged: a
requirement that has never been observed to fail is indistinguishable from one
that is not tested, and section 15 checks that for the numbered levels but not
for the L3i qualifier. Until it does, the matrix is the guard.

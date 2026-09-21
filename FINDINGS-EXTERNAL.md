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

**Fix verified independently.** The reporter checked the fix against the repository tree, not the maintainer's account of it, on 2026-09-21 (trustless-ai/recompute-kit#48).


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

**Fix verified independently.** The reporter checked the fix against the repository tree, not the maintainer's account of it, on 2026-09-21 (trustless-ai/recompute-kit#48). They also confirmed that their original structural figure was wrong and that the attested level was the one that moved, as reproduced above.


## EXT-005 — reconciliation reported agreement without valid evidence

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, fixed
**Severity:** fail-open — `--require-agreement` succeeded on inputs that establish nothing

`--require-agreement` returned success whenever no divergence was found. Two
empty inputs, a claim record with unparseable lines, and a witness journal
whose hashes were replaced with garbage all produced no divergence and exited
0. Confirming it turned up a fourth case: exec paths were compared by basename,
so a transcript claiming `/safe/bin/id` was corroborated by a kernel record of
`/usr/bin/id` — the substitution the reconciler exists to catch. Connection
scope was also applied to the witness side only.

Fixed in `witness/reconcile.py` 1.2. Evidence validity is established
separately from agreement: both records non-empty, no unparseable lines, and
the witness journal's own chain verifying through `conformance.py`. Agreement
over nothing corroborated is reported as vacuous. The strong result requires
valid evidence and non-vacuous agreement. Absolute exec paths are compared in
full. Four selftest controls, each failing against the previous reconciler.

The reconciler remains set-level: it establishes that each claimed effect was
witnessed and vice versa, not how many times. Stated rather than changed.

## EXT-006 — seven obligations checked for presence rather than type

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, fixed
**Severity:** each could reach L4 while violated

Every case below scored S4/A4 against the previous checker, after being
re-sealed so the chain still verified: a loss declaration without its interval;
a negative loss count with compensating totals; a declared loss range whose
records were in fact delivered; a coverage category omitted and read as empty;
a second coverage declaration without its basis; a policy change record
without its before and after digests; per-record policy binding where one event
lacked the digest; and determinism accepted from a reference alone. The last
three were in VLC-L4, the rest in L2 and L3.

The per-record check was also wrong in the other direction: it counted every
record carrying a digest, including the root record, so an honest per-record
log scored S3.

The worked example itself declared records 12–14 lost while delivering them.
The generator now omits them from the sequence.

Fixed: each obligation is checked as SPEC states it. `adapters/sentinel.json`
declares that a GAP record's interval is its chain position, which is weaker
than an explicit range and is said so in the adapter. Selftest section 9
re-seals ten mutants and asserts the specific requirement each must fail, with
VLC-L1-1 still passing; nine of the ten fail against the previous checker, and
the tenth is the honest control.

## EXT-007 — evidence manifest entries could fail open

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, fixed
**Severity:** a citation that was not one could still support a requirement

A present but malformed entry was treated as absent, so the requirement fell
back to the bare assertion — contrary to VLC-E-2. Digests were accepted as any
non-empty string. The negative control VLC-E-5 requires was not required, and
the project's own VLC-L4-3 entry did not name one.

Separately, the 1.1.1-draft release archive was built from a checkout with CRLF
line endings. `witness/reconcile.py` in that archive does not match its
published digest until line endings are normalized; in the repository it
matches exactly. Neither the specification nor the manifest said which
representation a digest is over.

Fixed: malformed entries fail; digests must be `sha256:` and 64 lowercase hex;
the negative control is required. VLC-E-6 states normatively that digests are
over LF-normalized bytes and that release archives carry those bytes. The
reconciler digest in `sentinel.json` is **not** updated: it pins the version
that produced the cited 2026-09-12 output, and the entry now says the
reconciler has since changed.

## EXT-008 — L1 was described as rewrite resistance

**Reporter:** pipavlo82 · **Reported:** 2026-09-21 · **Status:** confirmed, wording corrected
**Severity:** a summary claimed more than the requirement establishes

A verdict was altered, the chain and end marker recomputed, and the log still
reached L4. That is correct behaviour for a keyless chain checked on the log
alone. VLC-L1-1 already requires "a published root or public key"; the §4
summary, the README table and the checker's output implied detection without
one. All three now say that on the log alone L1 establishes chain consistency,
and that a complete rewrite is detectable only against an independently held
root or head. The requirement is unchanged.

## EXT-009 — ordinal-mode L2 accepted silent loss

**Reporter:** babyblueviper1 (invinoveritas) · **Reported:** 2026-09-21 (vlc-1#1) ·
**Status:** fixed by the reporter in #2, merged as `c002804`
**Severity:** a log with undeclared gaps scored L2

In `loss.mode: ordinal`, every hole in the delivered ordinals was counted as a
declared loss, so the identity closed by arithmetic for any log whose events
carried distinct ordinals. SPEC VLC-L2-2 requires the *producer* to declare
loss; here nobody had. Fixed: ordinal mode reads loss declarations exactly as
declaration mode does (`interval_fields`, the same typed checks) and requires
every hole to be covered by one.

## EXT-010 — duplicate member names were invisible to L1

**Reporter:** babyblueviper1 (invinoveritas) · **Reported:** 2026-09-21 (vlc-1#1) ·
**Status:** fixed by the reporter in #2, merged as `c002804`
**Severity:** a record's meaning could change with every hash still valid

The canonical-JSON mechanisms hash the parsed record, and Python's parser keeps
the last of two members with the same name. Adding an earlier duplicate changed
no hash, so an edited record verified while a first-wins parser read the
opposite value, with nothing recomputed. RFC 7493 §2.3 forbids duplicate names.
Fixed: the loader refuses duplicate member names, and — at the maintainer's
suggestion — `NaN` and `Infinity`, which are not canonical JSON.

## EXT-011 — a non-object line crashed the checker

**Reporter:** babyblueviper1 (invinoveritas) · **Reported:** 2026-09-21 (vlc-1#1) ·
**Status:** fixed by the reporter in #2, merged as `c002804`
**Severity:** hostile input indistinguishable from a low score

A line containing a bare JSON value such as `1` raised `AttributeError` and
exited 1 with nothing on stdout, where exit 1 otherwise means an expectation
was not met. Fixed: reported at VLC-L1-1 as an unreadable record.

## EXT-012 — a permanently red suite, and a verification workflow that could not go red

**Reporter:** babyblueviper1 · **Reported:** 2026-09-21 (vlc-1#1, finding 4) · **Status:** confirmed, fixed
**Severity:** CI could neither show a new regression nor, in one workflow, any failure at all

The report: since Corrigendum 2 the self-test failed three disclosed assertions
on every run, so a new regression would hide behind them; and the CI step that
scores the third-party formats piped its output through `tail -3` and asserted
nothing.

Confirming it found a third problem, worse than either. The "Independent
verification" workflow — the one written for outsiders — ran
`./selftest.sh | tee selftest.log` without `pipefail`, so the step took `tee`'s
exit status and could not fail on the self-test whatever it found. Its proof
step recorded `exit: $?` after `coqc | tee`, which is also `tee`'s status: the
log it publishes would have said `exit: 0` beside a proof that did not compile.
The separate `ci.yml` proof job checks the proofs correctly, so no failing proof
was ever published as passing. The artefact meant for outsiders could not have
reported one.

Fixed:

- The two captured witness journals are marked as expected failures, printed
  with their reason on every run. Each is marked only for its known cause: if it
  fails for any other reason, or starts passing, the suite goes red.
- The pre-fix capture cannot be regenerated, so it is re-pinned to the corrected
  result (L1) with both reasons asserted, including VLC-L3-1d, the gap it was
  kept to demonstrate. If that ever passes, the checker has been loosened.
- `independent-verification.yml` sets `pipefail` for the self-test and takes
  `coqc`'s status from `PIPESTATUS`, failing on a non-zero exit, an admitted
  proof or an axiom.
- `ci.yml` asserts each third-party format's structural and attested level.

Verified: an unrelated regression still fails the suite, a known capture
failing for a different reason still fails it, and both workflow fixes
propagate a failing exit.

**Addendum, same day.** The first run after the fix turned "Independent
verification" red, which is the fix working. The cause was a defect introduced
by the maintainer in Corrigendum 3: `selftest.sh` declares `#!/bin/sh`, and two
constructs added in sections 9 and 10 (process substitution and a here-string)
are bash-only. `ci.yml` runs `bash selftest.sh` and passed; this workflow runs
`./selftest.sh` under `sh`, which stopped with a syntax error on reaching
section 9, so sections 9 and 10 never ran there. Because of the `tee` defect
above, the workflow showed a green tick on `120f568` while the self-test had
crashed halfway through. Both constructs are now POSIX, reading from temporary
files rather than pipes so that a failure inside the loop is not lost in a
subshell. The two workflows now run the suite under `bash` and `sh`
respectively, so a future bash-only construct fails one of them.

## EXT-013 — sha256-prev-field did not link records to each other

**Found by:** the maintainer, writing tests for code paths babyblueviper1
reported as unexercised (vlc-1#1, finding 4) · **Found:** 2026-09-21 ·
**Status:** fixed
**Severity:** a deleted or reordered record passed VLC-L1-1

Under the `sha256-prev-field` mechanism each record's hash covers its own
`prev` field, so every record is self-consistent whatever that field says.
Nothing compared it with the hash of the record actually before it. Deleting an
interior record, or swapping two, left every hash valid and the end marker's
head unchanged, and VLC-L1-1 passed. No shipped adapter uses this mechanism,
which is why it was never seen; it is exactly the property L1 exists for.

Fixed: each record's declared predecessor must equal the recomputed hash of the
record before it, including the end marker's. Selftest section 2b builds an
honest, a deleted and a reordered log under this mechanism; the latter two fail
against the previous checker.

## EXT-014 — max_ordinal cannot see loss at either end of the sequence

**Found by:** the maintainer, from the same tests · **Found:** 2026-09-21 ·
**Status:** fixed after #2 merged
**Severity:** undeclared loss of the first or last records scores L2

`loss.produced.kind: max_ordinal` computes the produced count from the lowest
and highest ordinals among the records delivered. Losing records from the start
or the end of the sequence lowers those bounds with them, so the identity still
closes. Demonstrated with ten records, the first two or the last two removed
and nothing declared: `max_ordinal` reports L2; `field_of_end_marker` and
`field_of_any` both fail the identity.

SPEC VLC-L2-5 names "sequence high-water mark" as a source for the produced
count, which reads as a quantity the producer declares, not one inferred from
what arrived. The fix is likely to take both bounds from producer-declared
records. It is deferred deliberately: PR #2, in review, builds its ordinal-mode
tests on `max_ordinal`, and changing its meaning now would break a contribution
in flight. Selftest section 2b carries both cases as disclosed expected
failures; if either starts failing the identity, the suite goes red until the
marker is removed.

**Fixed, same day, after #2 merged.** `max_ordinal` now takes the high-water
mark from the end marker (`produced.high_water_field`) and the start from the
adapter (`produced.start`), and refuses to infer either. SPEC VLC-L2-5 now says
the high-water mark is a producer-declared quantity. Section 11's ordinal-mode
fixtures declare their bounds; section 2b's two expected failures now pass as
ordinary cases, with a third case showing that undeclared bounds are refused.

## EXT-015 — a witness below L3 could corroborate

**Reporter:** pipavlo82 · **Reported:** 2026-09-22 (trustless-ai/recompute-kit#48) ·
**Status:** fixed
**Severity:** the reconciler's strong result could rest on a witness the
specification says may not corroborate

EXT-005 made the reconciler check the witness journal before accepting
agreement, but it checked only the chain and end marker (VLC-L1-1, VLC-L1-3).
VLC-L5-4 requires a witness to demonstrate L3 before it may be presented as
corroboration, since a witness with an undeclared coverage gap agrees with a
lie honestly. A structural-L1 witness therefore produced the strong result.
The maintainer's own EXT-005 fix introduced the gap.

Fixed in `witness/reconcile.py` 1.3: the witness must pass VLC-L1-1 and
VLC-L1-3 and demonstrate at least structural L3. Consequence, disclosed: the
demo witness journals predate EXT-003 and score structural L1, so the honest
reconciliation is now refused, and is carried as an expected failure until the
sensor re-capture replaces them. Section 6's controls now each assert the
specific problem they exist to catch, since a control that only checks the
exit code would pass for the wrong reason while every case built on the demo
witness is refused for its standing.

## EXT-016 — "excluded both ways" was not true of unmapped tools

**Reporter:** pipavlo82 · **Reported:** 2026-09-22 (trustless-ai/recompute-kit#48) ·
**Status:** fixed
**Severity:** the report described a projection the code did not perform

A claimed tool with no entry in the scope's mapping was dropped from the claim
side, but its real effects stayed in the witness projection, where they could
surface as unclaimed effects. The report nonetheless said such tools were
"excluded both ways". Fixed: an unmapped claimed tool is an evidence problem
that blocks the strong result, and the report says so.

## Resolution of the captured-journal failures (EXT-003, EXT-015)

**Resolved:** 2026-09-21. The Sentinel sensor now reports event records only in
its end marker (octa-sentinel `5c7d8e0`). All four reference journals and both
agent transcripts were re-recorded by that sensor on a GitHub-hosted Ubuntu
runner, not the maintainer's machine (octa-sentinel workflow "Sensor
re-capture", run 35657697524). All four score structural L4, attested L5; the
loss capture declares over ten thousand kernel-dropped events in-chain and
still closes the identity; the honest witness pair is accepted by the
EXT-015 reconciler and the spoofed pair raises the substitution signature.

The 2026-09-12 captures are kept unedited in `examples/reference-impl/pre-EXT-003/`,
with a note on why. One is still load-bearing: section 6 uses it as the witness
below structural L3 that VLC-L5-4 says may not corroborate.

`selftest.sh` carries no expected failures after this change.

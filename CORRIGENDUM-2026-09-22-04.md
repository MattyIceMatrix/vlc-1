# Corrigendum 4 to VLC-1 1.1.1-draft

**Issued:** 2026-09-22
**Findings:** EXT-009 to EXT-014. Full entries in `FINDINGS-EXTERNAL.md`.

## The first outside contribution

EXT-009 to EXT-011 were reported by babyblueviper1 (invinoveritas) in vlc-1#1,
with reproductions and a tested patch, and fixed by the reporter in #2, merged
as `c002804`. It is the first change to VLC-1 written by someone other than the
maintainer. EXT-013 and EXT-014 were found by the maintainer while testing code
paths the same report identified as unexercised.

## Summary

| | Finding | Change |
|---|---|---|
| EXT-009 | ordinal-mode L2 accepted silent loss | holes must be covered by producer declarations |
| EXT-010 | duplicate member names invisible to L1 | loader refuses duplicates, `NaN` and `Infinity` |
| EXT-011 | a non-object line crashed the checker | reported at VLC-L1-1 |
| EXT-012 | CI could not show a new regression; one workflow could not fail | disclosed expected failures; `pipefail`; levels asserted |
| EXT-013 | `sha256-prev-field` did not link records | each record's `prev` checked against its predecessor |
| EXT-014 | `max_ordinal` could not see loss at either end | bounds declared by the producer, never inferred |

## Normative changes

**VLC-L2-5 clarified.** A final ordinal or high-water mark is a quantity the
producer declares in the delivered set, with the ordinal at which the sequence
starts. It is not computed from the ordinals of records that arrived.

No other normative text changes. The remaining fixes make the checker do what
the specification already required.

## What a previous report may have overstated

A report from the checker before this corrigendum may show a higher level than
the corrected checker assigns, for any log that:

- used `loss.mode: ordinal`, or `produced.kind: max_ordinal`;
- used the `sha256-prev-field` mechanism;
- contained a record with a duplicate member name, `NaN` or `Infinity`.

No shipped adapter used the first two. The third affects any log.

## Tests

`selftest.sh` now runs every chain mechanism and produced-count kind, the
Annex A mutations against a second adapter, and the reporter's seven cases.
Under both `sh` and `bash`: 68 pass, 2 disclosed expected failures, 0 fail. The
two are the reference implementation's captured journals, per Corrigendum 2.
Both workflows now fail on a new regression, and a known failure marked
expected fails the suite if it fails for any other reason or starts passing.

## Open

- The two captured journals, until the Sentinel sensor counts events only and
  writes explicit loss intervals, and is re-run.
- Reconciliation remains set-level and does not compare multiplicity.
- #3, anchoring VLC-L1-1 to an independently held root or head, in review.

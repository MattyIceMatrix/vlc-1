# Corrigendum 3 to VLC-1 1.1.1-draft

**Issued:** 2026-09-22
**Reported by:** pipavlo82, in an independent review of the published archive.
Full entries in `FINDINGS-EXTERNAL.md`, EXT-004 to EXT-008.

## Summary

| | Finding | Change |
|---|---|---|
| EXT-004 | VLC-L5-4, classed structural, read attested requirements | scored on structural requirements only |
| EXT-005 | reconciliation reported agreement without valid evidence | validity separated from agreement; full exec paths |
| EXT-006 | seven obligations checked for presence, not type | each checked as SPEC states it; fixture corrected |
| EXT-007 | manifest entries could fail open; digest representation unstated | malformed entries fail; VLC-E-6 added |
| EXT-008 | L1 described as rewrite resistance | summary corrected; requirement unchanged |

## Normative changes

**VLC-E-6 added** (Annex E): a manifest digest is `sha256:` followed by 64
lowercase hex, computed over LF-normalized bytes, and a release archive SHALL
carry those bytes.

**§4 summary corrected.** VLC-L1-1 is unchanged; its summary and the "what L1
does not give you" paragraph now say that without an independently held root a
verifier establishes chain consistency only.

No other normative text changes. Every other fix makes the checker do what the
specification already required.

## What a previous report may have overstated

A report produced by the 1.1.1-draft checker before this corrigendum may show a
higher level than the corrected checker assigns, for any log that:

- declared loss without an interval, with a negative count, or over records it
  delivered;
- omitted a coverage category, or carried a later coverage declaration without
  a basis;
- recorded a policy change without both digests, or bound policy per record with
  an event missing its digest;
- relied on a replay reference without declaring determinism;
- relied on an evidence entry that was malformed, had a malformed digest, or
  named no negative control.

A reconciliation run that reported agreement under `--require-agreement` before
this corrigendum should be re-run: it may have been over empty or unverified
input.

## Tests

`selftest.sh` gains three sections — adapter invariance, typed obligations, and
the evidence manifest — and four reconciliation controls. Every new control
fails against the checker it replaces. Totals: 43 of 46 pass. The three that do
not are the reference implementation's captured journals, per Corrigendum 2.

## Open

- The reconciler is set-level and does not compare multiplicity.
- A GAP record's interval is positional; an explicit range would be stronger.
- The Sentinel sensor should write an event-only produced count and explicit
  loss intervals, after which fresh captures can replace the three that fail.
- L3-1d basis on a witness no longer counts against VLC-L5-4 (EXT-004). If it
  should, that is a separate attested requirement.

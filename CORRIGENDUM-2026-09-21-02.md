# Corrigendum 2 to VLC-1 1.1.1-draft

**Issued:** 2026-09-21
**Applies to:** VLC-1 1.1.1-draft, `conformance.py`, `examples/make_examples.py`,
`adapters/plain-jsonl.json`
**Reported by:** pipavlo82 (trustless-ai/recompute-kit), in an independent
review of the published archive, 2026-09-21. Credited by name with permission.

---

## EXT-003 — the completeness identity ran over the wrong record class

**Severity: the identity could be satisfied by a log with a deleted event.**

### What was wrong

SPEC **VLC-L2-5** states the identity over event records:

```
  |delivered event records| + sum(loss declarations) == |records produced|
```

`check_l2` computed `non_event` from the adapter and then never used it. The
delivered count excluded only `marker_classes`, so every other bound record —
coverage declarations, loss declarations, epoch boundaries — was counted as a
delivered event.

Two consequences, one of them serious.

**A loss declaration was counted twice.** A `DROP` record appeared in the
delivered count *and* its `lost` field appeared in `sum(loss declarations)`,
on opposite sides of the same equation.

**A deleted event could be masked one-for-one.** Because framing records
counted toward `delivered`, a producer could remove a real event and emit an
additional framing record in its place. The totals close and the checker
reports the log complete. Demonstrated: a fixture of 60 inference events with
one event deleted and a second `COVERAGE` substituted returned

```
  ok   [S]  VLC-L2-5     61 delivered + 0 declared lost == 61 produced
```

from the shipped checker. After the fix the same log returns

```
  FAIL [S]  VLC-L2-5     identity does not close: 59 + 0 = 59 != 61 produced
```

This is the failure L2 exists to detect. A producer that can mint framing
records at will could defeat it without touching the hash chain.

### Why it was not caught

`adapters/sentinel.json` and `adapters/generic-appjsonl.json` already declared
`COVERAGE`, `EPOCH`, `GAP` and `POLICY` as `non_event_classes`. **The adapters
were correct and the checker ignored them.** `adapters/plain-jsonl.json` did
not declare them, and `examples/make_examples.py` computed the produced count
as `n_events + n_extra`, encoding the same wrong interpretation. Generator and
checker therefore agreed with each other while both disagreed with the
normative formula — the pattern the reviewer was looking for, and found.

The existing Annex A mutations did not catch it because each lowers the level
through earlier L1 mechanics, so none of them exercises the identity in
isolation.

### The correction

`check_l2` excludes `non_event_classes` from the delivered count. The generator
writes `records: n_events`. `adapters/plain-jsonl.json` declares `COVERAGE` and
`DROP` as non-events. No SPEC text changes: the specification was already
correct and the implementation did not follow it.

### What this breaks, and why that is not fixed silently

The reference implementation's captured journals were written by a sensor that
counts framing records in its `HEAD.records` field. `kernel-witness-L5.jsonl`
carries 75 event records and declares 78 produced. Under the corrected rule the
identity does not close and the capture drops from L4 to L1.

**Those captures cannot be corrected in place.** The count is inside a
hash-chained record; editing it breaks the binding. That is the property
working on the project's own evidence, and it is the reason this corrigendum
does not quietly adjust them.

The migration is:

1. correct the Sentinel sensor so `HEAD.records` counts event records only;
2. re-run it to produce fresh captures;
3. retain the existing captures, marked as written under the pre-EXT-003
   interpretation, rather than reissuing them.

Until step 1 lands, `selftest.sh` section 5 fails against those three files,
and that failure is accurate.

### Prior-art and credit note

The reviewer identified the counting mismatch and the generator/checker
agreement. The substitution attack above was constructed while confirming the
report and is a consequence of what was reported, not a separate finding.


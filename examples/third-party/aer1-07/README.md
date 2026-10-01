# AER-1 -07 Section 7 chain: VLC-1 cases rerun

Run 2026-10-01 against the reference Python verifier's `verify_chain_v07()` at kit
commit `aff1330` (captured by `aer1-fetch` in `capture/runs/aer1-20261001T090819Z`,
together with `draft-zambo-aer1-07.txt`). Python only; the other six implementations
were not run. Output: `results-kit-aff1330.txt`.

**The eight -06 gaps are closed.** All 14 original cases now give the result the
-07 text calls for. The one that still verifies (drop the newest entries, set
`close: true` on the new last one) is the trailing-truncation limit Section 7.3
states outright.

**Three new results contradict the Section 7 text.** The last entry's digest is
referenced by no later entry, so editing its output bytes, provenance class, tool or
id verifies. Section 7 says relabeling "breaks the links and is detectable by
recomputation"; that holds for every entry except the last. It is the same root as
the 7.3 limit (drop the last entry and append a forged one), but it needs no removal,
and a manifest that binds only the step *count* (one of the 7.3 options) does not
catch it. Only a commitment to the final entry digest does.

**One spec/code mismatch.** Section 7.1 says `seq` 1 and 1.0 are equivalent and both
accepted; the Python verifier rejects 1.0 ("seq is not an integer").

Also noted: `https://zambo.dev/aer1/test-vectors/index.json` still reports
`"spec_revision": "-06"` and version 1.3.2.

26 of 30 cases as expected; 4 contradict the text. One run of one implementation, not
confirmed by the author.

## Recheck, 2026-10-01 11:56Z (kit `e1430ec`, draft -08)

- -08 (GitLab raw; not yet on ietf.org) adds the Section 7.3 guidance that the outside
  commitment SHOULD bind the final entry digest. That answers the three last-entry
  results above; they still verify on the chain alone, as -08 says they will.
- `seq` 1.0: still rejected by `verify_chain_v07()` at `e1430ec`. The kit's own new
  vector `v07-seq-float-valid` fails its own Python conformance run (CHAIN-V07 18/19,
  `their-conformance-e1430ec.txt`). Commit `6f6a060`, named as the fix, is not what
  main serves. Once 1.0 is accepted, Section 7.1 also requires the digest to serialize
  it as `1`; Python's `json.dumps` writes `1.0`.

## Recheck, 2026-10-01 12:20Z (kit `1b3e3ee`): two Python verifiers

The kit has two Python implementations of the -07 chain check. `aer-1/conformance.py`
accepts `seq` 1.0 and normalizes it to `1` before hashing (lines 244 and 414-415,
from `6f6a060`, which was already in `e1430ec`), and passes `v07-seq-float-valid`
(19/19, as the author reports). `aer1-implementations/python/verifier.py`, the one in
the seven-language set that this harness and its `conformance.py` use, still rejects
1.0 (line 174) and fails that vector (18/19). The 11:56Z note above, that `6f6a060`
was not on main, was wrong: it was on main, in the other file.

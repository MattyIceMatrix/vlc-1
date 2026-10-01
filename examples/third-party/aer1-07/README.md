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

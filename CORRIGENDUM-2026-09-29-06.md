# Corrigendum 6 to VLC-1 1.4-draft — issued as 1.4.1-draft

**Issued:** 2026-09-29
**Findings:** EXT-022 to EXT-025, from an internal review on 2026-09-29.
Full entries in `FINDINGS-EXTERNAL.md`.

## No normative requirement is added or changed

Every change below repairs the checker so that it does what §8.4 and VLC-V-3
already said it did. **Published results move**, and this corrigendum says so
first, because a correction that hides its consequences is the thing this
specification exists to refuse.

## What moved

| Log | 1.4-draft (structural / attested) | 1.4.1-draft | With `--expect-head` |
|---|---|---|---|
| `reference-impl/kernel-witness-L5.jsonl` (observer adapter) | L4 / L5 | **L0 / L0** | L1 / L1 |
| `reference-impl/kernel-witness-with-loss-L5.jsonl` | L4 / L5 | **L0 / L0** | L1 / L1 |
| `third-party/jidec-ledger-chained.jsonl` | L1 / L1 | **L0 / L0** | L1 / L1 |
| `L0-plain` … `L4-policybound` (app-layer examples) | unchanged | unchanged | — |
| k8s-audit, CloudTrail, MCP, OpenShell, auditd samples | L0 / L0 | unchanged | — |

The reference implementation's journals no longer reach L2 or above. Its end
marker is declared `self_bound: false`: the chain does not cover it, so the
head it names and the produced count it carries can be edited without
recomputing any hash. They will return when the sensor binds its end marker
into the chain. Until then, **no claim of L4 or L5 for those journals should
be repeated**, including in material outside this repository.

## What was wrong

- **EXT-022, unbound end marker.** Deleting the last five events, copying the
  previous record's hash into the end marker and lowering its counts by five
  scored structural L4 / attested L5. No hash had to be recomputed. VLC-L1-3
  and the L2 produced count were read from a record the binding does not
  cover. Now VLC-L1-3 passes on an unbound marker only against a head supplied
  from outside the log, and the produced count is taken only from a bound
  record.
- **EXT-025, adapter raising the structural level.** Changing only the
  adapter moved `L2-looks-complete.jsonl` from structural L2 to structural L4:
  L3-1a pointed at an existing record class, L4-1 in `chain_root` mode on the
  chain's own hash, and L3-6/L4-1 passing on the adapter's word. This broke
  VLC-V-3, the one promise the two-number report exists to keep. Those paths
  now fail. One residual case, a relabelled record that no other role claims
  still reaching structural L3, is kept as a disclosed expected failure in
  `selftest.sh` §18. Every report pins `adapter_sha256`, so the mapping a level
  rests on is always named.
- **EXT-023, crashes instead of verdicts.** An empty log, a non-integer count
  and a malformed adapter raised exceptions, and `int(3.7)` read as 3. They now
  produce reports. Exit codes are 0 when a run completes, 1 when an expectation
  is not met, and 2 for usage, adapter or input errors.
- **EXT-024, lossy decoding.** Lines were decoded with `errors="replace"`, so
  different invalid bytes hashed identically. Decoding is now strict: an
  undecodable line fails VLC-L1-1 and is named.

## Also corrected

- `check()` is an importable function, and the module-level `EXPECT` global is
  gone.
- `proofs/sentinel_interval.v` no longer says it models the identity "exactly
  as the checker computes it". It models the ordinal form; the checker's
  default is a count identity.
- `sentinel_object.v` and `govern_concrete.v` are cited but not in this
  repository, and are now marked so. `selftest.sh` §16 scans `.v` and `.json`
  files for citations as well as `.md` and `.py` files.

`selftest.sh` gains sections 17–19 and passes under `sh` and `bash`, with one
expected failure, disclosed.

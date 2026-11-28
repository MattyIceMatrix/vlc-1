# v1.1.0 — L2 loss accounting for real operator ledgers

*Paste this as the release body when drafting the `v1.1.0` release
(RELEASING.md, "Later releases"). Everything below is on `main` and CI-green.
Package `vlc-check` 1.1.0 carries the reference checker at spec 1.4.9-draft.*

---

**Why this release:** `vlc-check` 1.0.0 grades L1 (tamper-evidence) and the
older L2 forms, but refuses the windowed L2 adapters built with the first
operator to walk to L2 (the JIDEC ledger, vlc-1 PR #12): "unknown loss.mode
'windowed_declaration'". 1.1.0 makes that a plain `pip install`.

## Added since 1.0.0 (all opt-in adapter forms; no existing result moves)
- **Windowed completeness declarations** (1.4.6-draft): the producer declares
  `production_count {from, to, received, refused, lost}` per window inside a
  chained checkpoint; the checker closes each window, requires the windows to
  tile, and reports a contiguous tail as awaiting declaration.
- **Record binding** (1.4.7-draft, EXT-033): a record bound one step removed
  (entry hash covers a digest, the digest is sha256 of the record bytes as
  delivered) is verified, then read under `@record`.
- **Signed declarations** (1.4.7-draft): a checkpoint must be signed by a
  ledger key that a statement signed by the operator key, pinned with
  `--operator-key`, named earlier in the chain.
- **Head cross-check** (1.4.7-draft): the head a checkpoint seals is the last
  entry of the window it declares.
- **Non-JSON records** (1.4.8-draft, EXT-034): `record_binding.non_object:
  "bind_only"` keeps Markdown and other plain-text records bound, without
  reading them.
- **First-window refusal boundary** (1.4.9-draft):
  `loss.refused_complete_since_field`, for a ledger whose first declared
  window starts before refusals were counted.

## Fixed since 1.0.0
- EXT-032: windowed declarations counted the end marker as a record.
- EXT-034: one plain-text record made a whole record-bound export unreadable.

Both reported by the JIDEC operator (The HORIZONs Co., Ltd.), credited in
`FINDINGS-EXTERNAL.md`.

## Verified
`selftest.sh` PASS (240 ok, 3 disclosed expected failures), the parity sweep
and all three differential fuzzers; the operator's fourteen synthetic trails
grade as their independent verifier does on thirteen, and the fourteenth
differs by design.

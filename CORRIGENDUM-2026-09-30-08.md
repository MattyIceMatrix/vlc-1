# Corrigendum 8 to VLC-1 1.4.3-draft — issued as 1.4.4-draft

**Issued:** 2026-09-30
**Findings:** EXT-027, from the invinoveritas verdict-ledger capture of 2026-09-30
(`examples/third-party/invinoveritas-ledger-live/`, #16). Full entry in
`FINDINGS-EXTERNAL.md`. The mechanism was contributed by the ledger's operator,
babyblueviper1, in #17, and reviewed here before merge.

## No normative requirement is added or changed

VLC-L1-1 to VLC-L1-4 read as before. The reference checker gains one mechanism,
`sha256-hex-join`, and one end-marker option, `content_json_field`; SPEC.md §4.1
describes both. **Two published results move**, listed first.

## What moved

| Log | 1.4.3-draft (structural / attested) | 1.4.4-draft | Why |
|---|---|---|---|
| `third-party/invinoveritas-ledger-live-full.jsonl`, log alone | L0 / L0 | L0 / L0 | unchanged: the signed head event is not a chain link, so VLC-L1-3 needs a head held outside the file |
| the same, with `--expect-head` = the head its signed Nostr event states | L0 / L0 | **L1 / L1** | the checker now recomputes all 230 links and reaches that head |
| `third-party/invinoveritas-ledger-live-truncated.jsonl` (newest entry dropped), with that head | L0 / L0, identical to the full file | **L0 / L0, VLC-L1-1 fails** | the truncation is now detected against the held head |
| `third-party/jidec-ledger-chained.jsonl`, log alone | L0 / L0 | **L1 / L1** | a new live capture after the operator bound its `jidec-head-v1` end marker into the chain (#12, closing EXT-022 for this ledger); the 2026-09-28 capture is kept unchanged as `jidec-ledger-chained-unbound` and still scores L0 on the log alone, L1 against its stamped head |
| every other log in this repository | unchanged | unchanged | `sha256-hex-join` is a new branch; no existing check was edited |

Both ledgers stop at L1 for real: neither states what was issued against what was
written (loss), what should have been recorded (coverage) or the rules that
admitted an entry (policy), and each operator writes its own entries (VLC-L5-1).

## What was wrong

- **EXT-027, a chain over carried digests had to be declared `none`.** The
  invinoveritas ledger hashes each full record once (`content_hash`) and chains
  only the digests: `head_hash = SHA-256(content_hash + "|" + prev_head_hash)`.
  None of the checker's mechanisms computes that, so the adapter declared `none`
  rather than reshape rows into a pass, and the file with its newest entry dropped
  scored exactly as the full one, although `verify_ledger.py` rejects it against
  the signed head.

## What was added

- **`integrity.mechanism: "sha256-hex-join"`.** Each record's hash is
  SHA-256(`content_field` + `separator` + hex(previous head)), over lower-case hex
  strings as UTF-8; a `content_field` value that is not 64 lower-case hex
  characters is unrecomputable. An optional `prev_field` is checked against the
  recomputed predecessor. The root is the adapter's constant.
- **Class pinning.** The hash covers `content_field` only, so the record class is
  outside the binding. With `record_class_field` set, the adapter must declare
  `integrity.link_class`; every record before the end marker must carry it, and
  only the final record may carry the end-marker class. A relabelled interior
  record fails VLC-L1-1. (Found in review of #17; condition 1 of #3.)
- **`end_marker.content_json_field`.** The end marker's head may sit inside a
  string member holding JSON, as in a Nostr event's `content`. It is parsed with
  the same I-JSON rules as the log: a duplicate member name or a non-finite number
  makes the delivered set unreadable. The marker's signature is not verified, so
  such a marker is `self_bound: false` and VLC-L1-3 needs `--expect-head`.
- **What the checker does not do.** It recomputes the chain over the delivered
  digests; it does not recompute `content_hash` from the full records, which are
  not in the file. For the invinoveritas capture that was done on the runner
  (`recompute.jsonl` on branch `capture/invinoveritas-ledger`).

## Controls

`examples/mechanism_cases.py` gains 10 `hex-join-*` vectors, run by `selftest.sh`
§2b: honest chain; unbound marker without a held head; content edited; interior
entry deleted; entries reordered; predecessor substituted; non-hex digest;
interior entry relabelled to the end-marker class; relabelled to an unknown class;
duplicate member name in the marker's JSON. CI asserts the invinoveritas ledger at
L0 on the log alone, L1 full and L0 truncated with its signed head, the JIDEC
bound capture at L1 on the log alone, and keeps the `verify_ledger.py` checks.
Before merge the maintainer also ran eleven attacks against the real capture with
the signed head (both relabels, class removed, duplicate key, NaN, marker moved,
doubled or relabelled, JSON list content, truncation, upper-case digest); every
one fails.

This version needs a 1.4.4-draft release and version DOI, which the maintainer
issues; none is cited here until it exists.

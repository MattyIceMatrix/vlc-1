# Corrigendum 7 to VLC-1 1.4.2-draft — issued as 1.4.3-draft

**Issued:** 2026-09-30
**Findings:** EXT-026, from the Trillian Tessera live capture of 2026-09-30
(`examples/third-party/tessera-live/`). Full entry in `FINDINGS-EXTERNAL.md`.

## No normative requirement is added or changed

VLC-L1-1 to VLC-L1-4 read as before. What changes is the set of mechanisms the
reference checker can recompute: it gains `merkle-tlog`, and SPEC.md gains §4.1,
draft text stating how a verifier decides clause 4 for it. **One published
result moves**, and this corrigendum says so first.

## What moved

| Log | 1.4.2-draft (structural / attested) | 1.4.3-draft | Why |
|---|---|---|---|
| `third-party/tessera-live-full.jsonl` | L0 / L0 | **L1 / L1** | the RFC 6962 root recomputed over the six entries equals the signed checkpoint's; the Ed25519 signature verifies under `log.vkey` |
| `third-party/tessera-live-scrubbed.jsonl` (one entry removed) | L0 / L0, identical to the full file | **L0 / L0, VLC-L1-1 fails** | the removal is now detected; up to 1.4.2-draft the two files scored the same |
| every other log in this repository, under every other mechanism | unchanged | unchanged | `merkle-tlog` is a new branch; no existing check was edited |

The full file stops at L1 on VLC-L2-2 and VLC-L2-4 (no loss declaration, no
declared overflow behaviour) and fails coverage (L3), policy (L4) and
independence (VLC-L5-1) for real: the log binds whatever bytes it is given, and
in this capture one job wrote the entries and held the signing key.

## What was wrong

- **EXT-026, a Merkle transparency log scored with logs that have no binding.**
  Every integrity mechanism `conformance.py` could recompute was a hash chain.
  A C2SP tlog-tiles log with a signed checkpoint, as Trillian Tessera v1.0.4 and
  Sigstore's Rekor v2 produce, had to be declared `none`: declaring a chain
  mechanism would have manufactured a pass. It therefore scored L0, and the file
  with the refused `delete_file` entry removed scored exactly as the full one,
  although a standard-library verifier (`verify_tlog.py`) rejects it. The gap was
  in the checker, not in the log.

## What was added

- **`integrity.mechanism: "merkle-tlog"`.** The entries, in log order, are the
  leaves (SHA-256(0x00 ‖ the adapter's `leaf_field`, as UTF-8 or base64-decoded
  bytes)); interior nodes are SHA-256(0x01 ‖ left ‖ right) with the RFC 6962 §2.1
  split. The last record is the checkpoint, the end marker: its tree size and
  root must equal the count and root recomputed from the entries, every earlier
  record must be an entry, and a mapped `index_field` must equal the leaf
  position. Removing, altering, inserting, reordering or truncating any entry
  fails VLC-L1-1; a checkpoint dropped with the tail fails VLC-L1-3.
- **Anchors.** `--expect-head` takes the root of a checkpoint held for the
  delivered size; `--expect-root` the root of a checkpoint held for an earlier
  size, which a prefix of the entries must produce. A tail cut and re-sealed by
  the key holder passes on the log alone, as a rewritten chain does, and fails
  against either held checkpoint.
- **Checkpoint signature.** Verified only when the adapter supplies
  `integrity.verifier_key` (a C2SP signed-note Ed25519 key) and maps the note
  (`end_marker.note_field`). Otherwise the report records
  `checkpoint_signature: "not performed: …"` and nothing is credited. The
  verifier is the RFC 8032 §6 Python reference code, vendored in
  `conformance.py` with its attribution, standard library only; it is checked
  against RFC 8032 test vectors 1 and 2 and against the Go-signed Tessera
  checkpoints.

## Controls

`examples/mechanism_cases.py` gains 26 `merkle-tlog` vectors, run by
`selftest.sh` §2b: valid; entry removed (with and without renumbering); entry
altered; entries reordered; tail cut with the checkpoint kept, dropped, and
re-sealed, against held head and held root; prefix rewritten against a held
root; wrong root, signed and unsigned; signature altered; wrong verifier key;
fields edited beside the note; no verifier key (not performed, not credited);
unanchored read field; relabelled interior record. `selftest.sh` §20 runs the
Ed25519 known answers and the Annex A mutations on the live Tessera log. CI now
asserts Tessera full L1, scrubbed lower with VLC-L1-1 failed, and the held
checkpoint anchors, and keeps the `verify_tlog.py` checks.

The maintainer issued the 1.4.3-draft release and its version DOI on 2026-09-30:
**[10.5281/zenodo.23063984](https://doi.org/10.5281/zenodo.23063984)**.

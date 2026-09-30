# A tile-based transparency log, live (positive control)

Captured 2026-09-30 on a GitHub-hosted runner (ubuntu-24.04, go1.27.1) by
`.github/workflows/falco-rekor-capture.yml` on branch `capture/falco-rekor`, run
`run-20260930T112902Z`. The log was built with **Trillian Tessera v1.0.4**
(`go install .../tessera/cmd/examples/posix-oneshot@latest` resolved to v1.0.4;
`posix-oneshot.buildinfo.txt`), the library Sigstore's Rekor v2 is built on
(`sigstore/rekor-tiles` go.mod on main requires `github.com/transparency-dev/tessera
v1.0.4`). It is a C2SP tlog-tiles log on the local filesystem, **not** a Rekor
deployment: no Rekor entry types, no Sigstore signing, no witnesses.

## What was done

`capture/scripts/tessera.sh` generated an Ed25519 note key for the origin
`vlc-1.capture/tessera-live` (kept: `log.vkey`; the signing key was not kept) and
appended six JSON audit statements (`entry-files/`) in two rounds of three with
`posix-oneshot`, which printed the index it assigned each one (`round*.stderr.txt`:
0-2, then 3-5). The checkpoint after round 1 (`checkpoint.round1`, size 3) was kept
as a verifier holding an earlier checkpoint would keep it; `log/checkpoint` is size 6.
Then `capture/scripts/tlogcap.go`, built against the same Tessera version, used
Tessera's `client.ProofBuilder` to build from the tiles an inclusion proof for every
entry against the size-6 checkpoint and a consistency proof from size 3 to size 6,
and verified them with `transparency-dev/merkle/proof`:

- `verify.jsonl`: both checkpoint signatures, 6 inclusion proofs and the consistency
  proof verified.
- `verify-tampered.jsonl`: the same on a copy of the log with one byte of the first
  `"deny"` in the entry bundle flipped: the inclusion proof of that entry (index 2)
  failed; the others and the consistency proof, which are built from the hash tiles,
  still verified.

`verify_tlog.py` (standard library only; Ed25519 per RFC 8032, Merkle hashing per
RFC 6962, proof verification per RFC 9162 section 2.1) repeats this independently of
Tessera's code: signatures, RFC 6962 root over the entries equal to the signed root,
level-0 tile equal to the leaf hashes, the size-3 checkpoint equal to the root of the
first three entries, and every proof in `verify.jsonl`. It passes on the log and on
`tessera-live-full.jsonl`, and fails on `tessera-live-scrubbed.jsonl` (the refused
`delete_file` statement removed): signed size 6 against 5 entries, an index gap, root
mismatch. CI runs all three.

## Score, and why it is not higher

**Under 1.4.3-draft (`merkle-tlog`, EXT-026): the full file scores structural L1 /
attested L1; the scrubbed file scores L0 and fails VLC-L1-1** ("record 2: 'index' is
3, but it is leaf 2 of the delivered tree"; with the survivors renumbered it fails on
the size, and with the size also changed on the root or the signature). The checker
recomputes the RFC 6962 root over the entries' `data`, requires the checkpoint's size
and root to equal it and the ones in the signed note, and verifies the note's Ed25519
signature under `log.vkey` (report field `checkpoint_signature`). The full file stops
at L1 on VLC-L2-2 and VLC-L2-4 (no loss declaration, no declared overflow behaviour),
and then fails VLC-L3-1a, L3-6, L4-1, L5-1 and L5-3/4/5/6: coverage, policy and
independence fail for real.

Held checkpoints anchor it as `--expect-root` / `--expect-head` do a chain:
`checkpoint.round1`'s root (hex `d1d2ed15...6519`) given as `--expect-root` must be the
root of a prefix of the delivered entries, and the size-6 root as `--expect-head` must
equal the recomputed root; CI checks both, and that the size-3 root is refused as a
head.

**Up to 1.4.2-draft** both files scored **L0**, on the same 13 failed requirements
(VLC-L1-1/2/3, L2-1, L2-3, L3-1a, L3-6, L4-1, L5-1, L5-3/4/5/6), and the scrubbed file
scored exactly as the full one -- the result every agent log in `THIRD-PARTY.md` got,
for a log whose removal of that one entry is detected by the verifier above. The
reason was the checker, not the log: the integrity mechanisms `conformance.py` could
recompute were all hash chains (`none`, `sha256-chain-prefix`,
`sha256-chain-canonical`, `sha256-prev-raw`, `sha256-prev-field`,
`sha256-canonical-fields`). The adapter declared `none` rather than a chain mechanism,
which would have manufactured a pass. This capture is the source of EXT-026 and of
`merkle-tlog`.

Requirement by requirement, as far as this capture shows:

| requirement | checker (1.4.3-draft) | what the capture shows outside the checker |
|---|---|---|
| VLC-L1-1 binding recomputes, rewrite detectable | PASS (merkle-tlog; rewrite by the key holder detectable only against a held checkpoint) | root recomputed from the entries equals the signed root; a consistency proof from a checkpoint held separately detects a rewrite |
| VLC-L1-3 truncation detectable | PASS | the checkpoint signs the size; a short delivered set fails |
| VLC-L2-1 production count | PASS (size read from the recomputed checkpoint) | the signed size is a production count, indices are contiguous from 0 |
| VLC-L2-2 / L2-4 loss declaration, overflow behaviour | FAIL | an entry lost before sequencing leaves no trace (Tessera README) |
| VLC-L3 coverage, VLC-L4 policy | FAIL | nothing: the log binds whatever bytes it is given, and says nothing about what should have been submitted or under which rules |
| VLC-L5-1 independence | FAIL (declared `self_reported`) | in this capture one job wrote the entries, held the key and could rewrite the directory; no witness policy was configured |

The checker does not read the inclusion or consistency proofs; it recomputes the whole
tree instead. `verify_tlog.py` checks the proofs.

## Files

- `convert.py` -- `python3 convert.py log [--scrub]`; builds one `entry` record per
  entry (index, data) and the `checkpoint` record (the note verbatim, plus its
  origin, size and root); `--scrub` removes the `delete_file` entry.
- `verify_tlog.py` -- `log DIR VKEY [OLD] [--proofs FILE]` or `jsonl FILE VKEY`.
- `log/` -- the log as Tessera wrote it (`checkpoint`, `tile/entries/000.p/{3,6}`,
  `tile/0/000.p/{3,6}`); its `.state/` directory (Tessera's internal state, not part
  of the tlog-tiles read API) was not uploaded by the capture job, which skips hidden
  files.
- `checkpoint.round1`, `log.vkey`, `verify.jsonl`, `verify-tampered.jsonl`,
  `round1.stderr.txt`, `round2.stderr.txt`, `posix-oneshot.buildinfo.txt`,
  `entry-files/`.

```sh
python3 convert.py log         > ../tessera-live-full.jsonl
python3 convert.py log --scrub > ../tessera-live-scrubbed.jsonl
python3 verify_tlog.py log log log.vkey checkpoint.round1 --proofs verify.jsonl
```

## Not established

One run, six entries, one checkpoint signer. Rekor v2 itself, witnessing, and a log
under load were not captured. Not confirmed by the Tessera or Sigstore maintainers.

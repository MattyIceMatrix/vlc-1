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

Both files score **L0** in `conformance.py`, on the same 13 failed requirements
(VLC-L1-1/2/3, L2-1, L2-3, L3-1a, L3-6, L4-1, L5-1, L5-3/4/5/6), and the scrubbed file
scores exactly as the full one -- the result every agent log in `THIRD-PARTY.md` got,
for a log whose removal of that one entry is detected by the verifier above.

The reason is the checker, not the log: the integrity mechanisms `conformance.py`
(VLC-1 1.4.2-draft) can recompute are hash chains (`none`, `sha256-chain-prefix`,
`sha256-chain-canonical`, `sha256-prev-raw`, `sha256-prev-field`,
`sha256-canonical-fields`). A Merkle tree with a signed tree head is none of them.
The adapter therefore declares `none` and describes the real mechanism in
`integrity.actual_mechanism`; converting the log into a hash chain, or declaring a
chain mechanism, would manufacture a pass. With integrity at `none` the checker also
cannot treat the checkpoint's size as anchored (VLC-L2-1 fails as "end marker not
bound by the chain") even though it is signed.

Requirement by requirement, as far as this capture shows:

| requirement | checker | what the capture shows outside the checker |
|---|---|---|
| VLC-L1-1 binding recomputes, rewrite detectable | FAIL (no mechanism) | root recomputed from the entries equals the signed root; a consistency proof from a checkpoint held separately detects a rewrite |
| VLC-L1-3 truncation detectable | FAIL | the checkpoint signs the size; a short delivered set fails |
| VLC-L2-1 production count | FAIL (end marker unbound) | the signed size is a production count, indices are contiguous from 0 |
| VLC-L3 coverage, VLC-L4 policy | FAIL | nothing: the log binds whatever bytes it is given, and says nothing about what should have been submitted or under which rules |
| VLC-L5-1 independence | FAIL (declared `self_reported`) | in this capture one job wrote the entries, held the key and could rewrite the directory; no witness policy was configured |

So on integrity this log is clearly stronger than every agent log scored so far (none
of which carries any integrity binding), and
the rubric as implemented cannot say so: it scores it with them. It fails coverage
and policy for real. It did not come near L5, so the capture raises no question of
the rubric over-scoring it; the question it raises is the opposite one (no Merkle
mechanism in `conformance.py`).

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

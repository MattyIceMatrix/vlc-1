# SYNTHETIC: the JIDEC ledger's real export shape, graded natively

**Everything in this directory is synthetic.** The fourteen trails under
`trails/` were built by **The HORIZONs Co., Ltd.**, the JIDEC ledger's operator,
with their own builder, and sent for [vlc-1 PR #12](https://github.com/MattyIceMatrix/vlc-1/pull/12)
on 2026-11-28 under the MIT licence. Test keys come from fixed seeds. No byte is
output of the JIDEC ledger.

The sibling example `jidec-l2-checkpoint-shape-synthetic/` models the settled L2
design in **our** template's shape. This one is the operator's **real** shape:
the entry hash covers `claim_sha256`, and the record behind it (the checkpoint
with its declaration, the key statement) is carried on the export line as
`record_canonical`. Bound one step removed, so no entry hash changes.

## What 1.4.7-draft added to grade it (EXT-033)

All opt-in; an adapter without these blocks grades exactly as before.

| adapter block | what the checker verifies |
|---|---|
| `record_binding` | sha256 of `record_canonical`, **as delivered** (no re-canonicalization), equals `claim_sha256`; only then is the record read under `@record`. A mismatch is L0. `@record.…` counts as anchored only while `claim_sha256` is in `hash_fields`. |
| `signatures` (`key_statement_hop`) | a key statement signed by the operator key, **pinned out of band** with `--operator-key`, names a ledger key; every checkpoint is signed by a ledger key named earlier in the chain. Fails VLC-L2-3 otherwise. |
| `loss.head_n_field`, `loss.head_hash_field` | the head a checkpoint seals is entry `to` of the window it declares: `ledger_head.n == to`, and `ledger_head.entry_sha256` is the hash of entry `to`. Fails VLC-L2-2 otherwise. |

## Run it

    python3 examples/third-party/jidec-l2-real-shape-synthetic/check_real_shape.py

It checks each export against the operator's `index.json` (byte for byte), then
grades it with `conformance.py` and `adapter-l2-record-bound.json`:

| trail | tamper | vlc-1 1.4.7-draft | operator's verifier |
|---|---|---|---|
| `honest` | none | **L2**, tail 18..20 | L2 |
| `declared_loss` | entry lost after its ordinal, declared | **L2** | L2 |
| `undercount` | a window's `received` lowered, resealed | L1, window does not close | L1 |
| `hidden_drop` | entry removed after declaring, resealed, re-signed | L1, window does not close | L1 |
| `tail_gap` | ordinal gap after the last checkpoint | L1, undeclared loss | L1 |
| `unbound_edit` | record bytes edited, `claim_sha256` kept | **L0**, record binding | L0 |
| `sig_stripped` | checkpoint signature removed | L1, VLC-L2-3 | L1 |
| `wrong_key` | checkpoint signed by a key nobody named | L1, VLC-L2-3 | L1 |
| `statement_not_operator` | key statement not signed by the operator key | L1, VLC-L2-3 | L1 |
| `head_mismatch` | `ledger_head.n` is not `to` | L1, head cross-check | L1 |
| `head_hash_mismatch` | `ledger_head.entry_sha256` is not entry `to` | L1, head cross-check | L1 |
| `window_overlap`, `window_gap` | windows do not tile | L1, tiling | L1 |
| `refusal_list_short` | a refusal list one line short | **L2**, by design | L1 with the lists supplied |

The last row is not a miss. The refusal list is its own file; the export carries
only its sha256, so an export-only check cannot see a short list. The operator's
own table on PR #12 says the same.

Controls in the same script: no pinned key, or a different one, fails VLC-L2-3;
dropping `claim_sha256` from `hash_fields`, or the `record_binding` block, leaves
`@record` fields unanchored (L0); a line carrying its own `@record` member is
refused; record bytes re-serialized in sorted key order fail the binding.

## `horizons/`

The operator's builder (`jidec_l2_synth.py`), their verifier written apart from
it (`jidec_l2_verify.py`), the in-process wrapper behind their table
(`run_vlc_bound.py`) and the two runs, exactly as sent; `README_for_vlc1.txt`
lists each file's sha256. Kept for reference and reproduction. **Nothing in
this repository imports or runs them**: the grading above is vlc-1's own code
on their bytes. MIT licence, © The HORIZONs Co., Ltd.

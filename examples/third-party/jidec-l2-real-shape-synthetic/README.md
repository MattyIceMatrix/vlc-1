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
| `record_binding.non_object` (1.4.8-draft, EXT-034) | `"bind_only"`: a record that is not a JSON object (the live ledger's Markdown notes, schema `v0-plain`) is still byte-checked, but not lifted; the line is classed by `unbound_class_field`. Default `"refuse"`. This adapter sets `"bind_only"`. |
| `signatures` (`key_statement_hop`) | a key statement signed by the operator key, **pinned out of band** with `--operator-key`, names a ledger key; every checkpoint is signed by a ledger key named earlier in the chain. Fails VLC-L2-3 otherwise. |
| `loss.refused_complete_since_field` (1.4.9-draft) | the `n` from which a window counts every refusal: `from <= v <= to + 1`, only the first window may exceed its `from`, and `from..v-1` is reported as a stated boundary (no refusal claim), not a loss. Absent means `from`. Named by the operator on PR #12 for the first v2 window. |
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

EXT-034 controls (1.4.8-draft), built from the honest trail by swapping entry
20's record and re-chaining it and the end marker with the operator's recipe:
a Markdown record grades L2 with `"bind_only"` and L0 without it (the
operator's report, reproduced); the Markdown edited with its digest kept is L0;
a JSON array record is L2; duplicate member names are still refused; an
unlifted line classed as the declaration class does not grade L2.

`refused_complete_since` controls (1.4.9-draft): the honest trail rebuilt with
the field in its checkpoints (records edited, the whole chain and each sealed
head recomputed by the operator's recipe; a no-edit rebuild is checked to
reproduce every honest hash first). Graded without the signatures block, since
edited records no longer carry the operator's signatures. First window from 4:
L2 with the boundary stated; from `to + 1`, from each window's own start, or
absent: L2; past `to + 1`, before `from`, a later window not at its `from`, or
not an integer: L1 at VLC-L2-2; the field without `refused_field`: adapter
error. The operator's second set (below) carries the field, signed, and is
the frozen control for it.

## `trails-v1_1/`: the operator's second signed set (2026-11-28)

Sent after 1.4.9-draft (archive sha256 `4a20eda2…fb18f`, MIT, same fixed test
keys). Every checkpoint carries `refused_complete_since`; the fourteen v1
variants keep their names and expectations, and six are new. Kept byte for
byte; each export is checked against the operator's `index.json` first.

| trail | what it does | vlc-1 1.4.9-draft | operator's index |
|---|---|---|---|
| fourteen v1 variants | as above, with the new field | as above | as above |
| `partial_first` | first window counts refusals only from entry 3 | **L2**, "refusals in scope from ordinal 3: 1..2 make no refusal claim" | L2 |
| `complete_since_later_window` | window 2 starts counting after its `from` | L1, VLC-L2-2 | L1 |
| `complete_since_out_of_range` | window 1 says 8, past `to + 1` (7) | L1, VLC-L2-2 | L1 |
| `complete_since_below_from` | window 1 says 0, below `from` | L1, VLC-L2-2 | L1 |
| `plain_note` | entry 4 is a Markdown note, bound and not read | **L2** (`bind_only`, EXT-034) | L2 |
| `plain_note_edited` | the note's bytes changed, digest kept | **L0**, record binding | L0 |

Nineteen of twenty agree with the operator's index; `refusal_list_short`
grades L2 by design, as before. The operator ran vlc-1 at `0833f71` on the
same twenty before sending and got the same. `horizons-v1_1/` holds their
builder, verifier, runs, README and SHA256SUMS exactly as sent; nothing in
this repository runs them.

## `horizons/`

The operator's builder (`jidec_l2_synth.py`), their verifier written apart from
it (`jidec_l2_verify.py`), the in-process wrapper behind their table
(`run_vlc_bound.py`) and the two runs, exactly as sent; `README_for_vlc1.txt`
lists each file's sha256. Kept for reference and reproduction. **Nothing in
this repository imports or runs them**: the grading above is vlc-1's own code
on their bytes. MIT licence, © The HORIZONs Co., Ltd.

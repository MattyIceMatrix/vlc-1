# SYNTHETIC: the jidec-chain-v1 shape, extended to L2

**Everything in this directory is fabricated** by `build_and_check.py`. It is
not the JIDEC ledger's output, and its maintainer has not endorsed it. It is a
concrete, runnable template for the L2 loss-accounting walk discussed in
[issue #12](https://github.com/MattyIceMatrix/vlc-1/issues/12).

## The design, in three additions

The live ledger grades structural L1: the chain holds, the end marker is
bound, but nothing states how many entries were *produced*, so the
completeness identity has nothing to close over. This template closes it with
the smallest extension that **changes no existing entry hash** — possible
because `sha256-canonical-fields` omits absent fields from the hashed object:

1. **`submission_seq`** on each event entry — the producer's intake ordinal,
   assigned *before* anything can be dropped (the ledger's `n` is assigned at
   write time, which is after the losses this identity exists to count).
2. **`jidec-loss-v1`**, a non-event declaration class carrying
   `{lost, from_seq, to_seq}` — an explicit count *and* interval (VLC-L2-2),
   cross-checked by the verifier against the delivered `submission_seq` set.
3. **`produced_count`** on the **bound** end marker — the producer's
   independent figure. Because the marker is bound (EXT-022), the count
   cannot be lowered after the fact without breaking a hash.

The identity the checker closes (VLC-L2-5):

    |delivered event entries| + sum(declared losses) == produced_count

All five new fields join `hash_fields`; historical entries don't carry them,
so their hashes are untouched. Window choice (cumulative vs per-day) is the
operator's trade — the adapter note discusses it; this example uses cumulative.

## Run it

    python3 examples/third-party/jidec-l2-shape-synthetic/build_and_check.py

Builds three trails and asserts the verdicts:

| trail | tamper | verdict |
|---|---|---|
| `trail-l2.jsonl` | none | **structural L2**, attested L1 |
| `trail-l2-overcount.jsonl` | `produced_count` raised by 1 | identity open → L1 |
| `trail-l2-undeclared.jsonl` | loss declaration deleted | identity open → L1 |

The adapter is `adapter-l2-template.json` — the live `jidec-ledger-chained`
adapter plus the `loss` block and the extended `hash_fields`. It is **not
served by the live checker**: it describes a shape no producer emits yet.

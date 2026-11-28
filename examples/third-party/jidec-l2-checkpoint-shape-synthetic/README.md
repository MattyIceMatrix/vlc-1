# SYNTHETIC: the settled JIDEC L2 design, graded end to end

**Everything in this directory is fabricated** by `build_and_check.py` — not
the JIDEC ledger's output, not endorsed by its maintainer. It models the L2
design **settled** in [issue #12](https://github.com/MattyIceMatrix/vlc-1/issues/12)
(2026-11-28), superseding the exploratory template one directory over
(`jidec-l2-shape-synthetic/`, kept for the record):

- the declaration lives **inside the checkpoint entry**, in the same chained,
  stamped record as the head it closes;
- full form from the first window: `production_count {from, to, received,
  refused, lost}` with `received = written-in-window + refused + lost`;
- **the unit is the ledger entry** — checkpoints and witness batches occupy
  ordinals and count as written;
- the day's refusal list is its own file; its sha256 rides in the checkpoint;
- graded with `loss.mode: "windowed_declaration"` (1.4.6-draft), whose tail
  rule answers the operational reality their checkpoint-lag find exposed:
  entries after the last checkpoint are reported as awaiting declaration when
  contiguous, and fail as undeclared loss when gapped.

## Run it

    python3 examples/third-party/jidec-l2-checkpoint-shape-synthetic/build_and_check.py

| trail | tamper | verdict |
|---|---|---|
| `trail.jsonl` | none | **structural L2** |
| `trail-tail.jsonl` | 3 entries after the last checkpoint | **structural L2**, tail reported |
| `trail-undercount.jsonl` | a window's `received` lowered, chain resealed | window does not close → L1 |
| `trail-hidden-drop.jsonl` | entry removed inside a declared window, chain resealed | window does not close → L1 |
| `trail-tail-gap.jsonl` | ordinal gap in the undeclared tail | undeclared loss → L1 |

The adapter (`adapter-l2-checkpoint.json`) is the live `jidec-ledger-chained`
adapter plus the `loss` block and three fields joining `hash_fields` — which
changes **no existing entry hash**, because `sha256-canonical-fields` omits
absent fields. It is not served by the live checker: it describes a shape no
producer emits yet.

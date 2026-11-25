# halo-record Runtime Records — SYNTHETIC trail (not their output)

**Every file here was synthesized by this project on 2026-11-25** to the shape
of halo-record's published schema and sealing recipe (bkuan001/halo-record:
`canon.py` RFC 8785 + SHA-256, `prev_hash`/`hash` under `integrity`, genesis
64 zeros). **None of it was produced by halo-record's own code**, and nothing
here scores that project: it exists so `adapters/halo-runtime-record.json` and
the `sha256-chain-jcs-nested` mechanism have a worked example until the
maintainer supplies a real trail (offered in bkuan001/halo-record#15).

- `trail-synthetic.jsonl` — 8 sealed records (non-ASCII tool name pins the
  RFC 8785 serialization): **VLC-L1-1 PASS; structural L0 on the log alone**,
  because the format carries no in-band end marker — truncation is
  undetectable from the file, which matches halo-record's own statement that
  the chain is integrity, not completeness (completeness lives in its
  external witness).
- `trail-synthetic-tampered.jsonl` — one tool name edited after sealing:
  **VLC-L1-1 FAIL**.

Reproduce:

    python3 conformance.py --log examples/third-party/halo-record-synthetic/trail-synthetic.jsonl \
        --adapter adapters/halo-runtime-record.json

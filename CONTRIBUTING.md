# Contributing

The most valuable contributions, in order:

### 1. Tell us a clause is wrong

Especially: *"VLC-Lx-y is shaped around your implementation."* Annex C of
`SPEC.md` commits to rewording or dropping any clause where that is true. A
specification is worth something only if parties who compete with its author can
adopt it, so this is not a courtesy — it is the acceptance criterion.

### 2. Write an adapter for a format we got wrong, or have not covered

Adapters are **data**. `conformance.py` never executes anything an adapter
supplies. Copy the closest file in `adapters/`, change the field names, add a
`sources` list pointing at the public documentation you worked from, and add a
shape-accurate sample under `examples/third-party/`.

If a scoring in `THIRD-PARTY.md` is wrong because a field name is wrong, fixing
the adapter *is* the correction, and it is a shorter argument than an email.

### 3. Bring a capture

Every sample in `examples/` except `examples/reference-impl/` is synthetic,
because synthetic logs can be made to sit exactly on a rung. Real captures are
better evidence and worse tests. Both are welcome; label which one you are
bringing.

### 4. Break the self-test

`selftest.sh` asserts in both directions: the worked examples must sit exactly on
their rung, every Annex A mutation must lower the level, and the author's own
pre-fix capture must **still fail** at L2. A patch that makes something pass
which used to fail is suspect until it explains which of those three it changed.

---

## Ground rules

- **No claims about closed products.** `THIRD-PARTY.md` scores only open,
  publicly documented formats. A vendor's marketing page is not a specification
  and we will not score one from it.
- **Say what you verified.** "I read the spec" and "I ran it against a capture"
  are different strengths of claim and the difference should be in the text.
- **Negative controls or it didn't happen.** Any new check must be shown to fail
  when the property it tests is absent.

## Running everything

```sh
./selftest.sh
cd proofs && coqc -q sentinel_completeness.v
```

Questions, or a format you want scored: moorematthew131@gmail.com

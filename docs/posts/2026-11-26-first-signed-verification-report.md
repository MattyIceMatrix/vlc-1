# The first signed verification report — and what it took to get here

*2026-11-26 · Matthew Moore ([@MattyIceMatrix](https://github.com/MattyIceMatrix))*

Yesterday VLC-1 became a product. Today it served its first customer-shaped request.
This post documents both, because the 24 hours tell one story.

## What VLC-1 is

Most "tamper-evident" logging answers one question: *were these records altered?*
VLC-1 answers the harder one: ***are these all the records?*** It is a conformance
spec (CC0, 26 requirements, levels L1–L5) and a reference checker that grades any
JSONL log plus a data-only adapter. The completeness identity —
`delivered + declared-lost == produced` under a hash chain — either closes or it
doesn't, and the checker's self-test fails in both directions: fabricated claims
and broken guarantees are both caught.

## What shipped yesterday

- **v1.0.0** — first stable release, with the spec frozen and 7 hash-chain
  mechanisms, including an RFC 8785 (JCS) family on a guarded subset that is
  never misgraded outside it.
- **`pip install vlc-check`** — the reference checker on PyPI, published via
  Trusted Publishing (OIDC, no stored tokens), with an install-and-grade sanity
  check gating every release.
- **GitHub Marketplace** — `uses: MattyIceMatrix/vlc-1@v1` grades your logs on
  every push.
- **Signed reports** — Ed25519 verdicts from a key generated inside the signing
  service and never exported, verifiable offline by a pure-Python verifier
  anyone can read in an afternoon.

The live checker is kept provably exact to the reference by a fixed conformance
matrix, a 300-case differential fuzzer on every push, and parity sweeps across
every served adapter. The fuzzer found five real divergences during development.
None ever shipped a wrong grade.

## What happened this morning

An independent operator — a security company that runs a public, cryptographically
anchored verification ledger — asked for a signed report on their current export.
(They review anything naming them before it is published, so this post names no one;
the technical exchange is public in this repository's issue tracker.)

Within hours, their export was captured in CI (388 entries, sha256 recorded), graded
by the reference checker — **structural L1 / attested L1**: every entry recomputes,
the end marker is bound, and the recomputed head equals the value their own anchored
checkpoints carry — then signed, re-verified offline *before* delivery, and
committed where anyone can re-verify it with two commands and no trust in us:

```
git clone https://github.com/MattyIceMatrix/vlc-1 && cd vlc-1
python3 tools/verify_report.py <verified-report.json>
```

What separates that ledger from L2 is precisely one thing: loss accounting. No
production count is declared, so there is no completeness identity to close. That
is not a flaw in the ledger — it is the spec doing its job: saying exactly what a
log does and does not establish, in a form a third party can check.

## Why this matters

A verification product has a bootstrapping problem: who verifies the verifier?
The answer VLC-1 gives is *nobody has to trust it* — every grade recomputes from
public bytes, every signature verifies offline, every claim names the requirement
it rests on. The first operator to put a real production system through that
process asked for more, not less: a slot for our verifier on their own nightly
verification board, and a joint walk toward L2.

That is the trade this project exists for: rigor in, confidence out.

## What's next

- The L2 loss-accounting walk with the first operator.
- More adapters for third-party log formats (26 served today).
- Engagement with the emerging logging standards (comments filed on prEN 18229-1
  under the EU AI Act; contact established with the national committee for
  ISO/IEC 24970).

If you run a system whose logs claim completeness — an agent runtime, an audit
ledger, a pipeline — the checker is free, the spec is CC0, and a graded log is
one `pip install` away.

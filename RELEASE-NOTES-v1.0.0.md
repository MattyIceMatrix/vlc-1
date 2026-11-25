# v1.0.0 — live checker, signed reports, CI distribution

*Paste this as the release body when drafting the `v1.0.0` release
(RELEASING.md step 1). Everything below is on `main` and CI-green.*

---

**VLC-1 grades an AI system's logs for completeness** — that delivered +
declared-lost == produced under a hash chain — instead of mere
tamper-evidence. This first stable release is the full working system:

## The spec (1.4.5-draft lineage, frozen here as 1.0)
- 26 requirements (15 structural, 11 attested), levels L1–L5, with a
  self-test that fails in both directions: fabricated claims and broken
  guarantees are both caught.
- 7 hash-chain mechanisms, including `sha256-chain-jcs-nested` — RFC 8785
  (JCS) canonicalization with a nested hash member and carried prev link,
  on a guarded subset that is never misgraded outside it.

## The checkers
- `conformance.py` — the reference: any JSONL log + a data-only adapter
  → a level. Adapters are data; the checker never executes them.
- The live checker (Cloudflare Workers) serves the same grades, kept
  provably exact to the reference by a fixed conformance matrix, a
  300-case differential fuzzer on every push, and parity sweeps across
  every served adapter (300 pairs). The fuzzer found 5 real divergences
  during development; none ever shipped a wrong grade.
- 26 adapters served, including third-party log formats.

## Signed reports
- Ed25519-signed verification reports; the private key is generated
  inside a Durable Object and never exported. Reports verify offline
  with the pure-Python verifier (`tools/verify_report.py`).

## CI distribution
- `uses: MattyIceMatrix/vlc-1@v1` — grade your logs on every push
  (root `action.yml`; tick the Marketplace box while drafting this
  release).
- `pip install vlc-check` once PyPI Trusted Publishing is enabled
  (RELEASING.md step 2); the publish workflow sanity-checks an
  install-and-grade before anything ships.

## Independent engagement
- Cross-test findings credited in the IETF AER-1 draft.
- Comment filed on prEN 18229-1 (EU AI Act logging); DIN committee
  contact established for ISO/IEC 24970.

License: CC0 (spec and checker). DOI: 10.5281/zenodo.22728393.

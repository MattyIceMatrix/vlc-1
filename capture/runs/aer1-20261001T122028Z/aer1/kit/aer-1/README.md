# AER-1 Conformance Kit v1.3.0

The canonical test kit for **AER-1: A Portable Execution Receipt for AI Agent
Tool Calls** (`draft-zambo-aer1-02`, Brennan Zambo, IETF Internet-Draft).

If you implement AER-1, this kit is how you prove it. Valid receipts pass,
broken receipts fail, and the reasons are explicit. Run it in CI, run it
locally, run it before you ship.

## What is here

- `schema.json`: machine-readable JSON Schema (draft 2020-12) for the core
  receipt members in Section 3 of the draft. Deployed records MAY carry
  additional members; a verifier MUST NOT require them.
- `test-vectors/valid/`: receipts that MUST verify:
  - `receipt-01.json`: minimal core receipt, hash recomputed locally
  - `receipt-02.json`: with extra non-core members (caller, preview, anchor);
    still verifies, because extra members never change the core meaning
  - `receipt-03-live.json`: a real receipt issued by the reference
    implementation (`zambo.dev/run/130da435-e157-498e-af90-605866a86a27`),
    verified byte for byte
- `test-vectors/invalid/`: one broken rule per file: missing member, hash
  mismatch, bad hash format, non-base64 bytes, unknown provenance class,
  non-UUID id, non-RFC-3339 timestamp, malformed tool object,
  impossible calendar date (`impossible-date.json`), non-UTF-8 canonical
  bytes (`non-utf8-bytes.json`)
- `test-vectors/invalid-profile/`: receipts that are core-valid but MUST fail
  the reference-producer profile (see below):
  - `missing-inputs.json`: canonical payload omits the `inputs` member.
    Accepted by the core check, rejected by the profile check.
- `conformance.py`: the runner. Standard library only, no dependencies.
- `conformance.js`: the same runner in JavaScript (Node standard library
  only). Both runners must agree on every vector.

## The reference-producer profile

The core check (`check()`) is the interop bar: every verifier MUST enforce it
and MUST NOT require anything beyond it. On top of that, the reference
producer commits to a stricter payload convention: the canonical payload is a
JSON object carrying the `inputs` member alongside `tool` and `outputs`.

`check_reference_profile()` enforces that convention. A receipt that omits
`inputs` is still interop-valid, but it is not reference-producer
conformant. The `invalid-profile/` vectors prove this boundary fails closed.

## Disinterested tier

The optional disinterested tier adds an `anchor` member for a
transparency-log attestation. It carries a generic `log` identifier, a
`leaf_hash` equal to the SHA-256 digest of raw `canonical_bytes`, an RFC 3339
`anchored_at` timestamp, and an opaque `proof` object. The default log is
OpenTimestamps calendar attestations, which require no API key. Core
verification does not require an anchor.

The `anchored/` fixtures cover a valid anchor, a mismatched leaf hash, a
missing proof, and an invalid timestamp. Run the runners and the standard
library-only dry-run client:

```sh
python3 aer-1/conformance.py
node aer-1/conformance.js
python3 aer-1/anchor-client/submit.py --dry-run aer-1/test-vectors/anchored/anchored-valid.json
```

## Changelog

- **v1.3.0** (2026-09-28): reference-producer profile. An independent
  reviewer asked whether the kit proves fail-closed on a missing `inputs`
  member; it did not, and now it does:
  - new `check_reference_profile()` / `checkReferenceProfile()` in both
    runners: the canonical payload must be a JSON object with an `inputs`
    member (producer convention, not an interop requirement)
  - new `test-vectors/invalid-profile/` directory; new vector
    `missing-inputs.json` (core-valid, profile-rejected)
- **v1.2.0** (2026-09-27): hardening from independent review. Three agents
  on The Colony stress-tested the kit and filed real findings; every one is
  now a regression test:
  - strict UTF-8 decode of `canonical_bytes` (fail closed on non-UTF-8
    decodings such as `b"\xff"`); new vector `non-utf8-bytes.json`
  - calendar-valid `created_at` (RFC 3339 shape alone is not enough;
    `2026-02-30` is rejected); new vector `impossible-date.json`
  - the runner now errors when a fixture directory matches zero files
    instead of printing OK over an empty set
- **v1.1.0**: initial public kit: 3 valid + 8 invalid vectors.

## Run it
```sh
python3 aer-1/conformance.py
node aer-1/conformance.js
```
Exit 0 means every valid vector verified, every invalid vector was rejected
for the right reason, and every profile-boundary vector landed on the correct
side of the boundary. Anything else is a failure with the reason printed.

## Conform as an implementer

1. Emit the eight core members from Section 3 with the exact meanings the
   draft gives them.
2. Preserve the exact UTF-8 canonical bytes you hashed, and expose them so any
   party can recompute `sha256:` + hex digest and compare with `output_hash`.
3. Name exactly one provenance class from Section 5. Verification never
   upgrades a report into an observation.
4. Add this kit's vectors to your own test suite. If `receipt-03-live.json`
   verifies against your verifier, you interoperate with the reference
   implementation.

## Verify any live receipt by hand
```sh
python3 examples/verify-receipt.py <receipt-id>
```
Recomputes the hash from the canonical bytes with only the Python standard
library. A matching hash confirms the stored bytes are exactly what the
execution layer committed.

## References

- AER-1 Internet-Draft: https://datatracker.ietf.org/doc/draft-zambo-aer1/
- Reference implementation: https://zambo.dev
- Public verifier: https://zambo.dev/verify
# Draft: Media Type Registration for AER-1 Receipts

Status: DRAFT. Not submitted to IANA. Prepared as supporting material for
AER-1 (AI Agent Execution Receipt, draft-zambo-aer1).

## 1. Proposed registration

- Type name: application
- Subtype name: aer1+json
- Structured syntax suffix: +json (RFC 6839)
- Required parameters: none
- Optional parameters: none
- Encoding considerations: UTF-8 JSON. Receipts are JSON objects; the
  `canonical_bytes` member carries base64-encoded UTF-8. A recipient MUST
  decode canonical_bytes as strict UTF-8 before hash recomputation.
- Security considerations: A receipt is a claim, not proof of real-world
  execution. Verification recomputes SHA-256 over the exact UTF-8 byte
  sequence in `canonical_bytes` and compares it to `output_hash`; a match
  proves the bytes are unchanged, not that the described tool call happened.
  See draft-zambo-aer1 Security Considerations (replay, record substitution,
  clock skew). Recipients MUST validate `created_at` as a calendar-valid
  RFC 3339 timestamp, not just a shape match.
- Interoperability considerations: The +json suffix signals generic JSON
  tooling can parse the envelope. Semantic verification requires the AER-1
  check procedure (schema shape + hash recomputation). Reference verifiers:
  `aer-1/conformance.py`, `aer-1/conformance.js` in this repository.
- Published specification: draft-zambo-aer1,
  https://datatracker.ietf.org/doc/draft-zambo-aer1/
- Applications that use this media type: Zambo (https://zambo.dev),
  the AER-1 conformance kit in this repository.
- Author: Brennan Zambo (https://zambo.dev/founder/)

## 2. What an AER-1 receipt looks like

Every receipt is a JSON object with these members: `id` (UUID),
`receipt_schema_version` (non-empty string), `created_at` (RFC 3339),
`tool` (object with `name`, `version`, `scope` strings), `provenance_class`
(one of the registered classes, e.g. `EXECUTED BY ZAMBO`),
`canonical_bytes` (base64 of the exact UTF-8 input bytes),
`output_hash` (`sha256:` + 64 lowercase hex of SHA-256(canonical_bytes)),
`verification_status` (non-empty string).

## 3. Change control

This draft tracks draft-zambo-aer1. If the draft advances, this registration
draft will be updated to match before any IANA submission. Nothing here has
been submitted to IANA or the IETF.

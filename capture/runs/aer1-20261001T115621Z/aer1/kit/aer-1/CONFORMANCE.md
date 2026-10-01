# AER-1 Conformance

Kit version: 1.3.0. Draft revision: draft-zambo-aer1-02. Generated UTC: yesterday.

| Runner | Version | Exit code |
| --- | --- | ---: |
| Python | 3.11.14 | 0 |
| Node.js | v24.13.0 | 0 |

| Fixture | Python | JavaScript | Agreement |
| --- | --- | --- | --- |
| `anchored-bad-leaf-hash.json` | PASS | PASS | yes |
| `anchored-bad-timestamp.json` | PASS | PASS | yes |
| `anchored-missing-proof.json` | PASS | PASS | yes |
| `anchored-valid.json` | PASS | PASS | yes |
| `bad-created-at.json` | PASS | PASS | yes |
| `bad-id.json` | PASS | PASS | yes |
| `bad-provenance.json` | PASS | PASS | yes |
| `bad-verification-status.json` | PASS | PASS | yes |
| `bytes-not-base64.json` | PASS | PASS | yes |
| `hash-bad-format.json` | PASS | PASS | yes |
| `hash-mismatch.json` | PASS | PASS | yes |
| `impossible-date.json` | PASS | PASS | yes |
| `missing-inputs.json` | PASS | PASS | yes |
| `missing-output-hash.json` | PASS | PASS | yes |
| `non-utf8-bytes.json` | PASS | PASS | yes |
| `receipt-01.json` | PASS | PASS | yes |
| `receipt-02.json` | PASS | PASS | yes |
| `receipt-03-live.json` | PASS | PASS | yes |
| `tool-not-object.json` | PASS | PASS | yes |
| `uppercase-id.json` | PASS | PASS | yes |

Both runners recompute the same receipt bytes and apply the same expected outcomes.
The frozen v1 corpus and its hashes are pinned in [aer-1/frozen-vectors/v1/](frozen-vectors/v1/).

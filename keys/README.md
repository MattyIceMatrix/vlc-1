# Keys

Public keys and key statements for this project. Private keys never appear here.

| File | What it is |
|---|---|
| `vlc-report-signing.pub.json` | The key that signs VLC verified reports (see `VERIFIED-REPORTS.md`). |
| `matthew-moore-operator.pub.pem` | Matthew Moore's operator key (Ed25519, SPKI PEM). Signs the statement below. |
| `matthew-moore-operator-statement.json` / `.sig` | Operator key statement naming, in its key history, the blind-08 witness key below and the audit ledger key of the OCTA governance gateway. Verify: the `.sig` is a base64 Ed25519 signature over the hex SHA-256 of the `.json` text, under the operator public key. |
| `matthew-moore-blind08-witness.pub.pem` | Witness key for the blind-08 exercise (Ed25519, SPKI PEM). sha256 of the PEM text: `7cff65ba3e5ef54e` … (full value inside the statement). |

All three keys were generated 2026-11-28 on the operator's own machine; only public
material was ever transmitted.

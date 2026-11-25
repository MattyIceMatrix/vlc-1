# Verified reports

*Added 2026-11-25.*

The live checker at <https://vlc-1.moorematthew131.workers.dev/checker.html>
hands anyone a **self-generated** report — a JSON file of their own verdict,
marked `"Self-generated … not a verified result and not a conformance mark."`
Useful to its owner; worth nothing to their auditor, because anyone can edit
a JSON file.

A **verified report** closes that gap. It is the same server-computed verdict,
issued by the operator through `POST /api/verify`, signed with an Ed25519 key
that is **generated inside the Worker's Durable Object on first use and never
exported**: no dashboard paste, no laptop copy, no transcript, no backup — the
private key has never existed anywhere but Cloudflare's storage. Only the
public half leaves, via `GET /api/pubkey`, and is committed here:

- `keys/vlc-report-signing.pub.json` — key id, raw public key (hex), SPKI (base64)

## Verifying one — offline, stdlib only

```
./tools/verify_report.py report.json
```

Exit 0 and `VALID` iff the Ed25519 signature matches the canonical JSON of the
report's `report` member (sorted keys, compact separators — the same `canon()`
the checker itself hashes records with). The verification code path is the
reference checker's own pure-Python `ed25519_verify` (`conformance.py`,
RFC 8032 §5.1.7, strict decoding), so trusting the verifier means trusting
nothing beyond the spec repo already cloned. Any other Ed25519 implementation
reproduces the result from the public key file alone.

What a valid signature attests: *this exact verdict, over a journal with this
head hash and record count, was computed by the operator's checker at the
stated time.* What it does not attest: anything about the journal's producer,
or any level the live subset does not grade (levels 3–5 need the reference
checker).

## Two issuing paths

`POST /api/verify` signs a verdict the live subset computed itself
(canonical- and prefix-chain journals). For everything else — merkle-tlog,
`sha256-canonical-fields`, `hex-join`, the full adapter set — the operator
runs the reference checker locally and `POST /api/sign-report` signs the
submitted result; the signed wrapper states that division of labour plainly
(`"checker": "conformance.py reference checker, run by the operator; this
service signed the operator-submitted result"`). `tools/issue_verified_report.py`
drives that flow and refuses to save anything it has not re-verified offline
first. Either way, the verification story for the holder is identical:
`tools/verify_report.py`, this repo's public key, no network.

## Issuing one (operator)

`POST /api/verify` with the journal as the body requires the `x-admin-key`
header (`ADMIN_KEY` secret) — verified reports are issued, not self-served.
The response carries `{ report, signature }`, ready to hand to the customer,
who can check it against this repository without contacting the site. The
roundtrip is tested in `worker/signing.test.mjs`: the JS signer and the
Python verifier are proven against each other on every run, including the
tampered-report rejection.

## Key rotation

Rotation = mark the active row inactive in the Durable Object's
`signing_keys` table (a fresh key generates on the next issue), commit the
new public key to `keys/`, and leave old public keys in place so old reports
stay verifiable. A report's `signature.key_id` names the key that signed it;
`tools/verify_report.py` refuses a key-id mismatch rather than guessing.

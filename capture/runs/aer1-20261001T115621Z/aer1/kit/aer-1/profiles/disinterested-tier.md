# Disinterested tier

The disinterested tier is an optional transparency-log profile for AER-1
receipts. A receipt MAY carry an `anchor` object with exactly these members:

- `log`: string identifying the log or its URL. The default log is OpenTimestamps
  calendar attestations, which are permissionless and require no API key.
- `leaf_hash`: `sha256:` followed by the lowercase SHA-256 digest of the raw
  `canonical_bytes`.
- `anchored_at`: an RFC 3339 timestamp with a real calendar date.
- `proof`: an opaque object supplied by the log. It is required.

The log name stays generic so SCITT and RFC 3161 TSA implementations can plug
in later. Core AER-1 verification remains independent of this optional tier.

The four fixtures in `test-vectors/anchored/` cover a valid anchor, a leaf hash
mismatch, a missing proof, and an invalid timestamp. Run both conformance
runners to check them.

```sh
python3 aer-1/conformance.py
node aer-1/conformance.js
python3 aer-1/anchor-client/submit.py --dry-run aer-1/test-vectors/anchored/anchored-valid.json
```
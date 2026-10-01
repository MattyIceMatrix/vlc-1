# AER-1 Python

Pure Python 3.9+ standard-library implementation. `verifier.py` validates core receipts, the reference profile, anchors, and Section 8.1 Merkle roots. `emitter.py` produces receipts with exact UTF-8 commitments.

```sh
python3 conformance.py          # deterministic checked-in 44-vector corpus
python3 conformance.py --live   # fetch the live index and fixtures, with local fallback
python3 emitter.py
```

No pip installation is required.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.

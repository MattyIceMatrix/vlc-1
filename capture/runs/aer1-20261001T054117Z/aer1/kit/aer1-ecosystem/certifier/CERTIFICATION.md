# AER-1 certification rules

A conformant implementation must reproduce the expected PASS/FAIL verdict for all 43 frozen vectors and agree with the reference verifier on every supplied fuzz case. The certifier records each input hash, command, timestamp, individual result, and overall verdict in `conformance-report.json`.

A green badge may be displayed only when the report says `overall: PASS`, vectors are 44/44, and the fuzz corpus has no disagreement. The badge is a snapshot, not a permanent security warranty; rerun it after changing verification code or fixtures.

Disputes should include the report, input hashes, implementation version, command, and the smallest failing receipt. Maintainers reproduce against the frozen corpus before changing a vector or declaring a verifier bug. Badge text must not imply certification of the application logic beyond AER-1 receipt validation.

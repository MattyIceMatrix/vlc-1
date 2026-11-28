# Cross-test kit: draft-sharif-agent-audit-trail-06 (AAT)

Same discipline as the AER-1 cross-test (THIRD-PARTY.md): build sessions
that satisfy every MUST of the draft, then probe what the rules establish.
`python3 harness.py` (needs node for exact RFC 8785) builds the sessions
beside itself and asserts four results; the findings write-up goes to the
draft author first.

#!/usr/bin/env python3
"""Reproduce the AER-1 draft -05 Section 8.1 worked example (workflow 42a3c2cf).

Construction: leaf = SHA-256 over the UTF-8 bytes of the step's receipt_id
string; pair adjacent digests, SHA-256 over the concatenation of the two
32-byte digests; duplicate the last digest at odd levels; lowercase hex.
Expected root: 7c4817ca249edfeae259b98abf63ed38a31d9dbeebf5ee23139410a7a7f63b37
(the canonical root; btw.media's review independently computed this value).
"""
import hashlib

RECEIPT_IDS = [
    "e80168eb-a6a1-4ec9-8478-ac108f9397ff",
    "514fe841-bbdd-4804-9ef4-6828842d8763",
    "a090bdad-f2cf-48c9-bc89-e9e17700fb15",
    "bf88a036-416b-456a-8e82-8c0991811d68",
    "ae795bf0-27f8-4cf2-8aef-3f8142b77217",
]

EXPECTED = "7c4817ca249edfeae259b98abf63ed38a31d9dbeebf5ee23139410a7a7f63b37"

def sha(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

level = [sha(rid.encode("utf-8")) for rid in RECEIPT_IDS]
while len(level) > 1:
    if len(level) % 2:
        level.append(level[-1])
    level = [sha(level[i] + level[i + 1]) for i in range(0, len(level), 2)]

root = level[0].hex()
print(root)
assert root == EXPECTED, f"MISMATCH: {root}"
print("MATCH: the Section 8.1 construction recomputes the canonical root")

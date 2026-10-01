# Merkle worked example, AER-1 draft Section 8.1

This directory contains a standalone, stdlib-only Python script that
recomputes the canonical Section 8.1 Merkle root for the frozen
workflow 42a3c2cf-2cdd-5b8a-aced-016e5a2fb634.

## Run it

    python3 reproduce-merkle-root-8.1.py

No dependencies beyond Python 3.

## What it checks

The script builds the tree exactly as the draft specifies:

- leaf = SHA-256 over the UTF-8 bytes of each step's receipt_id string
- parent = SHA-256 over the concatenation of the two 32-byte child digests
- at odd levels, the last digest is duplicated

and asserts the root equals the canonical value:

    7c4817ca249edfeae259b98abf63ed38a31d9dbeebf5ee23139410a7a7f63b37

## Independent check

btw.media independently recomputed this same root from the live page data,
confirming the construction is byte-exact across independent verifiers.
Each step in the workflow carries a verifiable receipt, and the root above
binds all five.

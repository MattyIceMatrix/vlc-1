#!/usr/bin/env python3
"""Verify a VLC verified report OFFLINE -- no network, stdlib only.

    ./tools/verify_report.py <report.json> [keys/vlc-report-signing.pub.json]

The report file is what /api/verify returns: {"report": ..., "signature": ...}.
The signature is Ed25519 over the canonical JSON of .report (sorted keys,
compact separators) -- the same canonicalization conformance.py uses for
record hashing. Verification reuses the reference checker's own pure-Python
ed25519_verify, so trusting this script means trusting nothing beyond the
spec repo you already cloned.

Exit 0: signature valid. Exit 1: INVALID. Exit 2: usage/parse error.

Blast radius: reads the two files named on the command line; writes nothing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from conformance import canon, ed25519_verify  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    report_path = sys.argv[1]
    key_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "keys", "vlc-report-signing.pub.json")
    try:
        with open(report_path, encoding="utf-8") as f:
            doc = json.load(f)
        with open(key_path, encoding="utf-8") as f:
            key = json.load(f)
        report = doc["report"]
        sig = bytes.fromhex(doc["signature"]["sig_hex"])
        pub = bytes.fromhex(key["public_key_raw_hex"])
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if doc["signature"].get("key_id") != key.get("key_id"):
        print(f"INVALID: report signed with key_id {doc['signature'].get('key_id')}, "
              f"public key file is {key.get('key_id')}", file=sys.stderr)
        return 1
    msg = canon(report).encode()
    if ed25519_verify(pub, msg, sig):
        print(f"VALID  Ed25519 signature by key {key['key_id']} over the canonical report")
        res = report.get("result")
        if isinstance(res, dict):
            # a reference-checker report (conformance.py run by the operator,
            # signed by the service): the verdict is nested under .result
            print(f"       structural L{res.get('structural_level')}  "
                  f"attested L{res.get('attested_level')}  adapter: {res.get('adapter')}  "
                  f"spec: {res.get('spec')}")
            print(f"       head: {res.get('head')}  issued: {report.get('issued_at')}")
        else:
            print(f"       verdict: {report.get('verdict')}  records: {report.get('records')}  "
                  f"issued: {report.get('issued_at')}")
        return 0
    print("INVALID: signature does not match the report content", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

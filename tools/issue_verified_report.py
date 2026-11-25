#!/usr/bin/env python3
"""Issue a signed VERIFIED REPORT for any journal the reference checker grades.

    VLC_ADMIN_KEY=... ./tools/issue_verified_report.py <journal.jsonl> <adapter.json> [out.json]

The live endpoint's /api/verify signs only what the live subset itself grades
(canonical- and prefix-chain). This tool covers everything else -- merkle-tlog,
sha256-canonical-fields, hex-join, the full adapter set: it runs conformance.py
locally, submits the report to the admin-gated /api/sign-report, saves the
signed document, and immediately re-verifies the signature OFFLINE with the
same pure-Python Ed25519 the spec repo ships, so a report is never handed over
unchecked. The signed wrapper states plainly that the operator ran the
reference checker; the service signed the operator-submitted result.

Requires: VLC_ADMIN_KEY in the environment (never on the command line).
Exit 0: signed and offline-verified. Exit 1: any step failed. Exit 2: usage.

Blast radius: reads the two inputs; writes the one output file (default
verified-report-<UTC>.json in the current directory); one HTTPS POST to the
issuing service. No installs, stdlib only.
"""
import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from conformance import check, canon, ed25519_verify  # noqa: E402

SERVICE = os.environ.get("VLC_SERVICE", "https://vlc-1.moorematthew131.workers.dev")


def no_unsignable_numbers(obj, path="$"):
    """Floats, and ints beyond 2^53, canonicalize differently in the signer's
    JavaScript than in Python -- the signature would never verify offline.
    Refuse up front with the exact path instead of confusing the operator."""
    if isinstance(obj, bool):
        return None
    if isinstance(obj, float):
        return f"{path} is a float ({obj!r})"
    if isinstance(obj, int) and abs(obj) >= 2**53:
        return f"{path} is an integer beyond 2^53 ({obj})"
    if isinstance(obj, dict):
        for k, v in obj.items():
            bad = no_unsignable_numbers(v, f"{path}.{k}")
            if bad:
                return bad
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            bad = no_unsignable_numbers(v, f"{path}[{i}]")
            if bad:
                return bad
    return None


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    admin = os.environ.get("VLC_ADMIN_KEY")
    if not admin:
        print("error: set VLC_ADMIN_KEY in the environment", file=sys.stderr)
        return 2
    journal, adapter = sys.argv[1], sys.argv[2]
    from datetime import datetime, timezone
    out_path = sys.argv[3] if len(sys.argv) > 3 else (
        "verified-report-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")

    rep = check(journal, adapter)
    bad = no_unsignable_numbers(rep)
    if bad:
        print(f"error: report not signable as-is: {bad}", file=sys.stderr)
        print("floats and ints beyond 2^53 canonicalize differently in the signer;", file=sys.stderr)
        print("strip or stringify that field before issuing", file=sys.stderr)
        return 1

    req = urllib.request.Request(
        SERVICE + "/api/sign-report",
        data=json.dumps(rep).encode(),
        headers={"content-type": "application/json", "x-admin-key": admin},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            doc = json.load(r)
    except Exception as e:  # noqa: BLE001 -- fail loud with the cause
        print(f"error: issuing service refused or unreachable: {e}", file=sys.stderr)
        return 1

    # never hand over a report we have not verified ourselves, offline
    key_path = os.path.join(REPO, "keys", "vlc-report-signing.pub.json")
    with open(key_path, encoding="utf-8") as f:
        pub = json.load(f)
    if doc["signature"]["key_id"] != pub["key_id"]:
        print(f"error: service signed with key {doc['signature']['key_id']}, "
              f"repo key file is {pub['key_id']} -- refusing to save", file=sys.stderr)
        return 1
    msg = canon(doc["report"]).encode()
    if not ed25519_verify(bytes.fromhex(pub["public_key_raw_hex"]), msg,
                          bytes.fromhex(doc["signature"]["sig_hex"])):
        print("error: signature from the service does not verify offline -- refusing to save",
              file=sys.stderr)
        return 1

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    inner = doc["report"]["result"]
    print(f"VERIFIED REPORT issued and offline-verified (key {pub['key_id']})")
    print(f"  journal:    {journal}")
    print(f"  structural: L{inner.get('structural_level')}  attested: L{inner.get('attested_level')}")
    print(f"  saved:      {out_path}")
    print("  anyone can re-verify: ./tools/verify_report.py " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prepare an optional disinterested-tier anchor for an AER-1 receipt."""
import argparse
import base64
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone


def anchor_for(receipt):
    raw = base64.b64decode(receipt["canonical_bytes"], validate=True)
    raw.decode("utf-8")
    return {
        "log": "OpenTimestamps calendar",
        "leaf_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "anchored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "proof": {"status": "pending"},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("receipt")
    args = parser.parse_args()
    with open(args.receipt, encoding="utf-8") as handle:
        receipt = json.load(handle)
    anchor = anchor_for(receipt)
    if args.dry_run:
        print(json.dumps(anchor, indent=2))
        return 0
    ots = shutil.which("ots")
    if not ots:
        print("ots is not installed. Install OpenTimestamps and run:")
        print("  ots stamp <receipt path>")
        print("Then attach the resulting proof to the anchor member.")
        return 0
    print("OpenTimestamps is available. Stamp the canonical bytes, then attach")
    print("the returned proof to this anchor member:")
    print(json.dumps(anchor, indent=2))
    subprocess.run([ots, "stamp", args.receipt], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
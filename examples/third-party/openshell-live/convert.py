#!/usr/bin/env python3
"""Convert `openshell logs <sandbox>` output into JSON lines for the checker.

One output record per input line, in the order OpenShell printed them; nothing
is added, dropped or reordered. Fields: t (the epoch timestamp as printed),
source (gateway | sandbox), level, target, msg, and class -- the OCSF shorthand
(NET:OPEN, HTTP:GET, CONFIG:LOADED, SSH:OPEN, EVENT, ...) for OCSF lines, or
"trace" for OpenShell's own tracing lines. Deterministic: the same input gives
byte-identical output.

Run: python3 convert.py openshell-logs-raw.txt > ../openshell-live-full.jsonl
"""
import json
import re
import sys

LINE = re.compile(r'^\[(\d+\.\d+)\] \[(\w+)\] \[(\w+) *\] \[([^\]]+)\] (.*)$')


def convert(lines):
    out = []
    for n, raw in enumerate(lines, 1):
        raw = raw.rstrip("\r\n")
        if not raw:
            continue
        m = LINE.match(raw)
        if not m:
            raise SystemExit(f"line {n}: not in OpenShell's log format: {raw[:80]!r}")
        t, source, level, target, msg = m.groups()
        cls = msg.split(" ", 1)[0] if level == "OCSF" else "trace"
        out.append({"t": t, "source": source, "level": level, "target": target,
                    "msg": msg, "class": cls})
    return out


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        for rec in convert(fh):
            sys.stdout.write(json.dumps(rec, separators=(",", ":"), sort_keys=True) + "\n")

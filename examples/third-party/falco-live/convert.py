#!/usr/bin/env python3
"""Convert Falco's JSON alert stream, as captured, into JSON lines for the checker.

  python3 convert.py EVENTS_JSON [--scrub]

EVENTS_JSON is {tuned,default}/events.json: the file Falco's file_output wrote with
json_output enabled, one alert per line (capture/runs/run-*/falco/ on branch
capture/falco-rekor). Output goes to stdout.

Nothing is added, renamed or dropped: each line is parsed and re-serialized with
sorted keys and no whitespace, in the order Falco wrote it. The adapter reads the
record class from Falco's own `rule` field, so no `class` label is added. Blank lines
are skipped.

--scrub removes one rule alert and nothing else: the first alert whose rule is
"Read sensitive file untrusted" (the first `cat /etc/shadow`, phase A). Deterministic:
the same input gives byte-identical output.
"""
import json
import sys
from pathlib import Path

SCRUB_RULE = "Read sensitive file untrusted"


def convert(path, scrub):
    removed = False
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if scrub and not removed and r.get("rule") == SCRUB_RULE:
            removed = True
            continue
        sys.stdout.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")
    if scrub and not removed:
        raise SystemExit(f"no {SCRUB_RULE!r} alert to remove")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    convert(sys.argv[1], "--scrub" in sys.argv[2:])

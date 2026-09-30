#!/usr/bin/env python3
"""Convert the Tessera tile log captured by capture/scripts/tessera.sh into JSON lines
for the checker.

  python3 convert.py LOG_DIR [--scrub]

LOG_DIR is the log as Tessera's POSIX driver wrote it (C2SP tlog-tiles layout:
`checkpoint`, `tile/entries/...`, `tile/<level>/...`; copied here as `log/`).
Output goes to stdout.

A tile log has no record objects: an entry is an opaque byte string in an entry
bundle, and the checkpoint is a signed note. So each record below is built, and
everything in it is taken from what Tessera wrote:
  {"class": "entry", "index": i, "data": "<the entry's bytes, UTF-8>"}
      one per entry, in index order. `index` is the entry's position in the log --
      bundle number x 256 + position in the bundle -- which is how tlog-tiles
      addresses an entry and the number posix-oneshot printed when it assigned it
      (round1.stderr.txt, round2.stderr.txt). The entries here are UTF-8 JSON text.
  {"class": "checkpoint", "origin", "size", "root_hash", "note"}
      last. `note` is the checkpoint file verbatim (C2SP signed note); origin, size and
      root_hash (base64, as in the note) are its first three lines.
`class` is the only label not in the log; it names which of the two it is.

--scrub removes one entry record and nothing else: the one whose data records the
refused delete_file call. The checkpoint is kept as signed, so the delivered set
still names a size and root the remaining entries no longer produce -- which
verify_tlog.py detects and conformance.py, having no Merkle mechanism, cannot.
Deterministic: the same input gives byte-identical output.
"""
import json
import sys
from pathlib import Path


def fmt_n(n):
    groups = []
    while n >= 1000:
        groups.insert(0, f"{n % 1000:03d}")
        n //= 1000
    groups.insert(0, f"{n:03d}")
    return "/".join(["x" + g for g in groups[:-1]] + [groups[-1]])


def convert(d, scrub):
    d = Path(d)
    note = d.joinpath("checkpoint").read_text()
    origin, size, root = note.split("\n")[:3]
    size = int(size)
    recs = []
    for bi in range((size + 255) // 256):
        w = size - bi * 256
        b = d.joinpath("tile/entries/" + fmt_n(bi) + (f".p/{w}" if w < 256 else "")).read_bytes()
        i = 0
        while i < len(b):
            n = int.from_bytes(b[i:i + 2], "big")
            recs.append({"class": "entry", "index": len(recs), "data": b[i + 2:i + 2 + n].decode("utf-8")})
            i += 2 + n
    if scrub:
        hit = [r for r in recs if '"tool":"delete_file"' in r["data"]]
        if len(hit) != 1:
            raise SystemExit("expected exactly one delete_file entry to remove")
        recs.remove(hit[0])
    recs.append({"class": "checkpoint", "origin": origin, "size": size, "root_hash": root, "note": note})
    for r in recs:
        sys.stdout.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    convert(sys.argv[1], "--scrub" in sys.argv[2:])

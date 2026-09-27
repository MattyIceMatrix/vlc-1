#!/usr/bin/env python3
"""L3i fixtures: the interval-attestation level, and the attacks on it.

L3i was added by Corrigendum 1 to repair EXT-002 (Shahab K., 2026-09-13): a log
truncated to a suffix and renumbered closes the L2 identity, because where the
PRODUCER is what failed, nothing is produced and nothing is declared. L3i has a
checker (check_l3i.py) and a proof (proofs/sentinel_interval.v). Until this file
it had no fixture, no adapter and no test, so every scored log took the
"not claimed" branch and the scoring body never executed.

EXT-002 closed with two questions put back to the reporter and never answered:
whether dropping attestor traffic wholesale, or replaying anchors across
intervals, defeats L3i. Cases C and D are those two questions. E and F are the
same family, found by reading the tick validation.

Run: python3 examples/l3i_cases.py <outdir>
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from conformance import canon, sha256_hex                      # noqa: E402

ROOT = "00" * 32
FIRST, LAST = 1, 8


def chain(bodies):
    """sha256-chain-canonical over the record bodies, in order."""
    prev, out = bytes.fromhex(ROOT), []
    for b in bodies:
        r = dict(b)
        r["hash"] = sha256_hex(prev.hex().encode() + canon(b).encode())
        out.append(r)
        prev = bytes.fromhex(r["hash"])
    return out


def adapter(out):
    ad = json.load(open(os.path.join(HERE, "..", "adapters", "generic-appjsonl.json")))
    ad["name"] = "l3i-case"
    ad["non_event_classes"] = ad["non_event_classes"] + ["IVAL", "TICK"]
    ad["interval"] = {
        "mode": "declared",
        "declaration_class": "IVAL",
        "tick_class": "TICK",
        "first_field": "first_tick",
        "last_field": "last_tick",
        "interval_id_field": "ival",
        "tick_index_field": "n",
        "attestor_field": "attestor",
        "witness_field": "sig",
        "bound_field": "binds",
        "trusted_attestors": ["roughtime.example"],
    }
    p = os.path.join(out, "l3i.adapter.json")
    json.dump(ad, open(p, "w"))
    return p


def build(tick_binds=None, keep_ticks=None):
    """One epoch, one interval declaration, 8 producer events, 8 ticks.

    tick_binds(n, prod_hashes, tick_hashes) -> the position tick n binds.
    keep_ticks: the tick indices to emit. None means all of them.
    """
    bodies = [
        {"class": "EPOCH_START", "producer": "acme-llm-proxy/2.4",
         "buffer": "bounded-queue-8192", "on_full": "drop_counted"},
        {"class": "IVAL", "ival": "iv-7", "first_tick": FIRST, "last_tick": LAST,
         "attestor": "roughtime.example"},
    ]
    for i in range(8):
        bodies.append({"class": "inference", "seq": i, "model": "acme-7b",
                       "route": "/v1/chat", "ts": 1757000000 + 3 * i,
                       "verdict": "allow"})
    recs = chain(bodies)
    prod_hashes = [r["hash"] for r in recs if r["class"] == "inference"]

    # Ticks are appended after the producer records, each binding a position.
    # They extend the same chain, so a tick's own hash covers what it binds.
    keep = range(FIRST, LAST + 1) if keep_ticks is None else keep_ticks
    tick_hashes = []
    prev = bytes.fromhex(recs[-1]["hash"])
    for n in keep:
        binds = (tick_binds(n, prod_hashes, tick_hashes) if tick_binds
                 else prod_hashes[n - 1])
        b = {"class": "TICK", "ival": "iv-7", "n": n,
             "attestor": "roughtime.example", "sig": f"sig-{n:03d}"}
        if binds is not None:
            b["binds"] = binds
        r = dict(b)
        r["hash"] = sha256_hex(prev.hex().encode() + canon(b).encode())
        recs.append(r)
        tick_hashes.append(r["hash"])
        prev = bytes.fromhex(r["hash"])
    return recs


def write(out, name, recs):
    p = os.path.join(out, name + ".jsonl")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in recs:
            fh.write(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n")
    return p


def main(out):
    os.makedirs(out, exist_ok=True)
    adapter(out)

    # A. honest: every tick present, each binding a distinct producer record.
    write(out, "l3i-honest", build())

    # B. the producer died mid-interval: ticks 5..8 never emitted. This is
    #    EXT-002 itself, and the case L3i exists to catch.
    write(out, "l3i-producer-died", build(keep_ticks=[1, 2, 3, 4]))

    # C. REPORTER'S QUESTION 1 -- attestor traffic dropped wholesale.
    write(out, "l3i-attestor-dropped", build(keep_ticks=[]))

    # D. REPORTER'S QUESTION 2 -- one anchor replayed across every tick.
    #    Eight signatures, one observed position: the attestor witnessed a
    #    point and the window is scored as covered.
    write(out, "l3i-anchor-replayed",
          build(tick_binds=lambda n, prod, ticks: prod[0]))

    # E. the witness set anchored to itself: each tick binds the tick before
    #    it, so no tick binds a producer record at all.
    write(out, "l3i-self-anchored",
          build(tick_binds=lambda n, prod, ticks: ticks[-1] if ticks else prod[0]))

    # F. ticks bound in reverse: every position is real and distinct, and the
    #    order of observation contradicts the order of the ticks.
    write(out, "l3i-reversed-binding",
          build(tick_binds=lambda n, prod, ticks: prod[LAST - n]))

    print(f"l3i fixtures written to {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/l3i")

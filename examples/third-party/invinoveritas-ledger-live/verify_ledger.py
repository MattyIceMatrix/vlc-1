#!/usr/bin/env python3
"""verify_ledger.py -- independent verifier for the invinoveritas verdict-ledger hash chain.

Standard library only. Written for VLC-1 from the published chain_spec, not from
invinoveritas code (their recompute_ledger.py is used only as a cross-check in the
capture run).

The binding (chain_spec served at GET https://api.babyblueviper.com/ledger):
    content_hash = sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')))
    head_hash    = sha256(content_hash + "|" + prev_head_hash)      (hex strings)
    genesis      = sha256("invinoveritas-ledger-genesis:before-entry-40")
The head is broadcast as a signed Nostr event (NIP-01, BIP-340 Schnorr), which is the
value held outside the ledger that plays the role of --expect-head.

Usage:
    verify_ledger.py jsonl FILE [--pubkey HEX] [--mutations] [--json]

FILE rows: class "ledger-entry" rows {entry, content_hash, prev_head_hash, head_hash},
then optionally one class "chain-head" row that is a raw Nostr event
{id, pubkey, created_at, kind, tags, content, sig}. This file checks the link
arithmetic and the head; recomputing content_hash from each full record needs the
records, which the capture does against the live API (capture/scripts/ledger_capture.py).

BLAST RADIUS: reads FILE; writes nothing; no network.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys

GENESIS_MARKER = "invinoveritas-ledger-genesis:before-entry-40"
GENESIS = hashlib.sha256(GENESIS_MARKER.encode()).hexdigest()
# The key invinoveritas publishes for its signed events (invinoveritas_verify.py,
# PUBLISHED_PUBKEY, and /ledger verifier_pubkey). Pinned; override with --pubkey.
PUBKEY = "6786e18a864893a900bd9858e650f67ccc3513f248fed374b591e2ff6922fbb7"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------- BIP-340
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], P - 2, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], P - 2, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return (x, (lam * (a[0] - x) - a[1]) % P)


def _mul(pt, k):
    r = None
    while k:
        if k & 1:
            r = _add(r, pt)
        pt = _add(pt, pt)
        k >>= 1
    return r


def _tagged(tag, msg):
    t = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(t + t + msg).digest()


def _lift_x(x):
    if x >= P:
        return None
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)
    if y * y % P != y2:
        return None
    return (x, y if y % 2 == 0 else P - y)


def schnorr_verify(msg: bytes, pubkey: bytes, sig: bytes) -> bool:
    if len(pubkey) != 32 or len(sig) != 64:
        return False
    pt = _lift_x(int.from_bytes(pubkey, "big"))
    r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    if pt is None or r >= P or s >= N:
        return False
    e = int.from_bytes(_tagged("BIP0340/challenge", sig[:32] + pubkey + msg), "big") % N
    R = _add(_mul(G, s), _mul(pt, N - e))
    return R is not None and R[1] % 2 == 0 and R[0] == r


def _selftest_bip340():
    # BIP-340 test vectors 1 (valid) and 5 (invalid: pubkey not on the curve)
    ok = schnorr_verify(
        bytes.fromhex("243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89"),
        bytes.fromhex("DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"),
        bytes.fromhex("6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE3341"
                      "8906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"))
    bad = schnorr_verify(
        bytes.fromhex("243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89"),
        bytes.fromhex("EEFDEA4CDB677750A420FEE807EACF21EB9898AE79B9768766E4FAA04A2D4A34"),
        bytes.fromhex("6CFF5C3BA86C69EA4B7376F31A9BCB4F74C1976089B2D9963DA2E5543E177769"
                      "69E89B4C5564D00349106B8497785DD7D1D713A8AE82B32FA79D5F7FC407D39B"))
    if not ok or bad:
        raise SystemExit("BIP-340 self-test failed; refusing to verify anything")


def nostr_event_id(ev) -> str:
    ser = json.dumps([0, ev["pubkey"], ev["created_at"], ev["kind"], ev["tags"], ev["content"]],
                     separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(ser.encode()).hexdigest()


# --------------------------------------------------------------------------- chain
def canon_record(record) -> bytes:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def content_hash(record) -> str:
    return hashlib.sha256(canon_record(record)).hexdigest()


def link(content_h: str, prev_head: str) -> str:
    return hashlib.sha256(f"{content_h}|{prev_head}".encode()).hexdigest()


def head_claim(ev):
    """(entry, head_hash) the head event states, from its JSON content. Returns
    (None, None) when the content does not state both."""
    try:
        c = json.loads(ev.get("content") or "")
    except ValueError:
        return None, None
    if not isinstance(c, dict):
        return None, None
    cands = [c] + [v for v in c.values() if isinstance(v, dict)]
    head = entry = None
    for d in cands:
        for k in ("head_hash", "head", "chain_head"):
            v = d.get(k)
            if isinstance(v, str) and HEX64.match(v.lower()):
                head = head or v.lower()
        for k in ("entry", "head_entry", "entry_n", "n", "latest_entry"):
            v = d.get(k)
            if isinstance(v, int) and not isinstance(v, bool):
                entry = entry if entry is not None else v
    return entry, head


def verify(rows, pubkey=PUBKEY, require_head=True):
    """Return (ok, findings, facts). Every failed condition is one finding.
    require_head=False checks the chain alone (used to show what the head adds)."""
    f, facts = [], {}
    entries = [r for r in rows if r.get("class") == "ledger-entry"]
    heads = [r for r in rows if r.get("class") == "chain-head"]
    other = [r for r in rows if r.get("class") not in ("ledger-entry", "chain-head")]
    if other:
        f.append(f"{len(other)} row(s) of unknown class")
    if not entries:
        return False, f + ["no ledger-entry rows"], facts
    if heads and rows[-1].get("class") != "chain-head":
        f.append("the chain-head row is not the last row")
    prev, prev_n, recomputed = GENESIS, None, {}
    for i, r in enumerate(entries):
        n, ch, ph, hh = r.get("entry"), r.get("content_hash"), r.get("prev_head_hash"), r.get("head_hash")
        if not all(isinstance(x, str) and HEX64.match(x) for x in (ch, ph, hh)):
            f.append(f"entry {n}: chain block missing or not 64 lower-case hex")
            continue
        if prev_n is not None and n != prev_n + 1:
            f.append(f"entry {n}: follows entry {prev_n} (gap or reorder)")
        if ph != prev:
            f.append(f"entry {n}: prev_head_hash is not the recomputed head of its predecessor")
        h = link(ch, prev)
        if h != hh:
            f.append(f"entry {n}: head_hash does not recompute")
        recomputed[n] = h
        prev, prev_n = h, n
    facts.update(first=entries[0].get("entry"), last=prev_n, count=len(entries), final_head=prev)
    if entries[0].get("entry") != 40:
        f.append(f"chain starts at entry {entries[0].get('entry')}, spec says 40")
    if not heads:
        if not require_head:
            return not f, f, facts
        f.append("no chain-head row: the final head is unanchored, so truncation of the newest "
                 "entries, or a rewrite of the whole chain, is undetectable")
        return not f, f, facts
    ev = heads[-1]
    try:
        id_ok = nostr_event_id(ev) == ev.get("id")
        sig_ok = schnorr_verify(bytes.fromhex(ev["id"]), bytes.fromhex(ev["pubkey"]), bytes.fromhex(ev["sig"]))
    except (KeyError, ValueError, TypeError):
        id_ok = sig_ok = False
    pk_ok = str(ev.get("pubkey", "")).lower() == pubkey
    hn, hh = head_claim(ev)
    facts.update(head_event=ev.get("id"), head_event_created_at=ev.get("created_at"),
                 head_event_entry=hn, head_event_head=hh,
                 head_event_id_ok=id_ok, head_event_sig_ok=sig_ok, head_event_pubkey_ok=pk_ok)
    if not id_ok:
        f.append("head event: NIP-01 id does not recompute")
    if not sig_ok:
        f.append("head event: BIP-340 signature does not verify")
    if not pk_ok:
        f.append("head event: not signed by the pinned invinoveritas key")
    if hh is None:
        f.append("head event: content does not state a head hash")
    elif hn is not None and hn != prev_n:
        if hn in recomputed and recomputed[hn] == hh:
            f.append(f"head event anchors entry {hn}, but the log ends at {prev_n}: "
                     f"entries after {hn} are unanchored")
        else:
            f.append(f"head event states entry {hn}, which the log does not reach "
                     f"(truncated) or whose recomputed head differs")
    elif hh != prev:
        f.append("head event: stated head differs from the recomputed final head")
    return not f, f, facts


MUTATIONS = {
    "remove-middle-entry": lambda e: e[:len(e) // 2] + e[len(e) // 2 + 1:],
    "edit-one-content-hash": lambda e: [dict(r, content_hash=("0" if r["content_hash"][0] != "0" else "1") + r["content_hash"][1:])
                                        if i == 5 else r for i, r in enumerate(e)],
    "swap-two-entries": lambda e: e[:3] + [e[4], e[3]] + e[5:],
    "truncate-newest-entry": lambda e: e[:-1],
    "rewrite-whole-chain-consistently": None,  # built below
}


def _rewrite(entries):
    out, prev = [], GENESIS
    for i, r in enumerate(entries):
        ch = r["content_hash"] if i != 7 else hashlib.sha256(b"forged record").hexdigest()
        h = link(ch, prev)
        out.append(dict(r, content_hash=ch, prev_head_hash=prev, head_hash=h))
        prev = h
    return out


def run_mutations(rows, pubkey):
    entries = [r for r in rows if r.get("class") == "ledger-entry"]
    heads = [r for r in rows if r.get("class") == "chain-head"]
    res = {}
    for name, fn in MUTATIONS.items():
        mut = _rewrite(copy.deepcopy(entries)) if fn is None else fn(copy.deepcopy(entries))
        for with_head in (True, False):
            ok, fl, _ = verify(mut + (heads if with_head else []), pubkey, require_head=with_head)
            res[f"{name}{' (with the Nostr head)' if with_head else ' (chain alone)'}"] = {"detected": not ok, "first_finding": fl[0] if fl else None}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["jsonl"])
    ap.add_argument("file")
    ap.add_argument("--pubkey", default=PUBKEY)
    ap.add_argument("--mutations", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    _selftest_bip340()
    with open(a.file, encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    ok, findings, facts = verify(rows, a.pubkey.lower())
    out = {"file": a.file, "ok": ok, "findings": findings, "facts": facts}
    if a.mutations:
        out["mutations"] = run_mutations(rows, a.pubkey.lower())
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(("OK " if ok else "FAIL ") + a.file)
        for k, v in facts.items():
            print(f"  {k}: {v}")
        for x in findings:
            print(f"  - {x}")
        for k, v in out.get("mutations", {}).items():
            print(f"  mutation {k}: {'detected' if v['detected'] else 'NOT detected'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

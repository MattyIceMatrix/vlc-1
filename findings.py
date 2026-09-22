#!/usr/bin/env python3
# ===========================================================================
# VLC-1 Annex K -- committed findings ledger: reference producer and checker.
#
# BLAST RADIUS: writes only the ledger file named by --ledger and the private
# openings directory named by --openings. `verify` writes nothing. No network,
# no processes, no installs. Standard library only.
# ===========================================================================
"""
A tester commits to a finding when it is found, without revealing it; the
commitment is chained and anchored, so the date of discovery cannot move and
a finding committed but never disclosed stays visible as open or overdue.

    findings.py commit   --ledger L --openings DIR --id F1 --doc finding.md \\
                         --class high --due 2026-12-01 --party tester
    findings.py reveal   --ledger L --openings DIR --id F1 --party tester
    findings.py defer    --ledger L --id F1 --due 2027-01-15 --reason fix-in-progress --party subject
    findings.py withdraw --ledger L --openings DIR --id F1 --reason duplicate --party tester
    findings.py head     --ledger L
    findings.py verify   --ledger L [--docs DIR] [--anchor tester=HEX ...] [--as-of 2026-12-02] [--json]

The openings directory holds each finding's nonce. It is the tester's secret
until reveal: never commit it to a repository or publish it.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import sys

VERSION = "vlc1-findings-1"
GENESIS = "0" * 64
KINDS = ("commit", "reveal", "defer", "withdraw")
CLASSES = ("info", "low", "medium", "high", "critical")
ASCII_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# --------------------------------------------------------------------------
# canonical form: sorted keys, no whitespace. Every string in a ledger record
# is restricted to ASCII and every number to an integer (K.3), so this is
# byte-identical to RFC 8785 over the domain the ledger permits.
# --------------------------------------------------------------------------
def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def record_hash(rec):
    body = {k: v for k, v in rec.items() if k != "hash"}
    return sha256_hex(canon(body))


def commitment_of(finding_id, cls, due, nonce, doc_sha256):
    return sha256_hex(canon({"v": VERSION, "finding_id": finding_id, "class": cls,
                             "due": due, "nonce": nonce, "doc_sha256": doc_sha256}))


def now_stamp():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg):
    print(f"findings.py: {msg}", file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate member {k!r}")
        seen[k] = v
    return seen


def _no_float(tok):
    raise ValueError(f"non-integer number {tok!r}")


def load(path):
    recs = []
    if not os.path.exists(path):
        return recs
    with open(path, "rb") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line.decode("utf-8"), object_pairs_hook=_no_dupes,
                                 parse_float=_no_float, parse_constant=_no_float)
            except (ValueError, UnicodeDecodeError) as e:
                raise ValueError(f"line {n}: {e}")
            if not isinstance(obj, dict):
                raise ValueError(f"line {n}: not an object")
            recs.append(obj)
    return recs


# --------------------------------------------------------------------------
# producer
# --------------------------------------------------------------------------
def append(ledger, body):
    recs = load(ledger)
    prev = recs[-1]["hash"] if recs else GENESIS
    at = now_stamp()
    if recs and at < recs[-1].get("at", ""):
        die("system clock is behind the last record; refusing to append out of order")
    rec = dict(body, v=VERSION, seq=len(recs), prev=prev, at=at)
    rec["hash"] = record_hash(rec)
    problems = shape_problems(rec)
    if problems:
        die("; ".join(problems))
    with open(ledger, "ab") as f:
        f.write((canon(rec) + "\n").encode())
    print(rec["hash"])


def opening_path(openings, finding_id):
    return os.path.join(openings, f"{finding_id}.json")


def cmd_commit(a):
    if not ASCII_TOKEN.match(a.id):
        die("finding id must be 1-128 of [A-Za-z0-9._:-]")
    if any(r.get("finding_id") == a.id for r in load(a.ledger)):
        die(f"finding {a.id} already has records in this ledger")
    with open(a.doc, "rb") as f:
        doc_sha256 = sha256_hex(f.read())
    nonce = secrets.token_hex(32)
    os.makedirs(a.openings, exist_ok=True)
    op = opening_path(a.openings, a.id)
    if os.path.exists(op):
        die(f"opening already exists: {op}")
    commitment = commitment_of(a.id, a.cls, a.due, nonce, doc_sha256)
    with open(op, "w") as f:
        json.dump({"finding_id": a.id, "class": a.cls, "due": a.due,
                   "nonce": nonce, "doc_sha256": doc_sha256}, f, indent=2)
    append(a.ledger, {"kind": "commit", "party": a.party, "finding_id": a.id,
                      "class": a.cls, "due": a.due, "commitment": commitment})


def _opening(a):
    op = opening_path(a.openings, a.id)
    if not os.path.exists(op):
        die(f"no opening for {a.id} in {a.openings}")
    with open(op) as f:
        return json.load(f)


def cmd_reveal(a):
    o = _opening(a)
    append(a.ledger, {"kind": "reveal", "party": a.party, "finding_id": a.id,
                      "nonce": o["nonce"], "doc_sha256": o["doc_sha256"]})


def cmd_withdraw(a):
    o = _opening(a)
    append(a.ledger, {"kind": "withdraw", "party": a.party, "finding_id": a.id,
                      "reason": a.reason, "nonce": o["nonce"], "doc_sha256": o["doc_sha256"]})


def cmd_defer(a):
    append(a.ledger, {"kind": "defer", "party": a.party, "finding_id": a.id,
                      "due": a.due, "reason": a.reason})


def cmd_head(a):
    recs = load(a.ledger)
    if not recs:
        die("empty ledger")
    print(recs[-1]["hash"])


# --------------------------------------------------------------------------
# checker
# --------------------------------------------------------------------------
FIELDS = {
    "commit":   {"class", "due", "commitment"},
    "reveal":   {"nonce", "doc_sha256"},
    "defer":    {"due", "reason"},
    "withdraw": {"reason", "nonce", "doc_sha256"},
}
COMMON = {"v", "seq", "prev", "at", "hash", "kind", "party", "finding_id"}


def shape_problems(r):
    p = []
    kind = r.get("kind")
    if kind not in KINDS:
        return [f"unknown kind {kind!r}"]
    want = COMMON | FIELDS[kind]
    if set(r) != want:
        extra, missing = sorted(set(r) - want), sorted(want - set(r))
        p.append(f"fields: missing {missing} extra {extra}")
    for k, v in r.items():
        if isinstance(v, str):
            if not v.isascii():
                p.append(f"{k}: non-ASCII string")
        elif k == "seq":
            if type(v) is not int:
                p.append("seq: not an integer")
        else:
            p.append(f"{k}: must be a string")
    if r.get("v") != VERSION:
        p.append(f"v: expected {VERSION}")
    for k in ("finding_id", "party", "reason"):
        if k in r and isinstance(r[k], str) and not ASCII_TOKEN.match(r[k]):
            p.append(f"{k}: must be 1-128 of [A-Za-z0-9._:-]")
    for k in ("prev", "hash", "commitment", "doc_sha256", "nonce"):
        if k in r and not (isinstance(r[k], str) and HEX64.match(r[k])):
            p.append(f"{k}: must be 64 lowercase hex")
    if "due" in r and not (isinstance(r["due"], str) and DATE.match(r["due"])):
        p.append("due: must be YYYY-MM-DD")
    if not (isinstance(r.get("at"), str) and STAMP.match(r["at"])):
        p.append("at: must be YYYY-MM-DDTHH:MM:SSZ")
    if kind == "commit" and r.get("class") not in CLASSES:
        p.append(f"class: must be one of {CLASSES}")
    return p


def verify(recs, docs=None, anchors=None, as_of=None):
    req = {}

    def ok(rid, note=""):
        req.setdefault(rid, {"status": "PASS", "notes": []})
        if note:
            req[rid]["notes"].append(note)

    def fail(rid, note):
        req[rid] = req.get(rid, {"status": "PASS", "notes": []})
        req[rid]["status"] = "FAIL"
        req[rid]["notes"].append(note)

    for rid in ("VLC-K-1", "VLC-K-2", "VLC-K-3", "VLC-K-4", "VLC-K-5", "VLC-K-6"):
        ok(rid)

    # J-1 shape and chain
    prev = GENESIS
    hashes = []
    for i, r in enumerate(recs):
        for msg in shape_problems(r):
            fail("VLC-K-1", f"record {i}: {msg}")
        if r.get("seq") != i:
            fail("VLC-K-1", f"record {i}: seq {r.get('seq')!r} != {i}")
        if r.get("prev") != prev:
            fail("VLC-K-1", f"record {i}: prev does not link to the record before it")
        h = record_hash(r)
        if r.get("hash") != h:
            fail("VLC-K-1", f"record {i}: hash does not recompute")
        hashes.append(h)
        prev = h
    if not recs:
        fail("VLC-K-1", "empty ledger")

    # J-2 time order
    last = ""
    for i, r in enumerate(recs):
        at = r.get("at", "")
        if isinstance(at, str) and at < last:
            fail("VLC-K-2", f"record {i}: at {at} earlier than the record before it")
        last = at if isinstance(at, str) else last

    # J-3 lifecycle, J-4 openings
    state = {}
    for i, r in enumerate(recs):
        fid, kind = r.get("finding_id"), r.get("kind")
        s = state.get(fid)
        if kind == "commit":
            if s is not None:
                fail("VLC-K-3", f"record {i}: {fid} committed twice")
                continue
            state[fid] = {"class": r.get("class"), "due": r.get("due"), "due_at_commit": r.get("due"),
                          "committed_at": r.get("at"),
                          "commit_seq": i, "commitment": r.get("commitment"), "party": r.get("party"),
                          "status": "open", "deferrals": 0, "doc_sha256": None, "closed_at": None}
            continue
        if s is None:
            fail("VLC-K-3", f"record {i}: {kind} for {fid} with no earlier commit")
            continue
        if s["status"] != "open":
            fail("VLC-K-3", f"record {i}: {kind} for {fid} after it was already {s['status']}")
            continue
        if kind == "defer":
            if isinstance(r.get("due"), str) and isinstance(s["due"], str) and r["due"] <= s["due"]:
                fail("VLC-K-3", f"record {i}: defer for {fid} does not move the due date later")
            s["due"] = r.get("due")
            s["deferrals"] += 1
            continue
        # reveal / withdraw: the opening must match the commitment
        expect = commitment_of(fid, s["class"], s["due_at_commit"], r.get("nonce"), r.get("doc_sha256"))
        if expect != s["commitment"]:
            fail("VLC-K-4", f"record {i}: {kind} for {fid} does not open its commitment")
        s["status"] = "revealed" if kind == "reveal" else "withdrawn"
        s["doc_sha256"] = r.get("doc_sha256")
        s["closed_at"] = r.get("at")
        if kind == "withdraw":
            s["withdraw_reason"] = r.get("reason")

    # J-5 disclosed documents, when supplied
    if docs:
        for fid, s in state.items():
            if s["status"] != "revealed":
                continue
            path = os.path.join(docs, fid)
            cands = [p for p in (path, path + ".md", path + ".txt", path + ".json") if os.path.exists(p)]
            if not cands:
                ok("VLC-K-5", f"{fid}: revealed, document not supplied")
                continue
            with open(cands[0], "rb") as f:
                if sha256_hex(f.read()) != s["doc_sha256"]:
                    fail("VLC-K-5", f"{fid}: document {os.path.basename(cands[0])} does not match the revealed digest")

    # J-6 anchors: each independently held value must be the hash of some record
    anchored = {}
    for party, value in (anchors or {}).items():
        if value in hashes:
            anchored[party] = hashes.index(value)
        else:
            fail("VLC-K-6", f"anchor from {party} matches no record: the ledger was rewritten, "
                            f"or the anchor is from another ledger")
    if not anchors:
        req["VLC-K-6"] = {"status": "NOT_TESTED", "notes": ["no anchor supplied; rewrite resistance "
                                                            "is not established on the ledger alone"]}

    # status report (not pass/fail)
    as_of = as_of or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    for s in state.values():
        if s["status"] == "open" and isinstance(s["due"], str) and s["due"] < as_of:
            s["status"] = "overdue"
    joint = min(anchored.values()) if anchored and len(anchored) == len(anchors or {}) else None
    for fid, s in state.items():
        s["anchored_by"] = sorted(p for p, k in anchored.items() if k >= s["commit_seq"])

    return {
        "ledger_records": len(recs),
        "head": hashes[-1] if hashes else None,
        "as_of": as_of,
        "requirements": req,
        "conformant": all(v["status"] != "FAIL" for v in req.values()),
        "anchors": {p: {"record": k} for p, k in anchored.items()},
        "jointly_anchored_through": joint,
        "unanchored_tail": (len(recs) - 1 - joint) if joint is not None else len(recs),
        "findings": {fid: {k: v for k, v in s.items() if k not in ("commitment", "due_at_commit")}
                     for fid, s in state.items()},
        "summary": {st: sum(1 for s in state.values() if s["status"] == st)
                    for st in ("open", "overdue", "revealed", "withdrawn")},
    }


def cmd_verify(a):
    try:
        recs = load(a.ledger)
    except ValueError as e:
        res = {"conformant": False, "requirements": {"VLC-K-1": {"status": "FAIL", "notes": [str(e)]}}}
        print(json.dumps(res, indent=2) if a.json else f"FAIL VLC-K-1 {e}")
        return 1
    anchors = {}
    for spec in a.anchor or []:
        party, _, value = spec.partition("=")
        if not ASCII_TOKEN.match(party) or not HEX64.match(value):
            die(f"--anchor must be PARTY=<64 lowercase hex>, got {spec!r}")
        anchors[party] = value
    if a.as_of and not DATE.match(a.as_of):
        die("--as-of must be YYYY-MM-DD")
    res = verify(recs, a.docs, anchors, a.as_of)
    if a.json:
        print(json.dumps(res, indent=2, sort_keys=True))
    else:
        for rid, v in sorted(res["requirements"].items()):
            print(f"{v['status']:<11}{rid}  " + "; ".join(v["notes"]))
        print(f"records {res['ledger_records']}  head {res['head']}")
        if res["anchors"]:
            print("anchored: " + ", ".join(f"{p} through record {v['record']}" for p, v in res["anchors"].items())
                  + f"; unanchored tail {res['unanchored_tail']}")
        print("findings as of {}: {}".format(res["as_of"], ", ".join(f"{k} {v}" for k, v in res["summary"].items())))
        for fid, s in res["findings"].items():
            extra = f", deferred {s['deferrals']}x" if s["deferrals"] else ""
            print(f"  {fid:<24}{s['class']:<9}{s['status']:<10}due {s['due']}{extra}")
        print("CONFORMANT" if res["conformant"] else "NOT CONFORMANT")
    return 0 if res["conformant"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def p(name, *need):
        s = sub.add_parser(name)
        s.add_argument("--ledger", required=True)
        if "openings" in need:
            s.add_argument("--openings", required=True)
        if "id" in need:
            s.add_argument("--id", required=True)
        if "party" in need:
            s.add_argument("--party", required=True)
        return s

    s = p("commit", "openings", "id", "party")
    s.add_argument("--doc", required=True)
    s.add_argument("--class", dest="cls", required=True, choices=CLASSES)
    s.add_argument("--due", required=True)
    s.set_defaults(fn=cmd_commit)
    s = p("reveal", "openings", "id", "party"); s.set_defaults(fn=cmd_reveal)
    s = p("withdraw", "openings", "id", "party"); s.add_argument("--reason", required=True); s.set_defaults(fn=cmd_withdraw)
    s = p("defer", "id", "party"); s.add_argument("--due", required=True); s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_defer)
    s = p("head"); s.set_defaults(fn=cmd_head)
    s = p("verify")
    s.add_argument("--docs")
    s.add_argument("--anchor", action="append", help="PARTY=HEX, a record hash that party published independently")
    s.add_argument("--as-of", help="YYYY-MM-DD for overdue status (default: today, UTC)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_verify)
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())

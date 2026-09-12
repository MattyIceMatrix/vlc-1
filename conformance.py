#!/usr/bin/env python3
"""
VLC-1 conformance checker -- vendor-neutral.

    ./conformance.py --log <file> --adapter <adapter.json> [--json] [--mutate M]

Reads ANY log, in any field naming, given a small declarative adapter that maps
the producer's field names onto the abstract quantities of VLC-1 clauses 4-7.
Reports the level ACTUALLY DEMONSTRATED and the exact requirement IDs that
failed.  It never reports the level a producer claims.

Design constraints, from SPEC.md Annex C:
  * adapters are DATA, not code -- no adapter may execute anything;
  * no requirement check is hard-coded to one vendor's mechanism;
  * every level must be reachable by an application-layer producer.

Exit codes:  0 = the log demonstrated the level requested with --expect (or, with
no --expect, the check ran).  1 = expectation not met.  2 = usage/adapter error.
"""
import argparse, hashlib, json, os, re, sys

VERSION = "VLC-1 1.0-draft"

PASS, FAIL, NA = "PASS", "FAIL", "n/a"


class LogError(Exception):
    """The delivered set is not readable as a log. Not an adapter fault, and
    not a crash: it is exactly what a verifier should report as L0."""


# ===========================================================================
# canonicalisation helpers
# ===========================================================================
def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_hex(b):
    if isinstance(b, str):
        b = b.encode()
    return hashlib.sha256(b).hexdigest()


def dig(rec, path):
    """Field lookup, dotted path, tolerant of absence."""
    if path is None:
        return None
    cur = rec
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x) != ""]
    return [x for x in re.split(r"[,\s]+", str(v)) if x]


# ===========================================================================
# the log model -- what every adapter must produce
# ===========================================================================
class Rec:
    __slots__ = ("i", "raw", "obj", "cls", "hash")

    def __init__(self, i, raw, obj, cls, h):
        self.i, self.raw, self.obj, self.cls, self.hash = i, raw, obj, cls, h


def load(path, ad):
    if not os.path.exists(path):
        raise LogError(f"log not found: {path}")
    lines = [l.rstrip("\n") for l in open(path, encoding="utf-8", errors="replace")
             if l.strip()]
    hf = ad["integrity"].get("hash_field")
    cf = ad.get("record_class_field")
    out = []
    for i, l in enumerate(lines):
        try:
            o = json.loads(l)
        except Exception:
            raise LogError(f"record {i} is not parseable as JSON")
        out.append(Rec(i, l, o, str(dig(o, cf)) if cf else "?", dig(o, hf)))
    return out


# ===========================================================================
# LEVEL 1 -- tamper-evidence
# ===========================================================================
def chain_root(recs, ad):
    r = ad["integrity"].get("root", {})
    k = r.get("kind", "zero")
    if k == "zero":
        return bytes(32)
    if k == "constant":
        return bytes.fromhex(r["value"])
    if k == "field_of_first_record":
        v = dig(recs[0].obj, r["field"])
        if v is None:
            return None
        if r.get("transform") == "sha256":
            return hashlib.sha256(str(v).encode()).digest()
        try:
            return bytes.fromhex(str(v))
        except ValueError:
            raise LogError("chain root field is not hex")
    raise SystemExit(f"adapter: unknown integrity.root.kind {k!r}")


def strip_hash_suffix(raw, hexhash):
    """For prefix-chained logs: the chained text is the record minus its own
    trailing hash member, whatever the member is called."""
    m = re.search(r',\s*"[A-Za-z0-9_]+"\s*:\s*"' + re.escape(hexhash) + r'"\s*\}\s*$', raw)
    if not m:
        return None
    return raw[: m.start()]


def rec_hash(prev, r, ad, prev_raw=b""):
    """Recompute the binding for one record. Returns hex or None."""
    mech = ad["integrity"]["mechanism"]
    hf = ad["integrity"].get("hash_field")
    if mech == "sha256-chain-prefix":
        if not r.hash:
            return None
        text = strip_hash_suffix(r.raw, r.hash)
        if text is None:
            return None
        return sha256_hex(prev + text.encode())
    if mech == "sha256-chain-canonical":
        body = {k: v for k, v in r.obj.items() if k != hf}
        return sha256_hex(prev.hex().encode() + canon(body).encode())
    if mech == "sha256-prev-raw":
        # AWS CloudTrail's digest chain: each digest file carries the SHA-256 of
        # the PREVIOUS digest file's bytes. Modelled here with one digest per
        # line, which is what the chain is.
        return sha256_hex(prev_raw) if prev_raw else ""
    if mech == "sha256-prev-field":
        pf = ad["integrity"]["prev_field"]
        body = {k: v for k, v in r.obj.items() if k not in (hf, pf)}
        return sha256_hex(str(dig(r.obj, pf) or "").encode() + canon(body).encode())
    raise SystemExit(f"adapter: unknown integrity.mechanism {mech!r}")


def check_l1(recs, ad, res):
    mech = ad["integrity"]["mechanism"]
    if mech == "none":
        res.fail("VLC-L1-1", "adapter declares no integrity binding")
        res.fail("VLC-L1-2", "no mechanism to recompute")
        res.fail("VLC-L1-3", "no end marker binding")
        return None

    prev = chain_root(recs, ad)
    if prev is None:
        res.fail("VLC-L1-1", "chain root not derivable from the delivered set")
        return None

    skip_first = ad["integrity"].get("root", {}).get("kind") == "field_of_first_record"
    body = recs[1:] if skip_first else recs
    # the first record's own hash must equal the root when the root is derived
    # from it -- otherwise the root is unpinned and L1 is vacuous
    if skip_first and recs[0].hash and recs[0].hash != prev.hex():
        res.fail("VLC-L1-1", "root record hash does not equal the derived root")
        return None

    em = ad["integrity"].get("end_marker")
    end = None
    if em:
        last = recs[-1]
        if last.cls != em.get("class"):
            res.fail("VLC-L1-3", f"last record class is {last.cls!r}, "
                                 f"expected {em.get('class')!r}: truncation undetectable")
        else:
            end = last
            body = body[:-1]

    prev_raw = b""
    for r in body:
        h = rec_hash(prev, r, ad, prev_raw)
        if h is None:
            res.fail("VLC-L1-1", f"record {r.i} carries no recomputable binding")
            return None
        if h != (r.hash or ""):
            res.fail("VLC-L1-1", f"binding broken at record {r.i}")
            return None
        prev_raw = r.raw.encode()
        if h:
            prev = bytes.fromhex(h)

    if end is not None:
        claimed = dig(end.obj, em.get("head_field", "head"))
        if claimed is None:
            res.fail("VLC-L1-3", "end marker carries no head value")
        elif str(claimed) != prev.hex():
            res.fail("VLC-L1-3", "end marker head does not match the recomputed binding")
        else:
            res.ok("VLC-L1-3")
        # Some designs chain the end marker; others make it commit to the head as
        # it stood before itself. The adapter says which.
        if end.hash and em.get("self_bound", True):
            h = rec_hash(prev, end, ad)
            if h is not None and h != end.hash:
                res.fail("VLC-L1-1", "end marker binding broken")
                return None
            if h is not None:
                prev = bytes.fromhex(h)
    else:
        res.fail("VLC-L1-3", "adapter declares no end marker: truncation undetectable")

    res.ok("VLC-L1-1")
    res.ok("VLC-L1-2") if ad["integrity"].get("documented", True) else \
        res.fail("VLC-L1-2", "adapter marks the mechanism as undocumented")
    prim = ad["integrity"].get("primitive", "SHA-256")
    if ad["integrity"].get("primitive_documented", True):
        res.ok("VLC-L1-4", f"primitive {prim}")
    else:
        res.fail("VLC-L1-4", "primitive strength/lifetime not documented")
    return prev.hex()


# ===========================================================================
# LEVEL 2 -- loss accounting
# ===========================================================================
def check_l2(recs, ad, res):
    lo = ad.get("loss")
    if not lo or lo.get("mode") == "none":
        res.fail("VLC-L2-1", "adapter declares no production count or ordinal")
        res.fail("VLC-L2-5", "no completeness identity is computable")
        return None
    mode = lo.get("mode", "declaration")

    non_event = set(ad.get("non_event_classes", []))
    markers = set(ad.get("marker_classes", []))
    # The delivered count is every BOUND record the producer wrote, excluding
    # the frame itself (root and end marker).  It is the verifier's own count,
    # and the identity's whole substance is that it must agree with a figure
    # the PRODUCER asserted independently.
    delivered = [r for r in recs if r.cls not in markers]

    # --- produced ---------------------------------------------------------
    p = lo.get("produced", {})
    kind = p.get("kind")
    produced = None
    if kind == "field_of_end_marker":
        em = ad["integrity"].get("end_marker", {})
        last = recs[-1]
        if last.cls == em.get("class"):
            v = dig(last.obj, p["field"])
            produced = int(v) if v is not None else None
    elif kind == "max_ordinal":
        vals = [dig(r.obj, p["field"]) for r in recs]
        vals = [int(v) for v in vals if v is not None]
        produced = (max(vals) - min(vals) + 1) if vals else None
    elif kind == "sum_of_end_marker_fields":
        em = ad["integrity"].get("end_marker", {})
        last = recs[-1]
        if last.cls == em.get("class"):
            vs = [dig(last.obj, f) for f in p["fields"]]
            if all(v is not None for v in vs):
                produced = sum(int(v) for v in vs)
    elif kind == "field_of_any":
        for r in reversed(recs):
            v = dig(r.obj, p["field"])
            if v is not None:
                produced = int(v)
                break
    else:
        res.fail("VLC-L2-1", f"adapter: unknown loss.produced.kind {kind!r}")
        return None

    if produced is None:
        res.fail("VLC-L2-1", "produced count not derivable from the delivered set")
        return None
    res.ok("VLC-L2-1", f"produced = {produced}")

    # --- declared loss ----------------------------------------------------
    declared = 0
    n_decls = 0
    if mode == "declaration":
        dc = lo.get("declaration_class")
        for r in recs:
            if r.cls == dc:
                n_decls += 1
                declared += int(dig(r.obj, lo.get("count_field", "lost")) or 0)
        if dc is None:
            res.fail("VLC-L2-2", "adapter names no loss-declaration class")
        else:
            res.ok("VLC-L2-2", f"{n_decls} declaration(s), {declared} record(s) declared lost")
    elif mode == "ordinal":
        of = lo.get("ordinal_field", p.get("field"))
        vals = sorted(int(dig(r.obj, of)) for r in recs
                      if dig(r.obj, of) is not None)
        holes = 0
        for a, b in zip(vals, vals[1:]):
            if b > a + 1:
                holes += b - a - 1
        declared = holes
        n_decls = 1 if holes else 0
        res.ok("VLC-L2-2", f"loss detected from ordinal holes: {holes}")
    else:
        res.fail("VLC-L2-2", f"adapter: unknown loss.mode {mode!r}")
        return None

    # --- L2-3: is the declaration integrity-bound? ------------------------
    if ad["integrity"]["mechanism"] == "none":
        res.fail("VLC-L2-3", "no integrity binding, so declarations are removable")
    elif mode == "declaration":
        bound = all(r.hash for r in recs if r.cls == lo.get("declaration_class"))
        res.ok("VLC-L2-3") if bound or n_decls == 0 else \
            res.fail("VLC-L2-3", "a loss declaration carries no binding")
    else:
        res.ok("VLC-L2-3", "loss is implied by bound ordinals")

    # --- L2-4: declared overflow behaviour --------------------------------
    ob = lo.get("overflow_behaviour")
    if ob in ("block", "drop_oldest", "drop_newest", "drop_counted"):
        res.ok("VLC-L2-4", ob)
    elif ob == "silent":
        res.fail("VLC-L2-4", "producer cannot detect discard: L2 not claimable")
    else:
        res.fail("VLC-L2-4", "overflow behaviour not declared")

    # --- L2-5/6: the identity --------------------------------------------
    lhs = len(delivered) + declared
    if lhs == produced:
        res.ok("VLC-L2-5", f"{len(delivered)} delivered + {declared} declared lost == {produced} produced")
        res.ok("VLC-L2-6")
    else:
        res.fail("VLC-L2-5", f"identity does not close: {len(delivered)} + {declared} "
                             f"= {lhs} != {produced} produced "
                             f"({produced - lhs} record(s) unaccounted for)")
        res.fail("VLC-L2-6", "log is NOT COMPLETE")
    return {"produced": produced, "delivered": len(delivered), "declared_lost": declared}


# ===========================================================================
# LEVEL 3 -- coverage declaration
# ===========================================================================
def check_l3(recs, ad, res):
    cv = ad.get("coverage")
    if not cv or cv.get("mode") == "none":
        res.fail("VLC-L3-1", "adapter declares no coverage declaration")
        res.fail("VLC-L3-6", "observation surface is not enumerable and is not declared as such")
        return None
    if cv.get("mode") == "non_enumerable":
        res.fail("VLC-L3-1", "observation surface declared non-enumerable")
        res.ok("VLC-L3-6", "declared non-enumerable honestly; L3 correctly not claimable")
        return None

    dc = cv.get("declaration_class")
    decls = [r for r in recs if r.cls == dc]
    if not decls:
        res.fail("VLC-L3-1", f"no {dc!r} record in the delivered set: silence about a "
                             f"source is indistinguishable from absence of the source")
        return None

    d0 = decls[0]
    att = as_list(dig(d0.obj, cv.get("attached_field")))
    una = as_list(dig(d0.obj, cv.get("unattached_field")))
    des = as_list(dig(d0.obj, cv.get("by_design_field")))
    basis = dig(d0.obj, cv.get("basis_field")) if cv.get("basis_field") else None

    if not att:
        res.fail("VLC-L3-1", "coverage declaration names no attached sources")
    else:
        res.ok("VLC-L3-1", f"{len(att)} attached, {len(una)} unattached-here, "
                           f"{len(des)} excluded by design")
    if basis:
        res.ok("VLC-L3-1d", f"exhaustiveness criterion: {basis}")
    else:
        res.fail("VLC-L3-1d", "no criterion given for why the enumeration is exhaustive")

    if ad["integrity"]["mechanism"] == "none" or not d0.hash:
        res.fail("VLC-L3-2", "coverage declaration is not integrity-bound: it is an assertion")
    else:
        res.ok("VLC-L3-2")

    # epoch anchoring: first coverage record must precede any event record
    non_event = set(ad.get("non_event_classes", []))
    first_event = next((r.i for r in recs if r.cls not in non_event), None)
    if first_event is not None and d0.i > first_event:
        res.fail("VLC-L3-3", f"first event at record {first_event} precedes the coverage "
                             f"declaration at {d0.i}: that interval is undeclared")
    else:
        res.ok("VLC-L3-3", f"declared at record {d0.i}, before any event")

    # L3-4 is a property of the PRODUCER, not of the log. The log can only say
    # whether such a test exists and was run.
    t = cv.get("bidirectional_test")
    if t and t.get("exists") and t.get("negative_control"):
        res.ok("VLC-L3-4", t.get("ref", "declared, with negative control"))
    elif t and t.get("exists"):
        res.fail("VLC-L3-4", "coverage test exists but has no negative control: a producer "
                             "that declares a source it does not observe is undetected")
    else:
        res.fail("VLC-L3-4", "no bidirectional coverage test declared")

    if dc in non_event:
        res.ok("VLC-L3-5")
    else:
        res.fail("VLC-L3-5", "coverage declarations are counted as events: identity inflated")

    res.ok("VLC-L3-6", "surface enumerated")
    return {"attached": att, "unattached": una, "by_design": des}


# ===========================================================================
# LEVEL 4 -- policy binding
# ===========================================================================
def check_l4(recs, ad, res):
    po = ad.get("policy")
    if not po or po.get("mode") == "none":
        res.fail("VLC-L4-1", "adapter declares no policy binding")
        return None
    if po.get("mode") == "observation_only":
        res.ok("VLC-L4-1", "log records no verdicts; L3 is the terminal level and is declared")
        return {"terminal": 3}

    mode = po.get("mode")
    if mode == "chain_root":
        r = ad["integrity"].get("root", {})
        if r.get("kind") == "field_of_first_record" and r.get("field") == po.get("digest_field"):
            res.ok("VLC-L4-1", "the policy digest roots the binding: re-rooting is detectable")
        else:
            res.fail("VLC-L4-1", "policy digest does not root the binding")
    elif mode == "per_record":
        n = sum(1 for r in recs if dig(r.obj, po.get("digest_field")) is not None)
        if n == len([r for r in recs if r.cls not in set(ad.get("non_event_classes", []))]):
            res.ok("VLC-L4-1", "every event record carries the policy digest")
        else:
            res.fail("VLC-L4-1", f"only {n} record(s) carry a policy digest")
    else:
        res.fail("VLC-L4-1", f"adapter: unknown policy.mode {mode!r}")

    cc = po.get("change_class")
    changes = [r for r in recs if cc and r.cls == cc]
    if cc is None:
        res.fail("VLC-L4-2", "adapter names no policy-change record class")
    else:
        res.ok("VLC-L4-2", f"{len(changes)} in-log policy change(s)")

    rp = po.get("replay", {})
    if rp.get("deterministic") is False:
        res.fail("VLC-L4-4", "decision function declared non-deterministic; L4 not claimable")
    elif rp.get("reference"):
        res.ok("VLC-L4-3", rp["reference"])
        res.ok("VLC-L4-4", "deterministic and replayable")
    else:
        res.fail("VLC-L4-3", "no independently re-evaluable policy artefact referenced")
    return {"changes": len(changes)}


# ===========================================================================
# LEVEL 5 -- independently witnessed
# ===========================================================================
def check_l5(recs, ad, res, own_level_reqs):
    """L5 is a property of WHO WROTE the log, so it is evaluated from the
    adapter's declared trust boundary plus the log's own standing. A checker
    cannot infer independence from bytes -- but it CAN refuse to let a
    provider leave the question unanswered, which is the whole point of
    VLC-L5-2."""
    ind = ad.get("independence")
    if not ind:
        res.fail("VLC-L5-1", "adapter declares no trust boundary between producer "
                             "and audited process")
        res.fail("VLC-L5-2", "boundary not stated")
        return None

    mode = ind.get("mode")
    # "in_process" and "in_band" are honest self-declarations of a self-report.
    if mode in ("in_process", "self_reported", "in_band"):
        res.fail("VLC-L5-1", f"producer declared {mode!r}: the audited process writes "
                             f"its own record, so the record is a claim")
    elif mode in ("kernel", "hypervisor", "external_host", "network_tap",
                  "hardware", "external_proxy"):
        if ind.get("audited_process_can_write_records", True):
            res.fail("VLC-L5-1", "producer is out-of-process but the audited process "
                                 "can still write its records")
        else:
            res.ok("VLC-L5-1", f"{mode}; audited process cannot write, detach or "
                               f"suppress the record")
    else:
        res.fail("VLC-L5-1", f"adapter: unrecognised independence.mode {mode!r}")

    if ind.get("boundary_statement"):
        res.ok("VLC-L5-2", ind["boundary_statement"][:120])
    else:
        res.fail("VLC-L5-2", "no statement of what a fully-compromised audited process "
                             "could still do to the record")

    rc = ind.get("reconciliation")
    if not rc:
        res.fail("VLC-L5-3", "no reconciliation against a self-reported record declared")
        res.fail("VLC-L5-5", "no reconciliation scope to declare")
    else:
        if rc.get("bidirectional"):
            res.ok("VLC-L5-3", rc.get("ref", "both directions reported"))
        else:
            res.fail("VLC-L5-3", "reconciliation reports one direction only: half a "
                                 "substitution is not a detection")
        if rc.get("scope_declared"):
            res.ok("VLC-L5-5", "scope and every exclusion recorded with the result")
        else:
            res.fail("VLC-L5-5", "reconciliation scope not recorded with the result")

    # VLC-L5-4: the witness is scored by the same rules as everyone else.
    own = 0
    for n in (1, 2, 3, 4):
        if all(res.r.get(x, (FAIL, ""))[0] == PASS for x in own_level_reqs[n]):
            own = n
        else:
            break
    if own >= 3:
        res.ok("VLC-L5-4", f"the witnessing log itself demonstrates L{own}")
    else:
        res.fail("VLC-L5-4", f"the witnessing log itself is only L{own}: a witness with "
                             f"an undeclared coverage gap agrees with a lie honestly")
    return {"mode": mode, "witness_own_level": own}


# ===========================================================================
# result accumulator
# ===========================================================================
LEVEL_REQS = {
    1: ["VLC-L1-1", "VLC-L1-2", "VLC-L1-3", "VLC-L1-4"],
    2: ["VLC-L2-1", "VLC-L2-2", "VLC-L2-3", "VLC-L2-4", "VLC-L2-5", "VLC-L2-6"],
    3: ["VLC-L3-1", "VLC-L3-1d", "VLC-L3-2", "VLC-L3-3", "VLC-L3-4", "VLC-L3-5", "VLC-L3-6"],
    4: ["VLC-L4-1", "VLC-L4-2", "VLC-L4-3", "VLC-L4-4"],
    5: ["VLC-L5-1", "VLC-L5-2", "VLC-L5-3", "VLC-L5-4", "VLC-L5-5"],
}


class Results:
    def __init__(self):
        self.r = {}

    def ok(self, rid, note=""):
        self.r.setdefault(rid, (PASS, note))

    def fail(self, rid, note=""):
        self.r[rid] = (FAIL, note)          # failure always wins

    def level(self):
        lv = 0
        for n in (1, 2, 3, 4, 5):
            reqs = LEVEL_REQS[n]
            if all(self.r.get(x, (FAIL, "not evaluated"))[0] == PASS for x in reqs):
                lv = n
            else:
                break
        return lv

    def terminal_note(self):
        s, _ = self.r.get("VLC-L4-1", (FAIL, ""))
        return s


# ===========================================================================
# mutations -- Annex A negative controls, applied to the log in memory
# ===========================================================================
def mutate(lines, how, ad):
    ls = list(lines)
    if how == "flip-byte":
        i = len(ls) // 2
        s = ls[i]
        j = max(1, len(s) // 2)
        ls[i] = s[:j] + ("0" if s[j] != "0" else "1") + s[j + 1:]
    elif how == "drop-interior":
        del ls[len(ls) // 2]
    elif how == "truncate-tail":
        ls = ls[:-1]
    elif how in ("drop-loss-decl", "drop-coverage"):
        cf = ad.get("record_class_field", "class")
        key = "loss" if how == "drop-loss-decl" else "coverage"
        cls = (ad.get(key) or {}).get("declaration_class")
        if cls is None:
            raise SystemExit(f"adapter names no {key} declaration class to remove")
        keep = []
        for l in ls:
            try:
                o = json.loads(l)
            except Exception:
                keep.append(l); continue
            if str(dig(o, cf)) != str(cls):
                keep.append(l)
        ls = keep
    elif how == "rebase-policy":
        ls[0] = re.sub(r'("policy_digest"\s*:\s*")([0-9a-f]{4})',
                       lambda m: m.group(1) + ("dead" if m.group(2) != "dead" else "beef"), ls[0])
        if ls[0] == lines[0]:
            raise SystemExit("no policy digest in the root record to re-base")
    else:
        raise SystemExit(f"unknown mutation {how!r}")
    return ls


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description=f"{VERSION} conformance checker")
    ap.add_argument("--log", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--expect", type=int, choices=[0, 1, 2, 3, 4, 5],
                    help="require exactly this level; exit 1 otherwise")
    ap.add_argument("--mutate", help="apply an Annex A mutation before checking")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    ad = json.load(open(a.adapter))
    for k in ("name", "integrity"):
        if k not in ad:
            raise SystemExit(f"adapter missing required key {k!r}")

    path = a.log
    tmp = None
    if a.mutate:
        lines = [l.rstrip("\n") for l in open(path) if l.strip()]
        lines = mutate(lines, a.mutate, ad)
        tmp = path + f".mutated.{a.mutate}"
        open(tmp, "w").write("\n".join(lines) + "\n")
        path = tmp

    res = Results()
    head = None
    try:
        recs = load(path, ad)
        head = check_l1(recs, ad, res)
        check_l2(recs, ad, res)
        check_l3(recs, ad, res)
        check_l4(recs, ad, res)
        check_l5(recs, ad, res, LEVEL_REQS)
    except LogError as e:
        res.fail("VLC-L1-1", f"delivered set unreadable: {e}")
    lv = res.level()

    if tmp:
        os.unlink(tmp)

    if a.json:
        print(json.dumps({
            "spec": VERSION, "adapter": ad["name"], "log": a.log,
            "mutation": a.mutate, "level_demonstrated": lv, "head": head,
            "requirements": {k: {"status": v[0], "note": v[1]} for k, v in sorted(res.r.items())},
        }, indent=2))
    else:
        print(f"{VERSION} — conformance report")
        print(f"  log      : {a.log}" + (f"  [mutated: {a.mutate}]" if a.mutate else ""))
        print(f"  adapter  : {ad['name']} — {ad.get('description','')}")
        print(f"  producer : {ad.get('producer','(unstated)')}")
        print()
        for n in (1, 2, 3, 4, 5):
            for rid in LEVEL_REQS[n]:
                st, note = res.r.get(rid, (FAIL, "not evaluated"))
                mark = "  ok  " if st == PASS else "  FAIL"
                print(f"{mark}  {rid:<12} {note}")
            print()
        print(f"  LEVEL DEMONSTRATED: L{lv}")
        if lv < 5:
            nxt = LEVEL_REQS[lv + 1]
            bad = [r for r in nxt if res.r.get(r, (FAIL, ""))[0] != PASS]
            print(f"  blocked from L{lv+1} by: {', '.join(bad)}")

    if a.expect is not None and lv != a.expect:
        print(f"\nEXPECTED L{a.expect}, DEMONSTRATED L{lv}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

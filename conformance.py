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

VERSION = "VLC-1 1.1.1-draft"

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


def _no_duplicate_names(pairs):
    # RFC 7493 I-JSON 2.3: duplicate member names make a record mean different
    # things to a last-wins and a first-wins parser, and the canonical-JSON
    # mechanisms hash the PARSED record, so the edit changes no hash.
    d = {}
    for k, v in pairs:
        if k in d:
            raise LogError(f"duplicate member name {k!r}: two parsers can read different values")
        d[k] = v
    return d


def _reject_nonfinite(tok):
    raise LogError(f"non-finite number {tok}: not representable in canonical JSON")


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
            o = json.loads(l, object_pairs_hook=_no_duplicate_names,
                           parse_constant=_reject_nonfinite)
        except LogError as e:
            raise LogError(f"record {i}: {e}")
        except Exception:
            raise LogError(f"record {i} is not parseable as JSON")
        if not isinstance(o, dict):
            raise LogError(f"record {i} is not a JSON object")
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


# Annex J -- interval coverage (Corrigendum 1, EXT-002). Kept in its own
# module so the scoring logic is testable standalone; see test_check_l3i.py.
# Reported as a QUALIFIER, not a rung: LEVEL_REQS is keyed by integers and the
# level arithmetic indexes it numerically, so a "3i" key would break it.
try:
    from check_l3i import check_l3i
except ImportError:                                    # pragma: no cover
    def check_l3i(recs, ad, res):                      # noqa: D103
        return None


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
    # EXT-013. Under sha256-prev-field each record's hash covers its OWN prev
    # field, so a record is self-consistent whatever that field says. Nothing
    # compared it with the hash of the record actually before it, so deleting
    # or reordering records left every hash valid. The link is checked here.
    link_field = ad["integrity"].get("prev_field") if mech == "sha256-prev-field" else None
    for r in body:
        if link_field is not None and str(dig(r.obj, link_field) or "") != prev.hex():
            res.fail("VLC-L1-1", f"record {r.i} does not link to its predecessor")
            return None
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
            if link_field is not None and str(dig(end.obj, link_field) or "") != prev.hex():
                res.fail("VLC-L1-1", "end marker does not link to its predecessor")
                return None
            h = rec_hash(prev, end, ad)
            if h is not None and h != end.hash:
                res.fail("VLC-L1-1", "end marker binding broken")
                return None
            if h is not None:
                prev = bytes.fromhex(h)
    else:
        res.fail("VLC-L1-3", "adapter declares no end marker: truncation undetectable")

    # EXT-008. On the log alone this establishes that the chain is internally
    # consistent from the root the log states. It does not establish resistance
    # to a complete rewrite: anyone who can recompute the binding can alter a
    # record and re-derive every later link and the end marker. That needs a
    # root or head the verifier obtained independently of the log (VLC-L1-1's
    # "published root"), and the report says so rather than implying more.
    res.ok("VLC-L1-1", "chain consistent from the root the log states; a complete "
                       "rewrite is detectable only against an independently held root or head")

    # These two used to default to TRUE, which meant an adapter that said
    # nothing at all passed them. That is not trusting an assertion, it is
    # manufacturing one out of silence. Both must now be stated explicitly.
    doc = ad["integrity"].get("documented")
    if doc is True:
        res.ok("VLC-L1-2", ad["integrity"].get("documentation", "declared documented"))
    elif doc is False:
        res.fail("VLC-L1-2", "adapter marks the mechanism as undocumented")
    else:
        res.fail("VLC-L1-2", "adapter does not state whether the mechanism is "
                             "documented; silence is not a declaration")

    prim = ad["integrity"].get("primitive")
    pdoc = ad["integrity"].get("primitive_documented")
    if pdoc is True and prim:
        res.ok("VLC-L1-4", f"primitive {prim}")
    elif pdoc is False:
        res.fail("VLC-L1-4", "primitive strength/lifetime not documented")
    else:
        res.fail("VLC-L1-4", "adapter does not name the primitive and state that "
                             "its strength and lifetime are documented")
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
    # SPEC VLC-L2-5: "|delivered event records| + sum(loss declarations) ==
    # |records produced|".  EVENT records.  A coverage declaration is not an
    # event, and a loss declaration is not an event either -- counting the DROP
    # record as delivered while also counting its lost_total on the other side
    # of the identity is a double count.  non_event was computed here and never
    # used, so the arithmetic silently ran over every bound record.
    # Reported by pipavlo82, 2026-09-21.
    delivered = [r for r in recs if r.cls not in markers and r.cls not in non_event]

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
        # EXT-014. The high-water mark is a quantity the PRODUCER declares, as
        # VLC-L2-5 says. It was computed as max - min + 1 over the ordinals that
        # happened to arrive, so losing records at either end of the sequence
        # moved both bounds with them and the identity still closed. Now the
        # end marker must carry the producer's final ordinal, and the adapter
        # must state where the sequence starts; neither is inferred.
        em = ad["integrity"].get("end_marker", {})
        hwf, start = p.get("high_water_field"), p.get("start")
        last = recs[-1]
        if hwf is None or type(start) is not int:
            res.fail("VLC-L2-1", "max_ordinal needs produced.high_water_field (on the end "
                                 "marker) and an integer produced.start; the bounds of the "
                                 "sequence are not inferred from what arrived")
            return None
        if last.cls == em.get("class"):
            hw = dig(last.obj, hwf)
            produced = hw - start + 1 if type(hw) is int and hw >= start - 1 else None
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
    if mode in ("declaration", "ordinal"):
        # EXT-006. VLC-L2-2 requires every loss declaration to state the number
        # lost AND the interval in which it occurred. The count was read with
        # int(... or 0), so a missing count read as zero, a negative count was
        # summed, and the interval was never looked at.
        # Ordinal mode reads declarations the same way (one definition of a
        # well-formed declaration for both modes) and then requires every
        # ordinal hole to be covered by one.
        dc = lo.get("declaration_class")
        iv = lo.get("interval_fields")            # [from_field, to_field]
        by_pos = lo.get("interval") == "position" # the record's place in the chain is the interval
        ordf = lo.get("event_ordinal_field")      # lets ranges be checked against delivered events
        if mode == "ordinal":
            of = lo.get("ordinal_field", p.get("field"))
            ordf = ordf or of
        problems = []
        ranges = []
        for r in recs:
            if r.cls != dc:
                continue
            n_decls += 1
            v = dig(r.obj, lo.get("count_field", "lost"))
            if type(v) is not int or v < 0:
                problems.append(f"record {r.i}: lost count {v!r} is not a non-negative integer")
                continue
            declared += v
            if iv:
                a, b = dig(r.obj, iv[0]), dig(r.obj, iv[1])
                if type(a) is not int or type(b) is not int or a < 0 or b < a:
                    problems.append(f"record {r.i}: interval {a!r}..{b!r} is missing or malformed")
                elif b - a + 1 != v:
                    problems.append(f"record {r.i}: interval {a}..{b} covers {b - a + 1} "
                                    f"record(s) but declares {v} lost")
                else:
                    ranges.append((a, b, r.i))
            elif not by_pos:
                problems.append(f"record {r.i}: no interval stated")
        if ordf and ranges:
            present = {dig(r.obj, ordf) for r in delivered}
            for a, b, at in ranges:
                hit = sorted(x for x in present if type(x) is int and a <= x <= b)
                if hit:
                    problems.append(f"record {at}: declares {a}..{b} lost, but {hit} "
                                    f"were delivered")
        if mode == "ordinal":
            vals = sorted(x for x in (dig(r.obj, of) for r in recs) if type(x) is int)
            holes = [(a + 1, b - 1) for a, b in zip(vals, vals[1:]) if b > a + 1]
            uncovered = [h for h in holes
                         if not any(a <= h[0] and h[1] <= b for a, b, _ in ranges)]
            if uncovered:
                problems.append(f"{len(uncovered)} ordinal gap(s) with no producer loss declaration: "
                                f"{uncovered[:5]}; a gap the producer did not declare is silent loss")
        if dc is None:
            res.fail("VLC-L2-2", "adapter names no loss-declaration class")
        elif n_decls and not iv and not by_pos:
            res.fail("VLC-L2-2", "adapter says neither where a loss declaration states its "
                                 "interval nor that its chain position is the interval")
        elif problems:
            res.fail("VLC-L2-2", "; ".join(problems[:3]) +
                     (f" (+{len(problems) - 3} more)" if len(problems) > 3 else ""))
        else:
            res.ok("VLC-L2-2", f"{n_decls} declaration(s), {declared} record(s) declared lost")
    else:
        res.fail("VLC-L2-2", f"adapter: unknown loss.mode {mode!r}")
        return None

    # --- L2-3: is the declaration integrity-bound? ------------------------
    if ad["integrity"]["mechanism"] == "none":
        res.fail("VLC-L2-3", "no integrity binding, so declarations are removable")
    elif mode in ("declaration", "ordinal"):
        bound = all(r.hash for r in recs if r.cls == lo.get("declaration_class"))
        res.ok("VLC-L2-3") if bound or n_decls == 0 else \
            res.fail("VLC-L2-3", "a loss declaration carries no binding")

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
        res.fail("VLC-L3-1a", "adapter declares no coverage declaration")
        res.fail("VLC-L3-6", "observation surface is not enumerable and is not declared as such")
        return None
    if cv.get("mode") == "non_enumerable":
        res.fail("VLC-L3-1a", "observation surface declared non-enumerable")
        res.ok("VLC-L3-6", "declared non-enumerable honestly; L3 correctly not claimable")
        return None

    dc = cv.get("declaration_class")
    decls = [r for r in recs if r.cls == dc]
    if not decls:
        res.fail("VLC-L3-1a", f"no {dc!r} record in the delivered set: silence about a "
                             f"source is indistinguishable from absence of the source")
        return None

    d0 = decls[0]
    att = as_list(dig(d0.obj, cv.get("attached_field")))
    una = as_list(dig(d0.obj, cv.get("unattached_field")))
    des = as_list(dig(d0.obj, cv.get("by_design_field")))
    basis = dig(d0.obj, cv.get("basis_field")) if cv.get("basis_field") else None

    # EXT-006. Only the first declaration was inspected, and an absent category
    # read as an empty one. A later declaration could drop its basis, and a
    # declaration that simply omitted "unattached" read as "nothing unattached".
    # Every declaration is checked, and each category field must be PRESENT
    # (it may be empty; it may not be missing).
    malformed = []
    for d in decls:
        for key in ("attached_field", "unattached_field", "by_design_field"):
            fld = cv.get(key)
            if fld and dig(d.obj, fld) is None:
                malformed.append(f"record {d.i} omits {fld!r}")
        if not as_list(dig(d.obj, cv.get("attached_field"))):
            malformed.append(f"record {d.i} names no attached sources")
    no_basis = [d.i for d in decls
                if cv.get("basis_field") and not dig(d.obj, cv.get("basis_field"))]
    if cv.get("basis_field") is None:
        basis = None

    if malformed:
        res.fail("VLC-L3-1a", "; ".join(malformed[:3]) +
                 (f" (+{len(malformed) - 3} more)" if len(malformed) > 3 else ""))
    else:
        # L3-1a: the declaration is present and well-formed — recomputed.
        # L3-1b: it describes the surface actually observed — relayed. A
        # verifier reading the log cannot check the second, and saying it can
        # is the defect EXT-001 reported.
        res.ok("VLC-L3-1b", "declared surface accepted as stated by the "
                            "producer; not recomputable from the log")
        res.ok("VLC-L3-1a", f"{len(att)} attached, {len(una)} unattached-here, "
                           f"{len(des)} excluded by design")
    if basis and not no_basis:
        res.ok("VLC-L3-1d", f"exhaustiveness criterion: {basis}")
    elif basis and no_basis:
        res.fail("VLC-L3-1d", f"coverage declaration(s) at record(s) {no_basis} give no "
                              f"criterion for why the enumeration is exhaustive")
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
        # EXT-006. Counted digests across ALL records and compared the total
        # to the number of events, so a non-event carrying a digest could stand
        # in for an event missing one. Each event is now checked on its own.
        ne = set(ad.get("non_event_classes", []))
        missing = [r.i for r in recs if r.cls not in ne
                   and not isinstance(dig(r.obj, po.get("digest_field")), str)]
        if not missing:
            res.ok("VLC-L4-1", "every event record carries the policy digest")
        else:
            res.fail("VLC-L4-1", f"{len(missing)} event record(s) carry no policy digest, "
                                 f"first at record {missing[0]}")
    else:
        res.fail("VLC-L4-1", f"adapter: unknown policy.mode {mode!r}")

    cc = po.get("change_class")
    changes = [r for r in recs if cc and r.cls == cc]
    # EXT-006. VLC-L4-2 requires each change record to carry the digests
    # before and after. Only the record's existence was checked.
    bf, af = po.get("change_before_field", "before"), po.get("change_after_field", "after")
    incomplete = [r.i for r in changes
                  if not isinstance(dig(r.obj, bf), str) or not dig(r.obj, bf)
                  or not isinstance(dig(r.obj, af), str) or not dig(r.obj, af)]
    if cc is None:
        res.fail("VLC-L4-2", "adapter names no policy-change record class")
    elif incomplete:
        res.fail("VLC-L4-2", f"policy change record(s) {incomplete} do not carry both the "
                             f"{bf!r} and {af!r} digests")
    else:
        res.ok("VLC-L4-2", f"{len(changes)} in-log policy change(s)")

    rp = po.get("replay", {})
    # EXT-006. Determinism was accepted whenever a reference existed, even with
    # no "deterministic" flag at all. VLC-L4-4 requires it to be declared.
    if rp.get("deterministic") is not True:
        res.fail("VLC-L4-4", "decision function not declared deterministic; L4 not claimable"
                 if rp.get("deterministic") is False else
                 "determinism not declared; absence is not a declaration")
        if rp.get("reference"):
            res.ok("VLC-L4-3", rp["reference"])
        else:
            res.fail("VLC-L4-3", "no independently re-evaluable policy artefact referenced")
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
    # Scored on STRUCTURAL requirements only. VLC-L5-4 is classed structural,
    # so its result must not depend on anything the adapter merely asserts.
    # Counting every requirement let an attested one (VLC-L3-1d, which reads
    # the adapter's basis_field) decide a structural result: pointing
    # basis_field at any non-empty field flipped this check from FAIL to ok
    # with the log unchanged.  Reported by pipavlo82, 2026-09-21 (EXT-004).
    own = 0
    for n in (1, 2, 3, 4):
        structural_reqs = [x for x in own_level_reqs[n]
                           if EVIDENCE_CLASS.get(x) == "structural"]
        if all(res.r.get(x, (FAIL, ""))[0] == PASS for x in structural_reqs):
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
# ===========================================================================
# Structural vs attested — the distinction this checker used to blur.
#
# A STRUCTURAL requirement is decided by recomputing something from the
# delivered evidence: the chain, the completeness identity, the presence and
# binding of a coverage declaration. The checker establishes it.
#
# An ATTESTED requirement is decided by a statement the producer makes through
# the adapter: that the mechanism is documented, that a bidirectional coverage
# test exists, that the producer sits outside the audited process's control.
# The checker RELAYS it. It cannot establish it from bytes, and saying it can
# was the single weakest claim this project made.
#
# Two consequences worth stating plainly:
#   * every report now carries BOTH levels, and the structural one is the one
#     an adversary cannot inflate by writing a generous adapter;
#   * L5 is attested by construction, so the structural ceiling is L4. That is
#     not a gap in the checker. Independence is a fact about who holds the pen,
#     and no amount of reading the bytes will settle it.
# ===========================================================================
EVIDENCE_CLASS = {
    "VLC-L1-1": "structural", "VLC-L1-2": "attested",
    "VLC-L1-3": "structural", "VLC-L1-4": "attested",
    "VLC-L2-1": "structural", "VLC-L2-2": "structural",
    "VLC-L2-3": "structural", "VLC-L2-4": "attested",
    "VLC-L2-5": "structural", "VLC-L2-6": "structural",
    # Corrigendum 1, EXT-001 (Shahab K., 2026-09-13): presence of a coverage
    # declaration was raising the structural level, which VLC-V-3 forbids.
    # L3-1a is well-formedness, which a verifier recomputes. L3-1b is
    # correspondence to reality, which it cannot. There is no path to
    # structural for L3-1b or L3-1d.
    # Annex J. L3i-2 and L3i-4 are attested in every case: a verifier
    # recomputes a declared range and a witness's binding to a position, never
    # an attestor's honesty or its independence from the producer.
    "VLC-L3i-1": "structural", "VLC-L3i-2": "attested",
    "VLC-L3i-3": "structural", "VLC-L3i-4": "attested",
    "VLC-L3-1a": "structural", "VLC-L3-1b": "attested",
    "VLC-L3-1d": "attested",
    "VLC-L3-2": "structural", "VLC-L3-3": "structural",
    "VLC-L3-4": "attested",   "VLC-L3-5": "structural",
    "VLC-L3-6": "structural",
    "VLC-L4-1": "structural", "VLC-L4-2": "structural",
    "VLC-L4-3": "attested",   "VLC-L4-4": "attested",
    "VLC-L5-1": "attested",   "VLC-L5-2": "attested",
    "VLC-L5-3": "attested",   "VLC-L5-4": "structural",
    "VLC-L5-5": "attested",
}

LEVEL_REQS = {
    1: ["VLC-L1-1", "VLC-L1-2", "VLC-L1-3", "VLC-L1-4"],
    2: ["VLC-L2-1", "VLC-L2-2", "VLC-L2-3", "VLC-L2-4", "VLC-L2-5", "VLC-L2-6"],
    3: ["VLC-L3-1a", "VLC-L3-1b", "VLC-L3-1d", "VLC-L3-2", "VLC-L3-3",
        "VLC-L3-4", "VLC-L3-5", "VLC-L3-6"],
    4: ["VLC-L4-1", "VLC-L4-2", "VLC-L4-3", "VLC-L4-4"],
    5: ["VLC-L5-1", "VLC-L5-2", "VLC-L5-3", "VLC-L5-4", "VLC-L5-5"],
}


# Which levels can be reached from the bytes at all. L5 cannot: independence is
# a fact about WHO HOLDS THE PEN, and no amount of reading a log settles it. A
# structural report that claimed L5 would be making exactly the error this
# taxonomy exists to stop.
STRUCTURALLY_ATTAINABLE = {1: True, 2: True, 3: True, 4: True, 5: False}

# VLC-E-1 names the first five; VLC-E-5 adds the negative control, which the
# checker did not require until EXT-007.
EV_REQUIRED = ("test", "runner", "runner_digest", "output_digest", "result",
               "negative_control")
# VLC-E-6: a digest is written sha256: followed by 64 lowercase hex characters.
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def evidence_for(ad, rid):
    """An attested requirement may carry a reproducible evidence artefact.

    A bare `"negative_control": true` in an adapter is a promise. An entry
    naming the runner, its digest, the digest of its output and the result is
    something a reader can go and re-run. The checker cannot re-run it from
    here -- it has only the log -- but it CAN tell the difference between a
    claim and a citation, and report which one it was given.
    """
    evidence = ad.get("evidence") or {}
    if rid not in evidence:
        return None, ""                    # genuinely no entry
    ev = evidence[rid]
    # EXT-007. A present but malformed entry used to be treated as absent,
    # which let the requirement fall back to the bare assertion. VLC-E-2 says
    # an entry that is not a complete citation is weaker than no entry at all.
    if not isinstance(ev, dict):
        return False, f"evidence entry is malformed ({type(ev).__name__}, not an object)"
    missing = [k for k in EV_REQUIRED if not ev.get(k)]
    if missing:
        return False, f"evidence entry incomplete (missing {', '.join(missing)})"
    bad = [k for k, v in ev.items() if k.endswith("_digest")
           and not (isinstance(v, str) and DIGEST_RE.match(v))]
    if bad:
        return False, f"evidence entry has a malformed digest ({', '.join(bad)})"
    if str(ev.get("result")).upper() != "PASS":
        return False, f"evidence entry records result={ev.get('result')!r}"
    return True, f"{ev['test']} via {ev['runner']} (digests recorded)"


class Results:
    def __init__(self):
        self.r = {}
        self.ev = {}

    def ok(self, rid, note=""):
        self.r.setdefault(rid, (PASS, note))

    def fail(self, rid, note=""):
        self.r[rid] = (FAIL, note)          # failure always wins

    def attach_evidence(self, ad):
        """Record, per attested requirement, whether a reproducible artefact
        was supplied. Never upgrades a FAIL; evidence for a claim the log
        contradicts is not evidence."""
        for rid, cls in EVIDENCE_CLASS.items():
            if cls != "attested":
                continue
            ok, note = evidence_for(ad, rid)
            if ok is None:
                continue
            self.ev[rid] = (ok, note)
            if ok is False and self.r.get(rid, (FAIL, ""))[0] == PASS:
                self.fail(rid, note)

    def _level_over(self, classes, ceiling=None):
        lv = 0
        for n in (1, 2, 3, 4, 5):
            if ceiling is not None and not ceiling.get(n, True):
                break
            reqs = [x for x in LEVEL_REQS[n] if EVIDENCE_CLASS.get(x) in classes]
            if reqs and all(self.r.get(x, (FAIL, "not evaluated"))[0] == PASS
                            for x in reqs):
                lv = n
            else:
                break
        return lv

    def structural_level(self):
        """What the delivered evidence demonstrates on its own. An adversary
        cannot raise this by writing a more generous adapter."""
        return self._level_over(("structural",), STRUCTURALLY_ATTAINABLE)

    def attested_level(self):
        """Structural, plus what the producer asserts through the adapter."""
        return self._level_over(("structural", "attested"))

    def level(self):                      # backwards compatible
        return self.attested_level()

    def evidence_tally(self):
        attested = [r for r, c in EVIDENCE_CLASS.items() if c == "attested"]
        cited = sum(1 for r in attested if self.ev.get(r, (False,))[0] is True)
        return cited, len(attested)


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
                    help="require exactly this ATTESTED level; exit 1 otherwise")
    ap.add_argument("--expect-structural", type=int, choices=[0, 1, 2, 3, 4, 5],
                    help="require exactly this STRUCTURAL level; exit 1 otherwise")
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
        check_l3i(recs, ad, res)        # qualifier; not in LEVEL_REQS
        check_l4(recs, ad, res)
        check_l5(recs, ad, res, LEVEL_REQS)
    except LogError as e:
        res.fail("VLC-L1-1", f"delivered set unreadable: {e}")
    res.attach_evidence(ad)
    lv = res.attested_level()
    slv = res.structural_level()
    cited, n_attested = res.evidence_tally()

    if tmp:
        os.unlink(tmp)

    if a.json:
        print(json.dumps({
            "spec": VERSION, "adapter": ad["name"], "log": a.log,
            "mutation": a.mutate,
            "level_demonstrated": lv,            # attested; kept for compatibility
            "structural_level": slv,
            "attested_level": lv,
            "attested_requirements_with_evidence": cited,
            "attested_requirements_total": n_attested,
            "head": head,
            "requirements": {
                k: {"status": v[0], "note": v[1],
                    "class": EVIDENCE_CLASS.get(k, "?"),
                    "evidence": (res.ev.get(k, (None, ""))[1] or None)}
                for k, v in sorted(res.r.items())},
        }, indent=2))
    else:
        print(f"{VERSION} — conformance report")
        print(f"  log      : {a.log}" + (f"  [mutated: {a.mutate}]" if a.mutate else ""))
        print(f"  adapter  : {ad['name']} — {ad.get('description','')}")
        print(f"  producer : {ad.get('producer','(unstated)')}")
        print()
        print("  [S] structural — recomputed from the delivered evidence")
        print("  [A] attested   — asserted by the producer through the adapter")
        print("  [A+]           — attested AND carrying a reproducible evidence artefact")
        print()
        for n in (1, 2, 3, 4, 5):
            for rid in LEVEL_REQS[n]:
                st, note = res.r.get(rid, (FAIL, "not evaluated"))
                cls = EVIDENCE_CLASS.get(rid, "?")
                if cls == "structural":
                    tag = "[S] "
                else:
                    tag = "[A+]" if res.ev.get(rid, (False,))[0] is True else "[A] "
                mark = "  ok  " if st == PASS else "  FAIL"
                ev = res.ev.get(rid, (None, ""))[1]
                if ev and res.ev.get(rid, (False,))[0] is True:
                    note = (note + "  |  " + ev) if note else ev
                print(f"{mark} {tag} {rid:<12} {note}")
            print()
        print(f"  LEVEL DEMONSTRATED")
        print(f"    structural : L{slv}   recomputed from the log alone; a more generous")
        print(f"                        adapter cannot raise this number")
        print(f"    attested   : L{lv}   the above, plus what the producer asserts")
        print(f"                        {cited} of {n_attested} attested requirements carry a "
              f"reproducible evidence artefact")
        if slv < 5:
            nxt = [r for r in LEVEL_REQS[slv + 1] if EVIDENCE_CLASS.get(r) == "structural"]
            bad = [r for r in nxt if res.r.get(r, (FAIL, ""))[0] != PASS]
            if bad:
                print(f"    structural blocked from L{slv+1} by: {', '.join(bad)}")
            elif slv == 4:
                print(f"    structural cannot exceed L4: independence is a fact about who")
                print(f"    holds the pen, not a property of the bytes")
        if lv < 5:
            nxt = LEVEL_REQS[lv + 1]
            bad = [r for r in nxt if res.r.get(r, (FAIL, ""))[0] != PASS]
            print(f"    attested blocked from L{lv+1} by: {', '.join(bad)}")

    rc = 0
    if a.expect is not None and lv != a.expect:
        print(f"\nEXPECTED attested L{a.expect}, DEMONSTRATED L{lv}", file=sys.stderr)
        rc = 1
    if a.expect_structural is not None and slv != a.expect_structural:
        print(f"\nEXPECTED structural L{a.expect_structural}, DEMONSTRATED L{slv}",
              file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())

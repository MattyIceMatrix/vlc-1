#!/usr/bin/env python3
"""
VLC-1 conformance checker -- vendor-neutral.

    ./conformance.py --log <file> --adapter <adapter.json> [--json]
                     [--expect N] [--expect-structural N]
                     [--expect-root HEX] [--expect-head HEX] [--mutate M]

Reads ANY log, in any field naming, given a small declarative adapter that maps
the producer's field names onto the abstract quantities of VLC-1 clauses 4-7.
Reports the level ACTUALLY DEMONSTRATED and the exact requirement IDs that
failed.  It never reports the level a producer claims.

Design constraints, from SPEC.md Annex C:
  * adapters are DATA, not code -- no adapter may execute anything;
  * no requirement check is hard-coded to one vendor's mechanism;
  * every level must be reachable by an application-layer producer.

Programmatic use (standard library only, no global state):

    from conformance import check, AdapterError, UsageError
    report = check("log.jsonl", "adapters/x.json", expect_head=None)
    report["structural_level"], report["attested_level"]

check() returns exactly the object --json prints. A log that is empty, not
UTF-8, not JSON or otherwise not a log is a VERDICT (L0, reason under
VLC-L1-1), not an error.

Exit codes (EXT-023):
  0  the run completed and a report was printed (whatever level it shows),
     and every --expect / --expect-structural given was met;
  1  the run completed but a level given with --expect or
     --expect-structural was not the level demonstrated;
  2  no verdict was possible: a usage error (bad arguments, a log file that
     cannot be opened, an anchor that is not 64 hex characters, an unknown
     mutation) or an adapter error (unreadable, not JSON, or malformed).
     With --json, stdout carries {"error": "usage"|"adapter", "message": ...}.
"""
import argparse, hashlib, json, os, re, shutil, sys, tempfile

VERSION = "VLC-1 1.4.1-draft"

PASS, FAIL, NA = "PASS", "FAIL", "n/a"


class LogError(Exception):
    """The delivered set is not readable as a log. Not an adapter fault, and
    not a crash: it is exactly what a verifier should report as L0."""


class AdapterError(ValueError):
    """The adapter is unreadable or malformed. No verdict is possible: the
    checker does not know how to read the log. Exit status 2 (EXT-023)."""


class UsageError(ValueError):
    """A request the checker cannot act on: a missing log file, an anchor that
    is not 64 hex characters, an unknown mutation. Exit status 2 (EXT-023)."""


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
    """Read the delivered set. Raises UsageError when the file cannot be read at
    all (no verdict is possible) and LogError when it can be read but is not a
    log (the verdict is L0, with the reason)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise UsageError(f"log not readable: {path}: {e.strerror or e}")
    # EXT-024. Decoded with errors="replace", every undecodable byte sequence
    # became U+FFFD before hashing, so two logs differing only in which invalid
    # bytes they carried hashed identically under the canonical-JSON mechanisms.
    # An undecodable line is not a record; the delivered set is unreadable.
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        line = data.count(b"\n", 0, e.start) + 1
        raise LogError(f"line {line} is not valid UTF-8 (byte offset {e.start}); "
                       f"an undecodable record cannot be hashed as delivered")
    # universal newlines, as text-mode open() gave the checker before
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        raise LogError("the delivered set is empty: no record to verify")
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
        h = dig(o, hf)
        # a hash that is not a string is no binding; it used to reach re.escape
        # and dict keys and crash the checker (EXT-023)
        out.append(Rec(i, l, o, str(dig(o, cf)) if cf else "?", h if isinstance(h, str) else None))
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
    raise AdapterError(f"unknown integrity.root.kind {k!r}")


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
    if mech == "sha256-canonical-fields":
        # The hash covers exactly the adapter's declared hash_fields, the predecessor link
        # included, as one canonical object: sha256(canon({f: rec[f] for f in hash_fields})).
        # An absent optional field is OMITTED from the object, never serialized as null
        # (a present-as-null member is refused in check_l1 before this runs). For
        # ASCII-only names and values canon() equals RFC 8785 JCS.
        body = {f: r.obj[f] for f in ad["integrity"]["hash_fields"] if f in r.obj}
        return sha256_hex(canon(body).encode())
    raise AdapterError(f"unknown integrity.mechanism {mech!r}")


def _read_fields(ad):
    """Every record field some requirement reads, as (adapter path, field name): keys
    ending in _field or named field (a string), and fields / *_fields (a list). The
    integrity hash_field is the output of the binding, not an input, so it is excluded.
    integrity.end_marker.head_field is excluded too: VLC-L1-3 compares its value with the head recomputed from
    the chain, so a changed head already fails there, whether or not the end marker is self-bound. Other
    end-marker fields (the loss-accounting counts) have no such comparison and stay in the read set."""
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if p in ("integrity.hash_field", "integrity.end_marker.head_field"):
                    continue
                if (k == "field" or k.endswith("_field")) and isinstance(v, str):
                    out.append((p, v))
                elif (k == "fields" or k.endswith("_fields")) and isinstance(v, list) \
                        and p != "integrity.hash_fields":
                    out.extend((p, x) for x in v if isinstance(x, str))
                else:
                    walk(v, p)
    walk(ad, "")
    return out


def check_canonical_fields_adapter(recs, ad):
    """sha256-canonical-fields preconditions. Returns a failure note or None.
    (1) hash_fields is a non-empty list of ASCII names; (2) the prev link field is one of
    them and the hash field is not; (3) every field a later requirement reads is covered --
    a field the checker relies on but the hash does not cover is unanchored, and the
    binding would verify while it changed; (4) no record carries a hash field as null."""
    integ = ad["integrity"]
    hfs = integ.get("hash_fields")
    if not (isinstance(hfs, list) and hfs and all(isinstance(f, str) and f for f in hfs)):
        return "hash_fields must be a non-empty list of field names"
    bad = [f for f in hfs if not f.isascii()]
    if bad:
        return f"hash_fields names must be ASCII-only: {bad!r}"
    if len(set(hfs)) != len(hfs):
        return "hash_fields lists a name twice"
    pf, hf = integ.get("prev_field"), integ.get("hash_field")
    if not pf or pf not in hfs:
        return "prev_field must be declared and listed in hash_fields (the link is part of the hashed object)"
    if hf in hfs:
        return f"hash_field {hf!r} cannot be an input to its own hash"
    unanchored = sorted({(p, f) for p, f in _read_fields(ad) if f.split(".")[0] not in hfs})
    if unanchored:
        return ("fields read by later requirements are not covered by hash_fields (unanchored): " +
                ", ".join(f"{f} (via {p})" for p, f in unanchored))
    for r in recs:
        nul = [f for f in hfs if f in r.obj and r.obj[f] is None]
        if nul:
            return (f"record {r.i} serializes {nul} as null; an absent optional field must be "
                    "omitted, and null is a different hashed object")
    return None


# Annex J -- interval coverage (Corrigendum 1, EXT-002). Kept in its own
# module so the scoring logic is testable standalone. It is exercised by
# examples/l3i_cases.py and selftest.sh section 14; an earlier version of this
# comment named a test_check_l3i.py that never existed, which is part of how
# EXT-018 survived -- the level looked tested because a comment said so.
# Reported as a QUALIFIER, not a rung: LEVEL_REQS is keyed by integers and the
# level arithmetic indexes it numerically, so a "3i" key would break it.
try:
    from check_l3i import check_l3i
except ImportError:                                    # pragma: no cover
    def check_l3i(recs, ad, res):                      # noqa: D103
        return None


class Ctx:
    """Per-run state shared between the level checks. Replaces the module-level
    EXPECT dict, so the checker can be imported and called more than once in
    one process without one call's anchors leaking into the next.

    expect_root / expect_head: values the verifier obtained independently of
    the log (EXT-008), from --expect-root / --expect-head or check().
    end_bound: set by check_l1. True only when the end marker's own binding was
    recomputed and verified, so the values L2 reads from it are anchored."""

    def __init__(self, expect_root=None, expect_head=None):
        self.expect_root = expect_root.lower() if expect_root else None
        self.expect_head = expect_head.lower() if expect_head else None
        self.end_bound = False


def check_l1(recs, ad, res, ctx):
    mech = ad["integrity"]["mechanism"]
    if mech == "none":
        res.fail("VLC-L1-1", "adapter declares no integrity binding")
        res.fail("VLC-L1-2", "no mechanism to recompute")
        res.fail("VLC-L1-3", "no end marker binding")
        return None

    if mech == "sha256-canonical-fields":
        why = check_canonical_fields_adapter(recs, ad)
        if why:
            res.fail("VLC-L1-1", why)
            return None

    prev = chain_root(recs, ad)
    if prev is None:
        res.fail("VLC-L1-1", "chain root not derivable from the delivered set")
        return None

    if ctx.expect_root and prev.hex() != ctx.expect_root:
        res.fail("VLC-L1-1", f"chain root {prev.hex()[:16]}... does not equal the independently "
                             f"supplied root {ctx.expect_root[:16]}...: the log was re-rooted or is a different log")
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
    link_field = ad["integrity"].get("prev_field") if mech in ("sha256-prev-field", "sha256-canonical-fields") else None
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
        head_ok = claimed is not None and str(claimed) == prev.hex()
        # EXT-022. The head comparison alone does not detect truncation when the
        # end marker is not itself bound by the chain. The marker names the head
        # of whatever precedes it, so an editor who drops the last k records and
        # copies the new last record's hash into the marker -- no hash computed
        # -- passes the comparison. The marker counts as bound only when its own
        # binding is recomputed here and verifies.
        end_bound = False
        if em.get("self_bound", True):
            if link_field is not None and str(dig(end.obj, link_field) or "") != prev.hex():
                res.fail("VLC-L1-1", "end marker does not link to its predecessor")
                return None
            h = rec_hash(prev, end, ad, prev_raw) if end.hash else None
            if h is not None and h != end.hash:
                res.fail("VLC-L1-1", "end marker binding broken")
                return None
            if h:
                end_bound = True
                prev = bytes.fromhex(h)
        ctx.end_bound = end_bound
        if claimed is None:
            res.fail("VLC-L1-3", "end marker carries no head value")
        elif not head_ok:
            res.fail("VLC-L1-3", "end marker head does not match the recomputed binding")
        elif end_bound:
            res.ok("VLC-L1-3", "end marker is bound by the chain and names the recomputed head")
        elif ctx.expect_head:
            # the final head is compared with the independent value below; a
            # mismatch there fails VLC-L1-1 and the level with it
            res.ok("VLC-L1-3", "end marker is not bound by the chain; the tail is anchored "
                               "by the head supplied independently of the log")
        else:
            why = ("the adapter declares it not self-bound" if not em.get("self_bound", True)
                   else "it carries no recomputable binding of its own")
            res.fail("VLC-L1-3", f"not established: the end marker names the recomputed head, but "
                                 f"{why}, so records dropped from the tail with the marker's head "
                                 f"rewritten are undetectable on the log alone; supply --expect-head "
                                 f"(a head obtained independently of the log)")
    elif not em:
        res.fail("VLC-L1-3", "adapter declares no end marker: truncation undetectable")
    # else: the adapter declares one and the log lost it; that was already reported above
    # with the record it found instead, and must not be overwritten by a claim about the adapter.

    # EXT-008. On the log alone this establishes that the chain is internally
    # consistent from the root the log states. It does not establish resistance
    # to a complete rewrite: anyone who can recompute the binding can alter a
    # record and re-derive every later link and the end marker. That needs a
    # root or head the verifier obtained independently of the log (VLC-L1-1's
    # "published root"), and the report says so rather than implying more.
    if ctx.expect_head and prev.hex() != ctx.expect_head:
        res.fail("VLC-L1-1", f"final head {prev.hex()[:16]}... does not equal the independently "
                             f"supplied head {ctx.expect_head[:16]}...")
        return None
    anchored = [k for k, v in (("root", ctx.expect_root), ("head", ctx.expect_head)) if v]
    if anchored:
        res.ok("VLC-L1-1", "chain consistent AND its " + " and ".join(anchored) +
                           " equal the value(s) supplied independently of the log")
    else:
        res.ok("VLC-L1-1", "chain consistent from the root the log states; a complete "
                           "rewrite is detectable only against an independently held root or head "
                           "(--expect-root / --expect-head)")

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
def check_l2(recs, ad, res, ctx):
    lo = ad.get("loss")
    if not lo or lo.get("mode") == "none":
        res.fail("VLC-L2-1", "adapter declares no production count or ordinal")
        res.fail("VLC-L2-5", "no completeness identity is computable")
        return None
    mode = lo.get("mode", "declaration")
    if ad["integrity"]["mechanism"] == "none":
        # stated before the produced count is read, so an unbound count below
        # cannot leave this unreported
        res.fail("VLC-L2-3", "no integrity binding, so declarations are removable")

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
    # EXT-022. The produced count is the producer's independent figure, and the
    # identity is only as good as that figure's anchoring. Read from an end
    # marker the chain does not bind, it can be lowered after the fact to hide
    # exactly the records the identity exists to count. So a count read from
    # the end marker is established only when check_l1 verified the marker's
    # own binding. An independently supplied head (--expect-head) anchors the
    # chain, not the marker's other fields, and does not change this.
    # EXT-023. A count must be a JSON integer. int() used to accept "40" and
    # turn 3.7 into 3, and raised on "forty", crashing the checker.
    p = lo.get("produced", {})
    kind = p.get("kind")
    produced = None
    em = ad["integrity"].get("end_marker") or {}
    last = recs[-1]
    at_end = last.cls == em.get("class") if em else False
    unbound_end = ("the end marker is not bound by the chain, so a count read from it "
                   "can be rewritten to hide a drop; the produced count is not established")
    bad = []

    def count(v, where):
        if type(v) is int and v >= 0:
            return v
        bad.append(f"{where} is {v!r}, not a non-negative JSON integer")
        return None

    if kind == "field_of_end_marker":
        if at_end:
            if not ctx.end_bound:
                res.fail("VLC-L2-1", unbound_end)
                return None
            v = dig(last.obj, p["field"])
            produced = count(v, f"end marker {p['field']!r}") if v is not None else None
    elif kind == "max_ordinal":
        # EXT-014. The high-water mark is a quantity the PRODUCER declares, as
        # VLC-L2-5 says. It was computed as max - min + 1 over the ordinals that
        # happened to arrive, so losing records at either end of the sequence
        # moved both bounds with them and the identity still closed. Now the
        # end marker must carry the producer's final ordinal, and the adapter
        # must state where the sequence starts; neither is inferred.
        hwf, start = p.get("high_water_field"), p.get("start")
        if hwf is None or type(start) is not int:
            res.fail("VLC-L2-1", "max_ordinal needs produced.high_water_field (on the end "
                                 "marker) and an integer produced.start; the bounds of the "
                                 "sequence are not inferred from what arrived")
            return None
        if at_end:
            if not ctx.end_bound:
                res.fail("VLC-L2-1", unbound_end)
                return None
            hw = dig(last.obj, hwf)
            if hw is not None and type(hw) is not int:
                bad.append(f"end marker {hwf!r} is {hw!r}, not a JSON integer")
            produced = hw - start + 1 if type(hw) is int and hw >= start - 1 else None
    elif kind == "sum_of_end_marker_fields":
        if at_end:
            if not ctx.end_bound:
                res.fail("VLC-L2-1", unbound_end)
                return None
            vs = [dig(last.obj, f) for f in p["fields"]]
            if all(v is not None for v in vs):
                cs = [count(v, f"end marker {f!r}") for f, v in zip(p["fields"], vs)]
                if all(c is not None for c in cs):
                    produced = sum(cs)
    elif kind == "field_of_any":
        for r in reversed(recs):
            v = dig(r.obj, p["field"])
            if v is not None:
                if r is last and at_end and not ctx.end_bound:
                    res.fail("VLC-L2-1", unbound_end)
                    return None
                produced = count(v, f"record {r.i} {p['field']!r}")
                break
    else:
        raise AdapterError(f"unknown loss.produced.kind {kind!r}")

    if bad:
        # a malformed count is reported and the declarations are still read,
        # so each defect is named where it lies; the identity is not computable
        res.fail("VLC-L2-1", "; ".join(bad))
        produced = None
    if produced is None and not bad:
        res.fail("VLC-L2-1", "produced count not derivable from the delivered set")
        return None
    if produced is not None:
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
        raise AdapterError(f"unknown loss.mode {mode!r}")

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
    if produced is None:
        res.fail("VLC-L2-5", "no well-formed produced count: the identity is not computable")
        res.fail("VLC-L2-6", "completeness not established")
    elif lhs == produced:
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
def _roles(ad):
    """Record classes the adapter gives a role other than coverage declaration."""
    em = ad["integrity"].get("end_marker") or {}
    iv = ad.get("interval") or {}
    named = [em.get("class"), (ad.get("loss") or {}).get("declaration_class"),
             (ad.get("policy") or {}).get("change_class"),
             iv.get("declaration_class"), iv.get("tick_class")]
    out = {c: "a declared role" for c in ad.get("marker_classes", [])}
    for c, what in zip(named, ("the end marker", "the loss declaration", "the policy change record",
                               "the interval declaration", "the interval tick")):
        if c is not None:
            out[c] = what
    return out


def check_l3(recs, ad, res):
    cv = ad.get("coverage")
    if not cv or cv.get("mode") == "none":
        res.fail("VLC-L3-1a", "adapter declares no coverage declaration")
        res.fail("VLC-L3-6", "observation surface is not enumerable and is not declared as such")
        return None
    if cv.get("mode") == "non_enumerable":
        # EXT-025. This used to PASS VLC-L3-6, a structural requirement, on the
        # adapter's word alone. The declaration is honest and is relayed as
        # such; it demonstrates nothing from the log, and L3 is not claimable
        # either way.
        res.fail("VLC-L3-1a", "observation surface declared non-enumerable")
        res.fail("VLC-L3-6", "declared non-enumerable (the producer's statement, relayed): "
                             "honest, and L3 correctly not claimable; nothing enumerated in the log")
        return None
    if cv.get("mode") != "enumerated":
        raise AdapterError(f"unknown coverage.mode {cv.get('mode')!r}")

    dc = cv.get("declaration_class")
    decls = [r for r in recs if r.cls == dc]
    if not decls:
        res.fail("VLC-L3-1a", f"no {dc!r} record in the delivered set: silence about a "
                             f"source is indistinguishable from absence of the source")
        res.fail("VLC-L3-6", "no enumeration of the observation surface in the log")
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
    # EXT-025. Which record is the coverage declaration is the adapter's
    # mapping, and a mapping could relabel a record that exists for another
    # purpose -- the epoch record, say -- and its fields as the three categories.
    # That raised a log with no coverage declaration to structural L3 with the
    # log unchanged. What the log can refute is checked: the declaration is a
    # record of its own (no class the adapter maps to another role, not the
    # record the chain root is derived from), its three categories are three
    # different fields, and no source is named in two categories. A relabelled
    # record whose class no other role claims is indistinguishable from a
    # genuine declaration in the bytes; that residual is disclosed in EXT-025
    # and the report carries adapter_sha256 so the mapping is pinned.
    roles = _roles(ad)
    if dc in roles:
        malformed.append(f"class {dc!r} is also {roles[dc]}: a coverage declaration is a "
                         f"record of its own, not another record relabelled")
    root = ad["integrity"].get("root", {})
    if root.get("kind") == "field_of_first_record" and decls[0].i == 0:
        malformed.append("the chain root is derived from the coverage declaration's record: "
                         "a coverage declaration is a record of its own")
    cats = [cv.get(k) for k in ("attached_field", "unattached_field", "by_design_field")]
    if None in cats or len(set(cats)) != 3:
        malformed.append(f"the three coverage categories must be three different fields, got {cats!r}")
    for d in decls:
        for key in ("attached_field", "unattached_field", "by_design_field"):
            fld = cv.get(key)
            if fld and dig(d.obj, fld) is None:
                malformed.append(f"record {d.i} omits {fld!r}")
        if not as_list(dig(d.obj, cv.get("attached_field"))):
            malformed.append(f"record {d.i} names no attached sources")
        seen = {}
        for c in cats:
            for s in as_list(dig(d.obj, c)) if c else []:
                if s in seen and seen[s] != c:
                    malformed.append(f"record {d.i} names {s!r} under both {seen[s]!r} and {c!r}")
                seen.setdefault(s, c)
    no_basis = [d.i for d in decls
                if cv.get("basis_field") and not dig(d.obj, cv.get("basis_field"))]
    if cv.get("basis_field") is None:
        basis = None

    if malformed:
        res.fail("VLC-L3-1a", "; ".join(malformed[:3]) +
                 (f" (+{len(malformed) - 3} more)" if len(malformed) > 3 else ""))
        res.fail("VLC-L3-6", "no well-formed enumeration of the observation surface in the log")
    else:
        # L3-1a: the declaration is present and well-formed — recomputed.
        # L3-1b: it describes the surface actually observed — relayed. A
        # verifier reading the log cannot check the second, and saying it can
        # is the defect EXT-001 reported.
        res.ok("VLC-L3-1b", "declared surface accepted as stated by the "
                            "producer; not recomputable from the log")
        res.ok("VLC-L3-1a", f"{len(att)} attached, {len(una)} unattached-here, "
                           f"{len(des)} excluded by design")
        # EXT-025: recomputed from the log, not from the adapter's mode
        res.ok("VLC-L3-6", "surface enumerated in the log, in a well-formed declaration")
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

    # EXT-025. Attested: this reads only the adapter's list of non-event
    # classes. The structural consequence -- an identity inflated by counting
    # declarations -- is already decided from the log at VLC-L2-5.
    if dc in non_event:
        res.ok("VLC-L3-5", "the adapter excludes coverage declarations from the event count")
    else:
        res.fail("VLC-L3-5", "coverage declarations are counted as events: identity inflated")

    return {"attached": att, "unattached": una, "by_design": des}


# ===========================================================================
# LEVEL 4 -- policy binding
# ===========================================================================
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def check_l4(recs, ad, res):
    po = ad.get("policy")
    if not po or po.get("mode") == "none":
        res.fail("VLC-L4-1", "adapter declares no policy binding")
        return None
    if po.get("mode") == "observation_only":
        # EXT-025: this was a structural PASS on the adapter's word. The log
        # records no verdicts, so there is nothing to bind and L4 is not
        # claimable; L3 is the terminal level, which the producer declares.
        res.fail("VLC-L4-1", "log records no verdicts (the producer's statement, relayed); "
                             "L3 is the terminal level and L4 is not claimable")
        return {"terminal": 3}

    mode = po.get("mode")
    df = po.get("digest_field")
    integ = ad["integrity"]
    ne = set(ad.get("non_event_classes", []))
    events = [r for r in recs if r.cls not in ne]
    if not df:
        raise AdapterError("policy.digest_field is required for policy.mode " + repr(mode))
    # EXT-025. The chain's own output is not a policy digest. Pointing
    # digest_field at the hash field satisfied "every event carries a digest"
    # on any chained log.
    if df in (integ.get("hash_field"), integ.get("prev_field")):
        res.fail("VLC-L4-1", f"digest_field {df!r} is the integrity binding's own field, "
                             f"not a digest of a policy")
        initial = None
    elif mode == "chain_root":
        # EXT-025. This compared two adapter settings and never read the log.
        # Now: the root record carries a well-formed digest, and the root the
        # chain was verified from is derived from that digest.
        r = integ.get("root", {})
        v = dig(recs[0].obj, df)
        initial = v if isinstance(v, str) else None
        if r.get("kind") != "field_of_first_record" or r.get("field") != df:
            res.fail("VLC-L4-1", "policy digest does not root the binding")
        elif not (isinstance(v, str) and HEX64.match(v)):
            res.fail("VLC-L4-1", f"the root record's {df!r} is {v!r}, not a digest "
                                 f"(64 lowercase hex characters)")
        else:
            try:
                derived = chain_root(recs, ad)
            except LogError:
                derived = None
            if derived is None or recs[0].hash != derived.hex():
                res.fail("VLC-L4-1", "the root record does not commit to the root derived "
                                     "from its policy digest")
            else:
                res.ok("VLC-L4-1", "the root record's policy digest roots the binding: "
                                   "re-rooting is detectable")
    elif mode == "per_record":
        # EXT-006. Counted digests across ALL records and compared the total
        # to the number of events, so a non-event carrying a digest could stand
        # in for an event missing one. Each event is now checked on its own.
        # EXT-025: and a digest is a digest -- a constant string such as a
        # model name on every event satisfied "carries the digest"
        missing = [r.i for r in events
                   if not (isinstance(dig(r.obj, df), str) and HEX64.match(dig(r.obj, df)))]
        v0 = dig(events[0].obj, df) if events else None
        initial = v0 if isinstance(v0, str) else None
        if not missing:
            res.ok("VLC-L4-1", "every event record carries the policy digest")
        else:
            res.fail("VLC-L4-1", f"{len(missing)} event record(s) carry no policy digest "
                                 f"(64 lowercase hex characters), first at record {missing[0]}")
    else:
        raise AdapterError(f"unknown policy.mode {mode!r}")

    cc = po.get("change_class")
    changes = [r for r in recs if cc and r.cls == cc]
    # EXT-006. VLC-L4-2 requires each change record to carry the digests
    # before and after. Only the record's existence was checked.
    bf, af = po.get("change_before_field", "before"), po.get("change_after_field", "after")
    incomplete = [r.i for r in changes
                  if not isinstance(dig(r.obj, bf), str) or not dig(r.obj, bf)
                  or not isinstance(dig(r.obj, af), str) or not dig(r.obj, af)]
    # EXT-025. The digests must also form one history, recomputed from the log:
    # each change starts from the digest in force, and under per_record every
    # event carries the digest in force at its position. A field that differs
    # from record to record -- a hash, a timestamp -- is not a policy digest.
    broken = []
    if not incomplete and initial is not None:
        cur = initial
        for r in recs:
            if r.cls == cc:
                if dig(r.obj, bf) != cur:
                    broken.append(f"change at record {r.i} starts from {str(dig(r.obj, bf))[:12]!r}, "
                                  f"not the digest in force {cur[:12]!r}")
                cur = dig(r.obj, af)
            elif mode == "per_record" and r.cls not in ne:
                v = dig(r.obj, df)
                if isinstance(v, str) and v != cur:
                    broken.append(f"event at record {r.i} carries {v[:12]!r}, not the digest in "
                                  f"force {cur[:12]!r}, with no policy change record between")
    if cc is None:
        res.fail("VLC-L4-2", "adapter names no policy-change record class")
    elif incomplete:
        res.fail("VLC-L4-2", f"policy change record(s) {incomplete} do not carry both the "
                             f"{bf!r} and {af!r} digests")
    elif broken:
        res.fail("VLC-L4-2", "; ".join(broken[:2]) + (f" (+{len(broken) - 2} more)" if len(broken) > 2 else ""))
        if mode == "per_record":
            res.fail("VLC-L4-1", "the per-record digests do not form one policy history (see VLC-L4-2)")
    else:
        res.ok("VLC-L4-2", f"{len(changes)} in-log policy change(s), digests consistent")

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

    # VLC-L5-6 (1.4-draft, closes EXT-004's open question): the ATTESTED half of
    # a witness's standing. EXT-004 made VLC-L5-4 structural-only, correctly --
    # a structural verdict must not move with adapter text. That left nothing
    # speaking for the witness's exhaustiveness basis (VLC-L3-1d, attested).
    # A witness with structural L3 and no stated basis for its coverage being
    # exhaustive passed VLC-L5-4 and qualified in witness/reconcile.py, so it
    # could corroborate an ABSENCE -- vouch that nothing happened outside what
    # it saw -- on a coverage claim nobody had grounded. It may corroborate
    # what it observed; it may not stand for an absence.
    if res.r.get("VLC-L3-1d", (FAIL, ""))[0] == PASS:
        res.ok("VLC-L5-6", "the witness states the basis on which its coverage is "
                           "exhaustive (attested: the basis is relayed, not recomputed)")
    else:
        res.fail("VLC-L5-6", "the witness gives no basis for its coverage being "
                             "exhaustive: it can corroborate what it observed, not "
                             "that it observed everything")
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
    # EXT-025: VLC-L3-5 reads only the adapter's non-event list; attested.
    "VLC-L3-4": "attested",   "VLC-L3-5": "attested",
    "VLC-L3-6": "structural",
    "VLC-L4-1": "structural", "VLC-L4-2": "structural",
    "VLC-L4-3": "attested",   "VLC-L4-4": "attested",
    "VLC-L5-1": "attested",   "VLC-L5-2": "attested",
    "VLC-L5-3": "attested",   "VLC-L5-4": "structural",
    "VLC-L5-5": "attested",   "VLC-L5-6": "attested",
}

LEVEL_REQS = {
    1: ["VLC-L1-1", "VLC-L1-2", "VLC-L1-3", "VLC-L1-4"],
    2: ["VLC-L2-1", "VLC-L2-2", "VLC-L2-3", "VLC-L2-4", "VLC-L2-5", "VLC-L2-6"],
    3: ["VLC-L3-1a", "VLC-L3-1b", "VLC-L3-1d", "VLC-L3-2", "VLC-L3-3",
        "VLC-L3-4", "VLC-L3-5", "VLC-L3-6"],
    4: ["VLC-L4-1", "VLC-L4-2", "VLC-L4-3", "VLC-L4-4"],
    5: ["VLC-L5-1", "VLC-L5-2", "VLC-L5-3", "VLC-L5-4", "VLC-L5-5", "VLC-L5-6"],
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
    if not ls:
        raise UsageError("cannot apply a mutation to an empty log")
    if how == "flip-byte":
        i = len(ls) // 2
        s = ls[i]
        j = min(max(1, len(s) // 2), len(s) - 1)
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
            raise UsageError(f"adapter names no {key} declaration class to remove")
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
            raise UsageError("no policy digest in the root record to re-base")
    else:
        raise UsageError(f"unknown mutation {how!r}")
    return ls


# ===========================================================================
# adapter validation -- a malformed adapter is an error, not a verdict
# ===========================================================================
MECHANISMS = ("none", "sha256-chain-prefix", "sha256-chain-canonical", "sha256-prev-raw",
              "sha256-prev-field", "sha256-canonical-fields")
ROOT_KINDS = ("zero", "constant", "field_of_first_record")
LOSS_MODES = ("none", "declaration", "ordinal")
PRODUCED_KINDS = ("field_of_end_marker", "max_ordinal", "sum_of_end_marker_fields", "field_of_any")
COVERAGE_MODES = ("none", "non_enumerable", "enumerated")
POLICY_MODES = ("none", "observation_only", "chain_root", "per_record")


def load_adapter(path):
    """Read and validate an adapter. Returns (adapter dict, sha256 of its bytes).
    Raises AdapterError for anything the checker could not act on (EXT-023):
    it used to crash with a traceback, or exit 1 -- the status that means an
    expectation was not met."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise AdapterError(f"adapter not readable: {path}: {e.strerror or e}")
    try:
        ad = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise AdapterError(f"adapter is not valid JSON: {path}: {e}")
    validate_adapter(ad)
    return ad, hashlib.sha256(raw).hexdigest()


def validate_adapter(ad):
    def need(cond, msg):
        if not cond:
            raise AdapterError(msg)

    def obj(v):
        return v is None or isinstance(v, dict)

    need(isinstance(ad, dict), "adapter is not a JSON object")
    need(isinstance(ad.get("name"), str), "adapter missing required key 'name' (a string)")
    integ = ad.get("integrity")
    need(isinstance(integ, dict), "adapter missing required key 'integrity' (an object)")
    need(integ.get("mechanism") in MECHANISMS,
         f"unknown integrity.mechanism {integ.get('mechanism')!r}; one of {MECHANISMS}")
    for k in ("record_class_field",):
        need(ad.get(k) is None or isinstance(ad.get(k), str), f"{k} must be a string")
    for k in ("marker_classes", "non_event_classes"):
        v = ad.get(k, [])
        need(isinstance(v, list) and all(isinstance(x, str) for x in v), f"{k} must be a list of strings")
    for k in ("loss", "coverage", "policy", "independence", "interval", "evidence"):
        need(obj(ad.get(k)), f"{k} must be an object")
    if integ["mechanism"] != "none":
        need(isinstance(integ.get("hash_field"), str), "integrity.hash_field (a string) is required")
        root = integ.get("root", {})
        need(isinstance(root, dict) and root.get("kind", "zero") in ROOT_KINDS,
             f"integrity.root.kind must be one of {ROOT_KINDS}")
        if root.get("kind") == "constant":
            v = root.get("value")
            need(isinstance(v, str) and HEX64.match(v.lower()), "integrity.root.value must be 64 hex characters")
        if root.get("kind") == "field_of_first_record":
            need(isinstance(root.get("field"), str), "integrity.root.field (a string) is required")
        if integ["mechanism"] in ("sha256-prev-field", "sha256-canonical-fields"):
            need(isinstance(integ.get("prev_field"), str), "integrity.prev_field (a string) is required")
        em = integ.get("end_marker")
        need(obj(em), "integrity.end_marker must be an object")
        if em:
            need(isinstance(em.get("class"), str), "integrity.end_marker.class (a string) is required")
            need(isinstance(em.get("self_bound", True), bool), "integrity.end_marker.self_bound must be true or false")
    lo = ad.get("loss") or {}
    if lo:
        need(lo.get("mode", "declaration") in LOSS_MODES, f"unknown loss.mode {lo.get('mode')!r}")
        if lo.get("mode", "declaration") != "none":
            p = lo.get("produced")
            need(isinstance(p, dict) and p.get("kind") in PRODUCED_KINDS,
                 f"loss.produced.kind must be one of {PRODUCED_KINDS}")
            if p["kind"] in ("field_of_end_marker", "field_of_any"):
                need(isinstance(p.get("field"), str), f"loss.produced.field is required for {p['kind']}")
            if p["kind"] == "sum_of_end_marker_fields":
                need(isinstance(p.get("fields"), list) and p["fields"]
                     and all(isinstance(x, str) for x in p["fields"]),
                     "loss.produced.fields must be a non-empty list of strings")
            iv = lo.get("interval_fields")
            need(iv is None or (isinstance(iv, list) and len(iv) == 2 and all(isinstance(x, str) for x in iv)),
                 "loss.interval_fields must be [from_field, to_field]")
    cv = ad.get("coverage") or {}
    if cv:
        need(cv.get("mode") in COVERAGE_MODES, f"unknown coverage.mode {cv.get('mode')!r}")
        if cv.get("mode") == "enumerated":
            need(isinstance(cv.get("declaration_class"), str), "coverage.declaration_class is required")
    po = ad.get("policy") or {}
    if po:
        need(po.get("mode") in POLICY_MODES, f"unknown policy.mode {po.get('mode')!r}")
        if po.get("mode") in ("chain_root", "per_record"):
            need(isinstance(po.get("digest_field"), str), "policy.digest_field is required")
            need(obj(po.get("replay")), "policy.replay must be an object")
    ind = ad.get("independence") or {}
    need(obj(ind.get("reconciliation")), "independence.reconciliation must be an object")


# ===========================================================================
# the programmatic entry point
# ===========================================================================
def _check(log_path, ad, adapter_sha256, expect_root=None, expect_head=None, mutation=None):
    for name, v in (("expect_root", expect_root), ("expect_head", expect_head)):
        if v is not None and not (isinstance(v, str) and HEX64.match(v.lower())):
            raise UsageError(f"{name} must be 64 hex characters")
    ctx = Ctx(expect_root, expect_head)
    path, tmpdir = log_path, None
    if mutation:
        try:
            with open(log_path, "rb") as f:
                text = f.read().decode("utf-8", errors="strict")
        except OSError as e:
            raise UsageError(f"log not readable: {log_path}: {e.strerror or e}")
        except UnicodeDecodeError:
            raise UsageError("cannot apply a mutation to a log that is not valid UTF-8")
        lines = [l for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
        lines = mutate(lines, mutation, ad)
        # written to a private temporary directory, never beside the log
        tmpdir = tempfile.mkdtemp(prefix="vlc1-mutated-")
        path = os.path.join(tmpdir, "log.jsonl")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")

    res = Results()
    head = None
    try:
        try:
            recs = load(path, ad)
            head = check_l1(recs, ad, res, ctx)
            check_l2(recs, ad, res, ctx)
            check_l3(recs, ad, res)
            check_l3i(recs, ad, res)        # qualifier; not in LEVEL_REQS
            check_l4(recs, ad, res)
            check_l5(recs, ad, res, LEVEL_REQS)
        except LogError as e:
            res.fail("VLC-L1-1", f"delivered set unreadable: {e}")
        except (KeyError, TypeError, AttributeError, IndexError) as e:
            # an adapter shape validate_adapter did not anticipate; a verdict
            # computed from a half-read adapter would be worse than none
            raise AdapterError(f"adapter could not be applied to this log "
                               f"({type(e).__name__}: {e})")
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
    res.attach_evidence(ad)
    lv = res.attested_level()
    slv = res.structural_level()
    cited, n_attested = res.evidence_tally()
    return {
        "spec": VERSION, "adapter": ad["name"], "adapter_sha256": adapter_sha256,
        "log": log_path, "mutation": mutation,
        "level_demonstrated": lv,            # attested; kept for compatibility
        "structural_level": slv,
        "attested_level": lv,
        "attested_requirements_with_evidence": cited,
        "attested_requirements_total": n_attested,
        "anchors": {"root": ctx.expect_root, "head": ctx.expect_head},
        "head": head,
        "requirements": {
            k: {"status": v[0], "note": v[1],
                "class": EVIDENCE_CLASS.get(k, "?"),
                "evidence": (res.ev.get(k, (None, ""))[1] or None),
                "evidence_cited": res.ev.get(k, (False,))[0] is True}
            for k, v in sorted(res.r.items())},
    }


def check(log_path, adapter_path, expect_root=None, expect_head=None):
    """Score one JSONL log against one adapter and return the report.

    The return value is exactly the object `conformance.py --json` prints:
    structural_level and attested_level (ints 0-5), level_demonstrated (the
    attested level, kept for compatibility), adapter_sha256 (the mapping the
    levels are relative to), anchors, head, and requirements -- a dict from
    requirement ID to {status: "PASS"|"FAIL", note, class:
    "structural"|"attested", evidence, evidence_cited}.

    expect_root / expect_head: 64-hex values obtained independently of the
    log. Without expect_head, a log whose end marker the chain does not bind
    cannot establish VLC-L1-3.

    A log that is empty, not UTF-8, not JSON or otherwise unreadable is a
    verdict, not an error: the report comes back at L0 with the reason under
    VLC-L1-1. Raises AdapterError (a ValueError) for an unreadable or malformed
    adapter, and UsageError (a ValueError) for a log file that cannot be opened
    or an anchor that is not 64 hex characters. Standard library only; no
    global state, so it may be called repeatedly in one process.
    """
    ad, digest = load_adapter(adapter_path)
    return _check(log_path, ad, digest, expect_root, expect_head)


def render_text(rep, ad):
    out = [f"{VERSION} — conformance report",
           f"  log      : {rep['log']}" + (f"  [mutated: {rep['mutation']}]" if rep["mutation"] else ""),
           f"  adapter  : {ad['name']} — {ad.get('description', '')}",
           f"  adapter sha256: {rep['adapter_sha256']}",
           f"  producer : {ad.get('producer', '(unstated)')}", "",
           "  [S] structural — recomputed from the delivered evidence",
           "  [A] attested   — asserted by the producer through the adapter",
           "  [A+]           — attested AND carrying a reproducible evidence artefact", ""]
    req = rep["requirements"]

    def st(rid):
        return req.get(rid, {}).get("status", FAIL)
    for n in (1, 2, 3, 4, 5):
        for rid in LEVEL_REQS[n]:
            r = req.get(rid, {"status": FAIL, "note": "not evaluated", "evidence": None,
                              "evidence_cited": False})
            cls = EVIDENCE_CLASS.get(rid, "?")
            tag = "[S] " if cls == "structural" else ("[A+]" if r.get("evidence_cited") else "[A] ")
            note = r["note"]
            if r.get("evidence") and r.get("evidence_cited"):
                note = (note + "  |  " + r["evidence"]) if note else r["evidence"]
            out.append(f"{'  ok  ' if r['status'] == PASS else '  FAIL'} {tag} {rid:<12} {note}")
        out.append("")
    slv, lv = rep["structural_level"], rep["attested_level"]
    out += ["  LEVEL DEMONSTRATED",
            f"    structural : L{slv}   recomputed from the log under this adapter's mapping;",
            f"                        no adapter assertion can raise this number",
            f"    attested   : L{lv}   the above, plus what the producer asserts",
            f"                        {rep['attested_requirements_with_evidence']} of "
            f"{rep['attested_requirements_total']} attested requirements carry a "
            f"reproducible evidence artefact"]
    if slv < 5:
        nxt = [r for r in LEVEL_REQS[slv + 1] if EVIDENCE_CLASS.get(r) == "structural"]
        bad = [r for r in nxt if st(r) != PASS]
        if bad:
            out.append(f"    structural blocked from L{slv+1} by: {', '.join(bad)}")
        elif slv == 4:
            out += ["    structural cannot exceed L4: independence is a fact about who",
                    "    holds the pen, not a property of the bytes"]
    if lv < 5:
        bad = [r for r in LEVEL_REQS[lv + 1] if st(r) != PASS]
        out.append(f"    attested blocked from L{lv+1} by: {', '.join(bad)}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"{VERSION} conformance checker")
    ap.add_argument("--log", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--expect", type=int, choices=[0, 1, 2, 3, 4, 5],
                    help="require exactly this ATTESTED level; exit 1 otherwise")
    ap.add_argument("--expect-structural", type=int, choices=[0, 1, 2, 3, 4, 5],
                    help="require exactly this STRUCTURAL level; exit 1 otherwise")
    ap.add_argument("--expect-root", help="hex chain root obtained independently of the log; "
                    "VLC-L1-1 fails if the log's derived root differs (detects a re-rooted, re-sealed log)")
    ap.add_argument("--expect-head", help="hex final head obtained independently of the log; "
                    "VLC-L1-1 fails if the recomputed head differs (detects a rewritten, re-sealed log); "
                    "also anchors the tail when the end marker is not bound by the chain (VLC-L1-3)")
    ap.add_argument("--mutate", help="apply an Annex A mutation before checking")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        ad, digest = load_adapter(a.adapter)
        rep = _check(a.log, ad, digest, a.expect_root, a.expect_head, a.mutate)
    except (AdapterError, UsageError) as e:
        kind = "adapter" if isinstance(e, AdapterError) else "usage"
        print(f"conformance.py: {kind} error: {e}", file=sys.stderr)
        if a.json:
            print(json.dumps({"spec": VERSION, "error": kind, "message": str(e)}, indent=2))
        return 2

    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(render_text(rep, ad))

    rc = 0
    if a.expect is not None and rep["attested_level"] != a.expect:
        print(f"\nEXPECTED attested L{a.expect}, DEMONSTRATED L{rep['attested_level']}", file=sys.stderr)
        rc = 1
    if a.expect_structural is not None and rep["structural_level"] != a.expect_structural:
        print(f"\nEXPECTED structural L{a.expect_structural}, DEMONSTRATED L{rep['structural_level']}",
              file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())

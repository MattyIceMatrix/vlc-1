#!/usr/bin/env python3
"""jidec_l2_verify.py: grade a JIDEC export that carries nenrin-head-checkpoint-v2 window declarations
(the L2 design settled in vlc-1 PR #12, 2026-11-28). Standard library only, no network. Written apart
from jidec_l2_synth.py, so the two do not share code (Ed25519 included).

  python3 -I jidec_l2_verify.py --export <export.jsonl> --operator-key <64 hex> [--refusals <folder>]
                                [--expect-marker <64 hex>]
  python3 -I jidec_l2_verify.py --selftest      (needs jidec_l2_synth.py beside it)

It writes one JSON line on stdout and, last on stderr, JIDEC_L2_VERIFY_OK L<level> or
JIDEC_L2_VERIFY_NG L<level> <first reason>. The levels are this tool's reading of VLC-1, not VLC-1's:
  L1  chain:   each entry_sha256 is sha256(canon({n, schema, claim_sha256, created_at, prev_entry_sha256})),
               each links to the one before (entry 1 to 64 zeros), n strictly increases; the last line is
               the jidec-head-v1 marker over the last entry (its n is the head's n) and its hash recomputes;
               with --expect-marker, the marker hash equals the one held from earlier
      binding: every entry carries record_canonical and sha256 of its UTF-8 is the entry's claim_sha256;
               the bytes are one JSON object with no repeated member name
  L2  keys:    a nenrin-key-statement-v1 record is signed by the pinned operator key and names a ledger key;
               a checkpoint is signed by a ledger key named in a statement written before it (one hop)
      windows: per nenrin-head-checkpoint-v2: integer counts; refused = the sum by class; written = the
               entries present with from <= n <= to; received = written + refused + lost; ledger_head.n = to,
               ledger_head.entry_sha256 = the hash of entry `to`, marker_sha256 = the marker for (to, that hash);
               the checkpoint's own n is past `to`
      tiling:  the windows start at 1 and each starts one after the last one's `to`, in the order written
      list:    with --refusals, a file in the folder hashes to refusals_sha256 and its lines count by class
               to refused_by_class
      tail:    the entries after the last window's `to` are contiguous (a gap there is a loss no one declared)
番人(個人) 2026-11-28.
"""
import hashlib
import json
import os
import sys

# ---------------------------------------------------------------- Ed25519 verification (RFC 8032 5.1.7)
_q = (1 << 255) - 19
_l = (1 << 252) + 27742317777372353535851937790883648493
_d = (-121665 * pow(121666, _q - 2, _q)) % _q


def _pt_add(a, b):
    (x1, y1), (x2, y2) = a, b
    t = _d * x1 * x2 * y1 * y2 % _q
    x3 = (x1 * y2 + x2 * y1) * pow(1 + t, _q - 2, _q) % _q
    y3 = (y1 * y2 + x1 * x2) * pow(1 - t, _q - 2, _q) % _q
    return (x3, y3)


def _pt_mul(k, pt):
    acc = (0, 1)
    for bit in bin(k)[2:]:
        acc = _pt_add(acc, acc)
        if bit == "1":
            acc = _pt_add(acc, pt)
    return acc


def _pt_from(b32):
    y = int.from_bytes(b32, "little")
    s, y = y >> 255, y & ((1 << 255) - 1)
    if y >= _q:
        return None
    u, v = (y * y - 1) % _q, (_d * y * y + 1) % _q
    x = (u * pow(v, 3, _q) * pow(u * pow(v, 7, _q), (_q - 5) // 8, _q)) % _q
    if (v * x * x - u) % _q:
        x = x * pow(2, (_q - 1) // 4, _q) % _q
        if (v * x * x - u) % _q:
            return None
    if x == 0 and s:
        return None
    if x % 2 != s:
        x = _q - x
    return (x, y)


_by = 4 * pow(5, _q - 2, _q) % _q
_B = _pt_from(_by.to_bytes(32, "little"))


def ed25519_ok(pub, msg, sig):
    if len(pub) != 32 or len(sig) != 64:
        return False
    a, r = _pt_from(pub), _pt_from(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if a is None or r is None or s >= _l:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(), "little") % _l
    return _pt_mul(s, _B) == _pt_add(r, _pt_mul(h, a))


# ---------------------------------------------------------------- reading
class Bad(Exception):
    pass


def _strict(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise Bad("a member name repeats: %r" % k)
        seen[k] = v
    return seen


def _nonfinite(tok):
    raise Bad("a non-finite number: %s" % tok)


def jload(text):
    return json.loads(text, object_pairs_hook=_strict, parse_constant=_nonfinite)


def h256(b):
    return hashlib.sha256(b).hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def is_count(v):
    return type(v) is int and v >= 0


def is_hex64(v):
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def grade(export_path, op_pub_hex, refusals_dir=None, expect_marker=None):
    out = {"schema": "jidec-l2-verify-v1", "level": 0, "problems": []}
    prob = out["problems"]

    def fail(level_cap, msg):
        prob.append({"cap": level_cap, "why": msg})

    raw = open(export_path, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail(0, "the export is not UTF-8")
        return out
    lines = [x for x in text.split("\n") if x.strip()]
    try:
        recs = [jload(x) for x in lines]
    except (Bad, ValueError) as e:
        fail(0, "a line is not one strict JSON object: %s" % e)
        return out
    if not recs or not all(isinstance(r, dict) for r in recs):
        fail(0, "the export holds no records, or a line is not an object")
        return out
    marker, entries = recs[-1], recs[:-1]
    if marker.get("schema") != "jidec-head-v1" or not entries:
        fail(0, "the export does not end in a jidec-head-v1 marker after at least one entry")
        return out

    # ---- L1: chain
    prev, last_n = "0" * 64, 0
    by_n = {}
    for e in entries:
        n = e.get("n")
        if type(n) is not int or n <= last_n:
            fail(0, "entry ordinals must be integers that strictly increase (at %r)" % (n,))
            return out
        body = {k: e[k] for k in ("n", "schema", "claim_sha256", "created_at", "prev_entry_sha256") if k in e}
        if e.get("prev_entry_sha256") != prev:
            fail(0, "entry %d does not link to the entry before it" % n)
            return out
        if h256(canon(body)) != e.get("entry_sha256"):
            fail(0, "entry %d: entry_sha256 does not recompute" % n)
            return out
        prev, last_n, by_n[n] = e["entry_sha256"], n, e
    mb = {"n": marker.get("n"), "schema": "jidec-head-v1", "prev_entry_sha256": marker.get("prev_entry_sha256"), "head": marker.get("head")}
    if marker.get("n") != last_n or marker.get("head") != prev or marker.get("prev_entry_sha256") != prev:
        fail(0, "the end marker does not bind the last entry (its n is the head's n, head = prev = the last hash)")
        return out
    if h256(canon(mb)) != marker.get("entry_sha256"):
        fail(0, "the end marker's hash does not recompute")
        return out
    if expect_marker and marker["entry_sha256"] != expect_marker:
        fail(0, "the end marker differs from the one held from earlier")
        return out

    # ---- L1: record binding
    records = {}
    for n, e in by_n.items():
        rc = e.get("record_canonical")
        if not isinstance(rc, str) or h256(rc.encode("utf-8")) != e.get("claim_sha256"):
            fail(0, "entry %d: record_canonical is missing or does not hash to claim_sha256" % n)
            return out
        try:
            r = jload(rc)
        except (Bad, ValueError) as ex:
            fail(0, "entry %d: the record bytes are not one strict JSON object: %s" % (n, ex))
            return out
        if not isinstance(r, dict) or not isinstance(r.get("schema"), str):
            fail(0, "entry %d: the record has no schema" % n)
            return out
        records[n] = r
    out["level"] = 1
    out["entries"] = len(by_n)
    out["marker_sha256"] = marker["entry_sha256"]

    # ---- L2: keys and signatures
    op_pub = bytes.fromhex(op_pub_hex)
    op_kid = h256(op_pub)
    ledger_keys = {}          # key_id -> (public bytes, n of the statement)

    def signed_by(n, kid, pub):
        s = by_n[n].get("record_sig")
        if not isinstance(s, dict) or s.get("alg") != "Ed25519" or s.get("key_id") != kid:
            return "entry %d names its signer %s but carries no Ed25519 record_sig by it" % (n, kid[:12])
        try:
            sig = bytes.fromhex(s.get("sig", ""))
        except ValueError:
            return "entry %d: record_sig is not hex" % n
        if not ed25519_ok(pub, by_n[n]["record_canonical"].encode("utf-8"), sig):
            return "entry %d: the signature does not verify" % n
        return None

    windows = []
    for n in sorted(records):
        r = records[n]
        if r["schema"] == "nenrin-key-statement-v1":
            lk = r.get("ledger_key") or {}
            if r.get("operator_key_id") != op_kid:
                fail(1, "entry %d: the key statement names an operator key other than the pinned one" % n)
                continue
            why = signed_by(n, op_kid, op_pub)
            if why:
                fail(1, why)
                continue
            try:
                lpub = bytes.fromhex(lk.get("public_key", ""))
            except ValueError:
                lpub = b""
            if lk.get("alg") != "Ed25519" or len(lpub) != 32 or lk.get("key_id") != h256(lpub):
                fail(1, "entry %d: the ledger key is not an Ed25519 key whose id is the sha256 of its bytes" % n)
                continue
            ledger_keys[lk["key_id"]] = (lpub, n)
        elif r["schema"] == "nenrin-head-checkpoint-v2":
            kid = r.get("signer_key_id")
            k = ledger_keys.get(kid)
            if k is None or k[1] >= n:
                fail(1, "entry %d: the checkpoint's signer is not a ledger key named by the operator before it" % n)
            else:
                why = signed_by(n, kid, k[0])
                if why:
                    fail(1, why)
            pc, lh = r.get("production_count") or {}, r.get("ledger_head") or {}
            a, b = pc.get("from"), pc.get("to")
            got = [pc.get(x) for x in ("received", "refused", "lost")]
            if not (is_count(a) and is_count(b) and a >= 1 and b >= a and all(is_count(x) for x in got)):
                fail(1, "entry %d: the window or its counts are not non-negative integers with 1 <= from <= to" % n)
                continue
            rec_v, ref_v, lost_v = got
            byc = r.get("refused_by_class")
            if not isinstance(byc, dict) or not all(is_count(x) for x in byc.values()) or sum(byc.values()) != ref_v:
                fail(1, "entry %d: refused_by_class does not sum to refused" % n)
            written = sum(1 for m in by_n if a <= m <= b)
            if written + ref_v + lost_v != rec_v:
                fail(1, "entry %d: window %d..%d does not close: %d written + %d refused + %d lost != %d received"
                     % (n, a, b, written, ref_v, lost_v, rec_v))
            if lh.get("n") != b:
                fail(1, "entry %d: ledger_head.n is %r, not the window's to %d" % (n, lh.get("n"), b))
            elif b not in by_n or lh.get("entry_sha256") != by_n[b]["entry_sha256"]:
                fail(1, "entry %d: ledger_head.entry_sha256 is not the hash of entry %d" % (n, b))
            elif lh.get("marker_sha256") != h256(canon({"n": b, "schema": "jidec-head-v1", "prev_entry_sha256": lh["entry_sha256"], "head": lh["entry_sha256"]})):
                fail(1, "entry %d: ledger_head.marker_sha256 is not the marker over (to, its hash)" % n)
            if n <= b:
                fail(1, "entry %d: a checkpoint cannot lie inside the window it declares" % n)
            if refusals_dir is not None:
                want = r.get("refusals_sha256")
                hit = None
                for name in sorted(os.listdir(refusals_dir)):
                    p = os.path.join(refusals_dir, name)
                    if name.startswith("refusals-") and os.path.isfile(p) and h256(open(p, "rb").read()) == want:
                        hit = p
                        break
                if hit is None:
                    fail(1, "entry %d: no refusal list in the folder hashes to refusals_sha256" % n)
                else:
                    cnt = {}
                    try:
                        for x in open(hit, "rb").read().decode("utf-8").splitlines():
                            c = jload(x).get("class")
                            cnt[c] = cnt.get(c, 0) + 1
                    except (Bad, ValueError, AttributeError):
                        cnt = None
                    if cnt != byc:
                        fail(1, "entry %d: the refusal list does not count to refused_by_class" % n)
            windows.append((n, a, b, rec_v, ref_v, lost_v, written))

    # ---- L2: tiling and tail
    if not windows:
        fail(1, "no nenrin-head-checkpoint-v2 declaration in the export")
    expect = 1
    for n, a, b, *_ in windows:
        if a != expect:
            fail(1, "entry %d: the window starts at %d, not %d (%s)" % (n, a, expect, "a gap" if a > expect else "an overlap"))
        expect = max(expect, b + 1)
    tail = sorted(m for m in by_n if m >= expect)
    if tail and tail != list(range(expect, expect + len(tail))):
        fail(1, "the undeclared tail %d.. has an ordinal gap: a loss no declaration covers" % expect)
    out["windows"] = [{"at": n, "from": a, "to": b, "written": w, "refused": f, "lost": lo, "received": rv}
                      for n, a, b, rv, f, lo, w in windows]
    out["tail"] = [tail[0], tail[-1]] if tail else None
    out["produced"] = sum(w[3] for w in windows)
    out["ledger_keys"] = sorted(ledger_keys)
    if not prob:
        out["level"] = 2
    return out


def run(argv):
    opt, i = {}, 0
    while i < len(argv):
        if argv[i] not in ("--export", "--operator-key", "--refusals", "--expect-marker") or i + 1 >= len(argv) or argv[i][2:] in opt:
            raise Bad("arguments: --export <f> --operator-key <hex> [--refusals <folder>] [--expect-marker <hex>]")
        opt[argv[i][2:]] = argv[i + 1]
        i += 2
    if "export" not in opt or "operator-key" not in opt or not is_hex64(opt["operator-key"]):
        raise Bad("--export and a 64-hex --operator-key are required")
    return grade(opt["export"], opt["operator-key"], opt.get("refusals"), opt.get("expect-marker"))


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import tempfile
    import jidec_l2_synth as syn
    ok = []

    def t(name, cond):
        ok.append(bool(cond))
        print(("ok    " if cond else "NG    ") + name)

    t("RFC 8032 test 1 verifies here too", ed25519_ok(bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"), b"",
      bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")))
    op = syn.KEYS["operator"]["pub"].hex()
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "t")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            syn.write(out)
        for v, want, what in syn.VARIANTS:
            d = os.path.join(out, v)
            r = grade(os.path.join(d, "export.jsonl"), op, d)
            t("%-22s L%d (expected %s): %s" % (v, r["level"], want, (r["problems"][0]["why"] if r["problems"] else "no problem")[:96]), "L%d" % r["level"] == want)
        r = grade(os.path.join(out, "honest", "export.jsonl"), op, os.path.join(out, "honest"))
        t("honest: windows 8 + 7 + 5 received, tail 18..20", [w["received"] for w in r["windows"]] == [8, 7, 5] and r["tail"] == [18, 20])
        r = grade(os.path.join(out, "honest", "export.jsonl"), syn.KEYS["stranger"]["pub"].hex(), os.path.join(out, "honest"))
        t("pinning a different operator key drops honest to L1", r["level"] == 1)
        r = grade(os.path.join(out, "refusal_list_short", "export.jsonl"), op, None)
        t("without the refusal lists, the short list is not seen (it is not in the export)", r["level"] == 2)
        r = grade(os.path.join(out, "honest", "export.jsonl"), op, os.path.join(out, "honest"), expect_marker="0" * 64)
        t("a marker other than the one held is L0", r["level"] == 0)
    n = sum(ok)
    print("jidec_l2_verify selftest %d / %d %s" % (n, len(ok), "all green" if n == len(ok) else "NG"))
    return 0 if n == len(ok) else 1


def main():
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    try:
        r = run(sys.argv[1:])
    except (Bad, OSError) as e:
        sys.stderr.write("JIDEC_L2_VERIFY_NG usage %s\n" % e)
        return 2
    sys.stdout.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
    if r["problems"]:
        sys.stderr.write("JIDEC_L2_VERIFY_NG L%d %s\n" % (r["level"], r["problems"][0]["why"]))
        return 1
    sys.stderr.write("JIDEC_L2_VERIFY_OK L%d\n" % r["level"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

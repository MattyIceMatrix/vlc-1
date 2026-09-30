#!/usr/bin/env python3
"""Cases for the chain mechanism and produced-count kinds no worked example uses.

Every shipped adapter uses sha256-chain-canonical or sha256-chain-prefix, and
every shipped example derives its produced count from sum_of_end_marker_fields.
The rest of the checker was reachable and untested (reported by babyblueviper1
in vlc-1#1, finding 4). Writing these cases found EXT-013 (under
sha256-prev-field, deleted and reordered records verified) and EXT-014
(max_ordinal could not see loss at either end of the sequence).

    python3 examples/mechanism_cases.py <outdir>

prints one line per case:  <log> <adapter> <requirement> <expected> <check|xfail>
"""
import copy, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "adapters", "generic-appjsonl.json")


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(path, recs):
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(json.dumps(r) for r in recs) + "\n")


def main(out):
    try:
        sys.stdout.reconfigure(newline="\n")
    except (AttributeError, ValueError):
        pass
    os.makedirs(out, exist_ok=True)
    base = json.load(open(BASE))
    cases = []

    # --- sha256-prev-field: each record must link to the one before it ------
    pf = copy.deepcopy(base)
    pf["integrity"] = dict(base["integrity"], mechanism="sha256-prev-field",
                           hash_field="hash", prev_field="prev",
                           root={"kind": "constant", "value": "00" * 32},
                           end_marker={"class": "END", "head_field": "head",
                                       "self_bound": True})
    pfa = os.path.join(out, "prev-field.adapter.json")
    json.dump(pf, open(pfa, "w"))

    prev, recs = "00" * 32, []
    for b in [{"class": "EPOCH_START", "producer": "x"}] + \
             [{"class": "inference", "seq": i, "verdict": "allow"} for i in range(8)]:
        r = dict(b, prev=prev)
        r["hash"] = sha(prev.encode() + canon(b).encode())
        recs.append(r)
        prev = r["hash"]
    end = {"class": "END", "records": 8, "lost_total": 0, "head": prev, "prev": prev}
    end["hash"] = sha(prev.encode() + canon({k: v for k, v in end.items()
                                            if k not in ("prev", "hash")}).encode())
    honest = recs + [end]

    def case(name, log_recs, adapter, req, expect, mode="check", anchor=None):
        p = os.path.join(out, name + ".jsonl")
        write(p, log_recs)
        cases.append((p, adapter, req, expect, mode) + ((anchor,) if anchor else ()))

    case("prev-field-honest", honest, pfa, "VLC-L1-1", "PASS")
    case("prev-field-interior-deleted",
         [r for r in honest if r.get("seq") != 4], pfa, "VLC-L1-1", "FAIL")
    swapped = honest[:]
    swapped[3], swapped[5] = swapped[5], swapped[3]
    case("prev-field-reordered", swapped, pfa, "VLC-L1-1", "FAIL")

    # --- produced-count kinds: loss at either end of the sequence -----------
    def chained(events, end_extra):
        prev, outr = "00" * 32, []
        for r in events:
            h = sha(prev.encode() + canon(r).encode())
            outr.append(dict(r, hash=h)); prev = h
        e = dict({"class": "END", "head": prev}, **end_extra)
        outr.append(dict(e, hash=sha(prev.encode() + canon(e).encode())))
        return outr

    for kind, field in (("field_of_end_marker", "records"),
                        ("field_of_any", "records"),
                        ("max_ordinal", "seq")):
        a = copy.deepcopy(base)
        a["loss"]["produced"] = {"kind": kind, "field": field}
        if kind == "max_ordinal":
            # EXT-014: the producer declares the sequence's bounds
            a["loss"]["produced"].update(high_water_field="last_seq", start=0)
        ap = os.path.join(out, f"{kind}.adapter.json")
        json.dump(a, open(ap, "w"))
        for tag, keep in (("all-delivered", range(10)),
                          ("tail-lost", range(8)),
                          ("head-lost", range(2, 10))):
            ev = [{"class": "EPOCH_START", "producer": "x"}] + \
                 [{"class": "inference", "seq": i, "verdict": "allow"} for i in keep]
            expect = "PASS" if tag == "all-delivered" else "FAIL"
            # the producer made seq 0..9 and says so in its end marker
            case(f"{kind}-{tag}",
                 chained(ev, {"records": 10, "lost_total": 0, "last_seq": 9}),
                 ap, "VLC-L2-5", expect)

    # EXT-014: max_ordinal with no declared high-water mark is refused rather
    # than inferred from the ordinals that arrived
    a = copy.deepcopy(base)
    a["loss"]["produced"] = {"kind": "max_ordinal", "field": "seq"}
    ap = os.path.join(out, "max_ordinal-undeclared.adapter.json")
    json.dump(a, open(ap, "w"))
    ev = [{"class": "EPOCH_START", "producer": "x"}] + \
         [{"class": "inference", "seq": i, "verdict": "allow"} for i in range(10)]
    case("max_ordinal-bounds-undeclared",
         chained(ev, {"records": 10, "lost_total": 0}), ap, "VLC-L2-1", "FAIL")

    # --- sha256-canonical-fields: hash = sha256(canon(declared fields)) ------
    # One canonical object over exactly the adapter's hash_fields, predecessor
    # link included. Conditions (vlc-1#3, 2026-09-22): a field a later
    # requirement reads must be inside hash_fields; names ASCII-only; an absent
    # optional field is omitted, never serialized as null.
    plain = json.load(open(os.path.join(HERE, "..", "adapters", "plain-jsonl.json")))
    HF = ["kind", "index", "accepted_at", "request_digest", "prev", "commitment_ref"]
    cfad = copy.deepcopy(plain)
    cfad["name"] = "canonical-fields-case"
    cfad["record_class_field"] = "kind"
    cfad["marker_classes"], cfad["non_event_classes"] = [], []
    cfad["integrity"] = {"mechanism": "sha256-canonical-fields", "hash_field": "hash",
                         "prev_field": "prev", "hash_fields": HF,
                         "root": {"kind": "constant", "value": "00" * 32},
                         "primitive": "SHA-256", "documented": True, "primitive_documented": True}
    cfa = os.path.join(out, "canonical-fields.adapter.json")
    json.dump(cfad, open(cfa, "w"))

    def cf_chain(rows, null_ref_at=None):
        prev, outr = "00" * 32, []
        for n, extra in enumerate(rows, 1):
            r = {"kind": "admission", "index": n, "accepted_at": f"2026-09-2{n % 10}T00:00:0{n % 10}Z",
                 "request_digest": sha(f"req-{n}".encode()), "prev": prev}
            r.update(extra)
            if null_ref_at == n:
                r["commitment_ref"] = None               # the mutant a naive producer emits
            r["hash"] = sha(canon({f: r[f] for f in HF if f in r}).encode())
            outr.append(r)
            prev = r["hash"]
        return outr

    ref = {"commitment_ref": sha(b"commitment")}
    case("canonical-fields-optional-absent", cf_chain([{}] * 6), cfa, "VLC-L1-1", "PASS")
    case("canonical-fields-optional-present", cf_chain([{}, ref, {}, ref, ref, {}]), cfa, "VLC-L1-1", "PASS")
    # null-serialized: its hash is computed WITH the null, so it is self-consistent --
    # a checker that hashed what it was given would pass it. It must be refused.
    case("canonical-fields-null-serialized", cf_chain([{}] * 6, null_ref_at=3), cfa, "VLC-L1-1", "FAIL")
    tampered = cf_chain([{}, ref, {}, ref, ref, {}])
    tampered[2]["accepted_at"] = "2026-09-29T23:59:59Z"
    case("canonical-fields-field-edited", tampered, cfa, "VLC-L1-1", "FAIL")
    case("canonical-fields-interior-deleted",
         [r for r in cf_chain([{}] * 6) if r["index"] != 4], cfa, "VLC-L1-1", "FAIL")
    # Deletion and reordering both fail because the predecessor link is INSIDE the
    # hashed object, not beside it. That holds today; these two keep it holding.
    # sha256-prev-field has had a reorder vector since EXT-014 and this mechanism
    # shipped without one -- the protection existed with nothing to notice it going.
    swapped = cf_chain([{}] * 6)
    swapped[2], swapped[3] = swapped[3], swapped[2]
    case("canonical-fields-reordered", swapped, cfa, "VLC-L1-1", "FAIL")
    unlinked = cf_chain([{}] * 6)
    unlinked[3]["prev"] = "00" * 32          # a valid-looking root, in the wrong place
    case("canonical-fields-prev-substituted", unlinked, cfa, "VLC-L1-1", "FAIL")
    # a field the checker reads (record_class_field) outside hash_fields is unanchored
    un = copy.deepcopy(cfad)
    un["integrity"]["hash_fields"] = [f for f in HF if f != "kind"]
    una = os.path.join(out, "canonical-fields-unanchored.adapter.json")
    json.dump(un, open(una, "w"))
    case("canonical-fields-unanchored-read-field", cf_chain([{}] * 6), una, "VLC-L1-1", "FAIL")
    na = copy.deepcopy(cfad)
    na["integrity"]["hash_fields"] = HF + ["accept\u00e9d_at"]
    naa = os.path.join(out, "canonical-fields-non-ascii.adapter.json")
    json.dump(na, open(naa, "w"))
    case("canonical-fields-non-ascii-name", cf_chain([{}] * 6), naa, "VLC-L1-1", "FAIL")

    # End marker's head field (Oga, vlc-1#5, 2026-09-27): VLC-L1-3 compares it with the head recomputed from the
    # chain, so it is anchored by that comparison and need not be listed in hash_fields. A non-self-bound end
    # marker whose head is NOT in hash_fields must pass; the same log with the head edited must still fail L1-3.
    em = copy.deepcopy(cfad)
    em["integrity"]["end_marker"] = {"class": "END", "head_field": "head", "self_bound": False}
    ema = os.path.join(out, "canonical-fields-end-marker.adapter.json")
    json.dump(em, open(ema, "w"))
    chain_em = cf_chain([{}] * 6)
    chain_em.append({"kind": "END", "head": chain_em[-1]["hash"]})
    case("canonical-fields-end-marker-head-unhashed", chain_em, ema, "VLC-L1-1", "PASS")
    # EXT-022 (2026-09-29) reverses the next expectation, which EXT-020 set to PASS. The head
    # comparison anchors the head against the chain, but the chain does not bind the marker: drop
    # the tail, copy the new last hash into the marker, and the comparison still holds (the
    # "resealed" case below, which passed VLC-L1-3 before the fix). On the log alone, an
    # unbound end marker cannot establish VLC-L1-3; --expect-head can (selftest section 17).
    case("canonical-fields-end-marker-head-ok", chain_em, ema, "VLC-L1-3", "FAIL")
    bad_head = copy.deepcopy(chain_em)
    bad_head[-1]["head"] = "ab" * 32
    case("canonical-fields-end-marker-head-edited", bad_head, ema, "VLC-L1-3", "FAIL")

    # EXT-020, maintainer's review of #6: the exemption must be exactly as narrow as stated. The head is
    # exempt from hash_fields only because VLC-L1-3 anchors it, so every way of misstating the head must still
    # fail there, and an end-marker field with no such comparison must still be refused as unanchored.
    no_head = copy.deepcopy(chain_em)
    del no_head[-1]["head"]
    case("canonical-fields-end-marker-head-missing", no_head, ema, "VLC-L1-3", "FAIL")
    early_head = copy.deepcopy(chain_em)
    early_head[-1]["head"] = chain_em[3]["hash"]           # a real record, claiming a shorter log
    case("canonical-fields-end-marker-head-earlier", early_head, ema, "VLC-L1-3", "FAIL")
    tail_cut = copy.deepcopy(chain_em[:-2]) + [copy.deepcopy(chain_em[-1])]   # last event dropped, marker kept
    case("canonical-fields-end-marker-tail-dropped", tail_cut, ema, "VLC-L1-3", "FAIL")
    resealed = copy.deepcopy(chain_em[:-3]) + [dict(chain_em[-1], head=chain_em[-4]["hash"])]
    case("canonical-fields-end-marker-tail-dropped-resealed", resealed, ema, "VLC-L1-3", "FAIL")
    emc = copy.deepcopy(em)
    emc["loss"] = dict(emc.get("loss", {}), produced={"kind": "field_of_end_marker", "field": "produced"})
    emca = os.path.join(out, "canonical-fields-end-marker-count.adapter.json")
    json.dump(emc, open(emca, "w"))
    counted = copy.deepcopy(chain_em)
    counted[-1]["produced"] = 6
    case("canonical-fields-end-marker-count-unhashed", counted, emca, "VLC-L1-1", "FAIL")

    merkle_cases(out, case)

    for c in cases:
        print(" ".join(c))


# --- merkle-tlog (1.4.3-draft, EXT-026) -------------------------------------
# An RFC 6962 Merkle tree over the entries, closed by a C2SP checkpoint (origin,
# size, root) in a signed note with an Ed25519 signature -- the shape Trillian
# Tessera / Rekor v2 write (examples/third-party/tessera-live). Seven entries, so
# the tree is not a power of two. The signing below is RFC 8032 section 5.1.6 on
# the checker's own curve arithmetic; the verifier it exercises is checked
# separately against RFC 8032's test vector 1 and against a signature made by Go's
# note package (the Tessera capture), in selftest.sh.
def _ed_sign(seed, msg):
    sys.path.insert(0, os.path.join(HERE, ".."))
    import conformance as c

    def enc(pt):
        zi = pow(pt[2], c._ED_P - 2, c._ED_P)
        x, y = pt[0] * zi % c._ED_P, pt[1] * zi % c._ED_P
        return (y | ((x & 1) << 255)).to_bytes(32, "little")

    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    pub = enc(c._ed_mul(a, c._ED_B))
    r = int.from_bytes(hashlib.sha512(h[32:] + msg).digest(), "little") % c._ED_L
    R = enc(c._ed_mul(r, c._ED_B))
    k = int.from_bytes(hashlib.sha512(R + pub + msg).digest(), "little") % c._ED_L
    return pub, R + ((r + k * a) % c._ED_L).to_bytes(32, "little")


def merkle_cases(out, case):
    import base64
    b64 = lambda b: base64.b64encode(b).decode()
    origin = "vlc-1.selftest/merkle"
    seed, other = hashlib.sha256(b"vlc-1 merkle case key").digest(), hashlib.sha256(b"another key").digest()

    def vkey(sd):
        pub, _ = _ed_sign(sd, b"")
        raw = b"\x01" + pub
        kh = hashlib.sha256(origin.encode() + b"\n" + raw).digest()[:4].hex()
        return f"{origin}+{kh}+{b64(raw)}"

    def leaf(d):
        return hashlib.sha256(b"\x00" + d.encode()).digest()

    def mth(ls):
        if len(ls) == 1:
            return ls[0]
        k = 1
        while k * 2 < len(ls):
            k *= 2
        return hashlib.sha256(b"\x01" + mth(ls[:k]) + mth(ls[k:])).digest()

    def checkpoint(datas, sd=seed):
        root = mth([leaf(d) for d in datas])
        body = f"{origin}\n{len(datas)}\n{b64(root)}\n"
        _, sig = _ed_sign(sd, body.encode())
        kh = bytes.fromhex(vkey(sd).split("+")[1])
        note = body + "\n— " + origin + " " + b64(kh + sig) + "\n"
        return {"class": "checkpoint", "origin": origin, "size": len(datas),
                "root_hash": b64(root), "note": note}, root

    def log(datas, sd=seed):
        cp, root = checkpoint(datas, sd)
        return [{"class": "entry", "index": i, "data": d} for i, d in enumerate(datas)] + [cp], root

    base = {"name": "merkle-tlog-case", "record_class_field": "class", "marker_classes": [],
            "non_event_classes": ["checkpoint"],
            "integrity": {"mechanism": "merkle-tlog", "leaf_field": "data", "leaf_encoding": "utf-8",
                          "index_field": "index", "entry_class": "entry",
                          "end_marker": {"class": "checkpoint", "head_field": "root_hash",
                                         "head_encoding": "base64", "size_field": "size",
                                         "note_field": "note"},
                          "verifier_key": vkey(seed), "documented": True,
                          "primitive": "SHA-256, Ed25519", "primitive_documented": True},
            "loss": {"mode": "ordinal", "ordinal_field": "index",
                     "produced": {"kind": "field_of_end_marker", "field": "size"}},
            "coverage": {"mode": "none"}, "policy": {"mode": "none"},
            "independence": {"mode": "self_reported", "audited_process_can_write_records": True,
                             "boundary_statement": "test vector"}}

    def adapter(name, mod=None):
        a = copy.deepcopy(base)
        if mod:
            mod(a)
        p = os.path.join(out, f"merkle-{name}.adapter.json")
        json.dump(a, open(p, "w"))
        return p

    sa = adapter("signed")
    datas = ['{"event":"tool_call","tool":"t%d","decision":"%s"}\n' % (i, "deny" if i == 3 else "allow")
             for i in range(7)]
    honest, root7 = log(datas)
    root3 = mth([leaf(d) for d in datas[:3]])

    case("merkle-valid", honest, sa, "VLC-L1-1", "PASS")
    case("merkle-valid-end", honest, sa, "VLC-L1-3", "PASS")
    case("merkle-valid-produced", honest, sa, "VLC-L2-5", "PASS")
    # removing any entry fails VLC-L1-1: with indices left as delivered (a gap) ...
    case("merkle-entry-removed", [r for r in honest if r.get("index") != 3], sa, "VLC-L1-1", "FAIL")
    # ... and with the survivors renumbered, so only the size and root can catch it
    kept = [r for r in honest if r.get("index") != 3]
    renum = [dict(r, index=i) if r["class"] == "entry" else r for i, r in enumerate(kept)]
    case("merkle-entry-removed-renumbered", renum, sa, "VLC-L1-1", "FAIL")
    alt = copy.deepcopy(honest)
    alt[3]["data"] = alt[3]["data"].replace("deny", "allow")
    case("merkle-entry-altered", alt, sa, "VLC-L1-1", "FAIL")
    swp = copy.deepcopy(honest)
    swp[2]["data"], swp[5]["data"] = swp[5]["data"], swp[2]["data"]
    case("merkle-reordered", swp, sa, "VLC-L1-1", "FAIL")
    case("merkle-tail-cut-checkpoint-kept", honest[:5] + [honest[-1]], sa, "VLC-L1-1", "FAIL")
    case("merkle-tail-cut-checkpoint-dropped", honest[:5], sa, "VLC-L1-3", "FAIL")
    # a tail cut resealed BY THE KEY HOLDER verifies on the log alone (as a
    # rewritten chain does); a verifier holding the size-7 checkpoint refuses it
    resealed, _ = log(datas[:5])
    case("merkle-tail-cut-resealed", resealed, sa, "VLC-L1-1", "PASS")
    case("merkle-tail-cut-resealed-vs-held-head", resealed, sa, "VLC-L1-1", "FAIL",
         anchor="--expect-head=" + root7.hex())
    case("merkle-tail-cut-resealed-vs-held-root", resealed, sa, "VLC-L1-1", "FAIL",
         anchor="--expect-root=" + root7.hex())
    case("merkle-valid-vs-held-head", honest, sa, "VLC-L1-1", "PASS", anchor="--expect-head=" + root7.hex())
    # an earlier checkpoint held as --expect-root: the log must extend it
    case("merkle-valid-extends-held-root", honest, sa, "VLC-L1-1", "PASS",
         anchor="--expect-root=" + root3.hex())
    rw = datas[:]
    rw[1] = rw[1].replace("allow", "deny")
    rewritten, _ = log(rw)
    case("merkle-prefix-rewritten-resealed", rewritten, sa, "VLC-L1-1", "PASS")
    case("merkle-prefix-rewritten-vs-held-root", rewritten, sa, "VLC-L1-1", "FAIL",
         anchor="--expect-root=" + root3.hex())
    # the signature: a changed signature, another key, and the checkpoint's fields
    # recomputed for altered entries while the signed note is left as it was
    bad_sig = copy.deepcopy(honest)
    n = bad_sig[-1]["note"]
    i = len(n) - 12                      # inside the signature, past the key hash
    bad_sig[-1]["note"] = n[:i] + ("A" if n[i] != "A" else "B") + n[i + 1:]
    case("merkle-signature-altered", bad_sig, sa, "VLC-L1-1", "FAIL")
    other_key = adapter("other-key", lambda a: a["integrity"].__setitem__("verifier_key", vkey(other)))
    case("merkle-wrong-verifier-key", honest, other_key, "VLC-L1-1", "FAIL")
    forged = copy.deepcopy(alt)
    forged[-1]["root_hash"] = b64(mth([leaf(r["data"]) for r in alt[:-1]]))
    case("merkle-altered-fields-recomputed-note-kept", forged, sa, "VLC-L1-1", "FAIL")

    # a wrong root: a checkpoint whose size is right and whose root is not the
    # tree's, signed by the key holder (fields and note agree), and unsigned
    wrong = hashlib.sha256(b"not the root").digest()
    wr = copy.deepcopy(honest)
    wbody = f"{origin}\n{len(datas)}\n{b64(wrong)}\n"
    _, wsig = _ed_sign(seed, wbody.encode())
    wr[-1].update(root_hash=b64(wrong), note=wbody + "\n— " + origin + " " +
                  b64(bytes.fromhex(vkey(seed).split("+")[1]) + wsig) + "\n")
    case("merkle-wrong-root-signed", wr, sa, "VLC-L1-1", "FAIL")

    # without a verifier key the same forgery (note dropped) passes on the log
    # alone -- an unsigned checkpoint is no stronger than a keyless chain -- and
    # fails against the held head
    def unsigned(a):
        del a["integrity"]["verifier_key"]
        del a["integrity"]["end_marker"]["note_field"]
    ua = adapter("unsigned", unsigned)
    forged_u = [dict(r) for r in forged]
    del forged_u[-1]["note"]
    case("merkle-unsigned-altered-resealed", forged_u, ua, "VLC-L1-1", "PASS")
    case("merkle-unsigned-altered-resealed-vs-held-head", forged_u, ua, "VLC-L1-1", "FAIL",
         anchor="--expect-head=" + root7.hex())
    wu = [dict(r) for r in honest]
    wu[-1] = {k: v for k, v in wu[-1].items() if k != "note"}
    wu[-1]["root_hash"] = b64(wrong)
    case("merkle-wrong-root-unsigned", wu, ua, "VLC-L1-1", "FAIL")
    # a signed note with no verifier key: the tree is checked, the signature is
    # not verified and not credited (the report says so)
    na = adapter("note-no-key", lambda a: a["integrity"].pop("verifier_key"))
    case("merkle-valid-note-unverified", honest, na, "VLC-L1-1", "PASS")
    # mapping preconditions: a field a later requirement reads must be bound, and
    # every record before the checkpoint must be a leaf
    un = adapter("unanchored", lambda a: a["loss"].__setitem__("ordinal_field", "seq"))
    case("merkle-unanchored-read-field", honest, un, "VLC-L1-1", "FAIL")
    stray = copy.deepcopy(honest)
    stray[4]["class"] = "checkpoint"
    case("merkle-interior-record-relabelled", stray, sa, "VLC-L1-1", "FAIL")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mechanism-cases")

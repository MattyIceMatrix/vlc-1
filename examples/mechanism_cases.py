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

    def case(name, log_recs, adapter, req, expect, mode="check"):
        p = os.path.join(out, name + ".jsonl")
        write(p, log_recs)
        cases.append((p, adapter, req, expect, mode))

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

    for c in cases:
        print(" ".join(c))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mechanism-cases")

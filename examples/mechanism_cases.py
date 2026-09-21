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

    for c in cases:
        print(" ".join(c))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mechanism-cases")

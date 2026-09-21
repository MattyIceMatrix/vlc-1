#!/usr/bin/env python3
"""Re-sealed mutants for the typed normative obligations (EXT-006).

Each mutant violates exactly one obligation and is then RE-SEALED with the
generator's own chain rule, so VLC-L1-1 still passes and the mutant can only
fail at the requirement it targets. A mutant that fails at L1 instead proves
nothing about the check it names; that was the defect reported in the Annex A
mutations, and this file does not repeat it.

    python3 examples/typed_mutants.py <outdir>

prints one line per case:  <file> <adapter> <requirement> <expected PASS|FAIL>
"""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_examples as mk  # noqa: E402

BASE = os.path.join(HERE, "L4-policybound.jsonl")
ADAPTER = os.path.join(HERE, "..", "adapters", "generic-appjsonl-policy.json")


def load():
    return [json.loads(l) for l in open(BASE) if l.strip()]


def reseal(recs, out):
    root = mk.sha(mk.POLICY)
    g = mk.Log(root=root)
    for r in recs:
        body = {k: v for k, v in r.items() if k not in ("hash", "head")}
        if body.get("class") == "EPOCH_START":
            g.add(body, first=True)
        elif body.get("class") == "END":
            g.add(body, head_field="head")
        else:
            g.add(body)
    open(out, "w").write("\n".join(g.lines) + "\n")


def one(recs, cls):
    return [r for r in recs if r["class"] == cls][0]


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    cases = []

    def case(name, fn, req, expect, adapter=ADAPTER):
        recs = load()
        fn(recs)
        path = os.path.join(outdir, name + ".jsonl")
        reseal(recs, path)
        cases.append((path, adapter, req, expect))

    def adapter(name, mutate):
        a = json.load(open(ADAPTER)); mutate(a)
        p = os.path.join(outdir, name + ".adapter.json"); json.dump(a, open(p, "w"))
        return p

    # controls: an honest log must still pass the requirement under test
    case("control", lambda r: None, "VLC-L2-2", "PASS")

    # VLC-L2-2: a loss declaration states the count AND the interval
    case("drop_no_interval",
         lambda r: [one(r, "DROP").pop(k) for k in ("from_seq", "to_seq")],
         "VLC-L2-2", "FAIL")

    def negative(r):                       # compensated, so the identity still closes
        one(r, "DROP")["lost"] = -3
        one(r, "END")["lost_total"] = -3
    case("negative_loss", negative, "VLC-L2-2", "FAIL")

    def overlap(r):                        # declares lost records that were delivered
        d = one(r, "DROP"); d["from_seq"], d["to_seq"] = 20, 22
    case("range_overlaps_delivered", overlap, "VLC-L2-2", "FAIL")

    # VLC-L3-1a / 1d: every declaration, and absent is not empty
    case("coverage_category_absent",
         lambda r: one(r, "COVERAGE").pop("unattached_here"), "VLC-L3-1a", "FAIL")

    def second(r):
        c = copy.deepcopy(one(r, "COVERAGE")); c.pop("basis", None)
        r.insert(r.index(one(r, "COVERAGE")) + 1, c)
    case("second_coverage_no_basis", second, "VLC-L3-1d", "FAIL")

    # VLC-L4-2: a policy change carries the digests before and after
    def change(r):
        ev = [x for x in r if x["class"] == "inference"]
        r.insert(r.index(ev[20]), {"class": "POLICY", "note": "rules updated"})
    case("policy_change_no_digests", change, "VLC-L4-2", "FAIL")

    # VLC-L4-1 per-record: each event individually, both directions
    perrec = adapter("per_record", lambda a: a["policy"].__setitem__("mode", "per_record"))

    def all_digests(r):
        for x in r:
            if x["class"] == "inference":
                x["policy_digest"] = mk.POLICY
    case("per_record_honest", all_digests, "VLC-L4-1", "PASS", perrec)

    def one_missing(r):                    # the first record's digest used to fill the gap
        all_digests(r)
        [x for x in r if x["class"] == "inference"][5].pop("policy_digest")
    case("per_record_one_missing", one_missing, "VLC-L4-1", "FAIL", perrec)

    # VLC-L4-4: determinism is declared, not inferred from a reference
    nodet = adapter("no_determinism", lambda a: a["policy"]["replay"].pop("deterministic"))
    case("determinism_undeclared", lambda r: None, "VLC-L4-4", "FAIL", nodet)

    for c in cases:
        print(" ".join(c))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/typed-mutants")

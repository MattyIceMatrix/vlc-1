#!/usr/bin/env python3
"""The VLC-1 chain cases from aer1-06/, rerun against the AER-1 -07 Section 7 chain,
plus probes of the new -07 rules.

Uses the reference verifier's own verify_chain_v07() and chain_entry_digest_v07()
from the AER-1 conformance kit (gitlab.com/rambozambodotdev/zambo,
aer1-implementations/python/verifier.py; captured at kit commit aff1330).
Usage: python3 chain_attacks.py /path/to/zambo/aer1-implementations/python
Standard library only. Writes nothing.

Expectations follow -07 Section 7.2 and 7.3. Rebuilt truncations are expected to be
ACCEPTED: Section 7.3 states that limit. "GAP" means the result contradicts the text.
"""
import sys, base64, copy
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from verifier import verify_chain_v07 as verify, chain_entry_digest_v07 as digest

b = lambda s: base64.b64encode(s.encode()).decode()
Z = "0" * 64

def relink(tl):
    """Recompute every prev_digest, as the producer (or an attacker who rebuilds) would."""
    prev = Z
    for e in tl:
        e["prev_digest"] = prev
        prev = digest(e)
    return tl

def build(outputs, job="job-A"):
    tl = [{"id": f"r{i}", "seq": i + 1, "job_id": job, "tool": "live_price",
           "provenance_class": "EXECUTED BY ZAMBO", "canonical_bytes": b(o)} for i, o in enumerate(outputs)]
    tl[-1]["close"] = True
    return relink(tl)

rows = []
def case(group, name, tl, should_reject, note=""):
    f = verify(tl)
    ok = bool(f) == should_reject
    rows.append((group, name, "reject" if should_reject else "accept", "rejected" if f else "ACCEPTED", ok, note, f[:1]))
    print(f"{'ok ' if ok else 'GAP'}  {name:62s} -> {'rejected' if f else 'ACCEPTED'}  {f[:1] if f else ''}")

outs = ['{"coin":"BTC","usd":64000}', '{"coin":"ETH","usd":2400}', '{"coin":"SOL","usd":150}',
        '{"coin":"ADA","usd":0.4}', '{"coin":"DOT","usd":5}']
g = build(outs)
D = lambda: copy.deepcopy(g)

print("-- the 14 cases run against -06 (links not rebuilt by the attacker)")
case("06", "honest timeline", D(), False)
t = D(); t[2]["canonical_bytes"] = b('{"coin":"SOL","usd":1}'); case("06", "edit a middle entry's bytes", t, True)
t = D(); del t[2]; case("06", "delete a middle entry", t, True)
t = D(); t[1], t[2] = t[2], t[1]; case("06", "swap two entries", t, True)
t = D()[:3]; case("06", "drop newest two, no close", t, True)
t = D()[:3]; t[-1]["close"] = True; case("06", "drop newest two, set close:true on new last", t, False,
                                         "Section 7.3 limit: needs an outside commitment")
t = D()[2:]; t[0]["prev_digest"] = Z; case("06", "drop oldest two, zero the new first prev_digest", t, True)
t = D(); t[1]["provenance_class"] = "LOGGED BY AGENT"; case("06", "relabel an entry's provenance_class", t, True)
t = D(); t[2]["tool"] = "send_payment"; t[2]["id"] = "forged"; case("06", "relabel an entry's tool and id", t, True)
t = D(); t[2]["close"] = True; case("06", "set close:true on a middle entry", t, True)
g2 = build(['{"coin":"BTC","usd":64000}', '{"coin":"ETH","usd":2400}', '{"coin":"ETH","usd":2400}', '{"coin":"SOL","usd":150}'])
case("06", "honest timeline with two identical outputs", copy.deepcopy(g2), False)
t = copy.deepcopy(g2); del t[2]; case("06", "delete one of two identical consecutive entries", t, True)
t = copy.deepcopy(g2); t.insert(2, copy.deepcopy(t[2])); case("06", "insert a copy of an entry next to itself", t, True)
o = build(['{"coin":"XRP","usd":0.5}', '{"coin":"ETH","usd":2400}'], job="job-B")
t = copy.deepcopy(o) + copy.deepcopy(g2[2:]); case("06", "splice another job's prefix onto this job's suffix", t, True)

print("-- new: the last entry, which no later entry links to")
t = D(); t[-1]["canonical_bytes"] = b('{"coin":"DOT","usd":500}'); case("tail", "edit the LAST entry's output bytes", t, True,
    "Section 7 says relabeling is detectable; the last entry's digest is referenced by nothing")
t = D(); t[-1]["provenance_class"] = "LOGGED BY AGENT"; case("tail", "relabel the LAST entry's provenance_class", t, True, "same")
t = D(); t[-1]["tool"] = "send_payment"; t[-1]["id"] = "forged"; case("tail", "relabel the LAST entry's tool and id", t, True, "same")

print("-- new: attacker rebuilds the links (Section 7.3 says these verify)")
t = relink(D()[:3]); t[-1]["close"] = True; relink(t); case("rebuild", "rebuilt truncation from the end", t, False, "Section 7.3 limit")
t = D()[2:]
for i, e in enumerate(t): e["seq"] = i + 1
relink(t); case("rebuild", "rebuilt truncation from the start (seq renumbered)", t, False, "Section 7.3 limit")

print("-- new: Section 7.1 / 7.2 rules")
t = D(); t[0]["seq"] = 1.0; relink(t); case("rules", "seq 1.0 on entry 0 (7.1: equivalent to 1, accepted)", t, False)
t = D(); t[0]["seq"] = True; relink(t); case("rules", "seq true (7.1: MUST reject)", t, True)
t = D(); t[0]["seq"] = "1"; case("rules", "seq \"1\" (7.1: MUST reject)", t, True)
t = D(); t[1]["seq"] = 3; relink(t); case("rules", "seq gap, links rebuilt", t, True)
t = D(); t[2]["close"] = "false"; relink(t); case("rules", "close as the string \"false\"", t, True)
t = D()
for e in t: e["job_id"] = "job-Z"
case("rules", "swap job_id on every entry, links not rebuilt", t, True)
t = D(); t[0]["job_id"] = "job-Z"; relink(t); case("rules", "job_id differs on entry 0, links rebuilt", t, True)
t = D(); t[1]["canonical_bytes"] = "not base64!"; case("rules", "invalid base64 (fail closed)", t, True)
t = D(); t[1]["canonical_bytes"] = b('{"coin":"ETH","usd":2400}').rstrip("=") ; case("rules", "base64 with padding stripped (strict decode)", t, True)
t = build(['{"n":"Zürich"}', '{"n":"東京 😀"}']); case("rules", "non-ASCII output and honest chain", t, False)
h = build(outs)
for e in h: e.pop("seq"); e.pop("job_id")
prev = Z
import hashlib
for e in h: e["prev_digest"] = prev; prev = hashlib.sha256(base64.b64decode(e["canonical_bytes"])).hexdigest()
case("rules", "valid -06 timeline must not verify as -07 (7.4)", h, True)

bad = [r for r in rows if not r[4]]
print(f"\n{len(rows) - len(bad)} of {len(rows)} as expected; {len(bad)} gap(s)")
if __name__ == "__main__" and "--json" in sys.argv:
    import json; print(json.dumps(rows))

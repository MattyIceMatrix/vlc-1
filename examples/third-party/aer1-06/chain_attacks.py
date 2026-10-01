#!/usr/bin/env python3
"""VLC-1 truncation and relabel cases run against the AER-1 -06 Section 7 chain.

Uses the reference verifier's own verify_chain() from the AER-1 conformance kit
(gitlab.com/rambozambodotdev/zambo, aer1-implementations/python/verifier.py).
Usage: python3 chain_attacks.py /path/to/zambo/aer1-implementations/python
Standard library only. Writes nothing.
"""
import sys, base64, hashlib, copy
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
from verifier import verify_chain

b = lambda s: base64.b64encode(s.encode()).decode()
H = lambda s: hashlib.sha256(s.encode()).hexdigest()

def build(outputs):
    tl, prev = [], "0" * 64
    for i, o in enumerate(outputs):
        tl.append({"id": f"r{i}", "tool": {"name": "live_price"}, "provenance_class": "EXECUTED BY ZAMBO",
                   "canonical_bytes": b(o), "prev_digest": prev})
        prev = H(o)
    tl[-1]["close"] = True
    return tl

def case(name, tl, should_reject):
    f = verify_chain(tl)
    ok = bool(f) == should_reject
    print(f"{'ok ' if ok else 'GAP'}  {name:56s} -> {'rejected' if f else 'ACCEPTED'}")
    return ok

outs = ['{"coin":"BTC","usd":64000}', '{"coin":"ETH","usd":2400}', '{"coin":"SOL","usd":150}',
        '{"coin":"ADA","usd":0.4}', '{"coin":"DOT","usd":5}']
g = build(outs)
r = [case("honest timeline", g, False)]
t = copy.deepcopy(g); t[2]["canonical_bytes"] = b('{"coin":"SOL","usd":1}'); r.append(case("edit a middle entry's bytes", t, True))
t = copy.deepcopy(g); del t[2]; r.append(case("delete a middle entry", t, True))
t = copy.deepcopy(g); t[1], t[2] = t[2], t[1]; r.append(case("swap two entries", t, True))
t = copy.deepcopy(g[:3]); r.append(case("drop newest two, no close", t, True))
t = copy.deepcopy(g[:3]); t[-1]["close"] = True; r.append(case("drop newest two, set close:true on new last", t, True))
t = copy.deepcopy(g[2:]); t[0]["prev_digest"] = "0" * 64; r.append(case("drop oldest two, zero the new first prev_digest", t, True))
t = copy.deepcopy(g); t[1]["provenance_class"] = "LOGGED BY AGENT"; r.append(case("relabel an entry's provenance_class", t, True))
t = copy.deepcopy(g); t[2]["tool"] = {"name": "send_payment"}; t[2]["id"] = "forged"; r.append(case("relabel an entry's tool and id", t, True))
t = copy.deepcopy(g); t[2]["close"] = True; r.append(case("set close:true on a middle entry", t, True))
g2 = build(['{"coin":"BTC","usd":64000}', '{"coin":"ETH","usd":2400}', '{"coin":"ETH","usd":2400}', '{"coin":"SOL","usd":150}'])
r.append(case("honest timeline with two identical outputs", g2, False))
t = copy.deepcopy(g2); del t[2]; r.append(case("delete one of two identical consecutive entries", t, True))
t = copy.deepcopy(g2); t.insert(2, copy.deepcopy(t[2])); r.append(case("insert a copy of an entry next to itself", t, True))
o = build(['{"coin":"XRP","usd":0.5}', '{"coin":"ETH","usd":2400}'])
t = copy.deepcopy(o) + copy.deepcopy(g2[2:]); r.append(case("splice another job's prefix onto this job's suffix", t, True))
print(f"\n{sum(r)} of {len(r)} as expected; {len(r) - sum(r)} gap(s)")

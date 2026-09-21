#!/usr/bin/env python3
"""
Generate the VLC-1 worked example logs.

These are SYNTHETIC by design: each one is the smallest log that sits exactly at
one rung of the lattice, so the conformance checker's level boundaries can be
tested from both sides.  They imitate an application-layer LLM proxy, NOT the
kernel sensor, because clause 9.3 claims every level is reachable at the
application layer and a claim like that should be exhibited rather than asserted.

Real captured logs from the reference implementation live alongside these and
are marked as captures in README.md.

    ./make_examples.py          # writes *.jsonl into this directory
"""
import hashlib, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
ZERO = "0" * 64
POLICY = "9f2c" + "ab13" * 15          # a stand-in policy digest


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


class Log:
    """Canonical-JSON hash chain: h_i = SHA256(h_{i-1}_hex || canon(body))."""

    def __init__(self, root=ZERO, chained=True):
        self.head = root
        self.lines = []
        self.chained = chained

    def add(self, body, head_field=None, first=False):
        if not self.chained:
            self.lines.append(canon(body))
            return
        if head_field:
            body[head_field] = self.head
        if first:
            h = self.head                      # root record commits to the root
        else:
            h = sha(self.head + canon(body))
            self.head = h
        body["hash"] = h
        self.lines.append(canon(body))

    def write(self, name):
        p = os.path.join(HERE, name)
        open(p, "w").write("\n".join(self.lines) + "\n")
        print(f"  {name:<34} {len(self.lines):>4} records")


def calls(n, route="/v1/chat", seed=1, start=0):
    r = random.Random(seed)
    out = []
    for i in range(n):
        out.append({
            "class": "inference",
            "seq": start + i,
            "ts": 1757000000 + i * 3,
            "route": route,
            "model": "acme-7b",
            "tokens_in": r.randint(40, 900),
            "verdict": r.choice(["allow", "allow", "allow", "audit"]),
        })
    return out


# ---------------------------------------------------------------------------
def l0():
    """No binding at all. The state of most application logs."""
    g = Log(chained=False)
    g.add({"class": "EPOCH_START", "producer": "acme-llm-proxy/2.4"})
    for c in calls(30, seed=10):
        g.add(c)
    g.add({"class": "END", "records": 30})
    g.write("L0-plain.jsonl")


def l1():
    """Tamper-evident and nothing more. Where the industry stops."""
    g = Log()
    g.add({"class": "EPOCH_START", "producer": "acme-llm-proxy/2.4"})
    for c in calls(30, seed=11):
        g.add(c)
    g.add({"class": "END", "records": 30}, head_field="head")
    g.write("L1-hashchain.jsonl")


def _accounted(n_events, lost, seed, coverage=None, policy=False, name=""):
    root = sha(POLICY) if policy else ZERO
    g = Log(root=root)
    first = {"class": "EPOCH_START", "producer": "acme-llm-proxy/2.4",
             "buffer": "bounded-queue-8192", "on_full": "drop_counted"}
    if policy:
        first["policy_digest"] = POLICY
    g.add(first, first=policy)   # a policy-rooted chain commits to the root
                                 # in its first record; a zero-rooted one does not
    if coverage is not None:
        g.add(dict(coverage, **{"class": "COVERAGE"}))
    for c in calls(n_events, seed=seed):
        g.add(c)
    if lost:
        g.add({"class": "DROP", "lost": lost, "from_seq": 12, "to_seq": 12 + lost - 1,
               "cause": "outbound queue full"})
    g.add({"class": "END", "records": n_events, "lost_total": lost},
          head_field="head")
    g.write(name)


def l2():
    """The identity closes and a real loss is declared in-chain."""
    _accounted(40, 7, 12, name="L2-accounted.jsonl")


def l2_looks_complete():
    """The dangerous one.

    Chain valid. Identity closes exactly. Zero declared losses. Every record in
    it is true. And the proxy was terminating TWO routes that session: it was
    instrumented for /v1/chat and not for /v1/responses, so 58 inferences
    produced no record, lost nothing, and left no trace. At L2 this log is
    perfect. Nothing a verifier can compute from it says otherwise.
    """
    _accounted(60, 0, 13, name="L2-looks-complete.jsonl")


def l3():
    """The same session, with the observation surface written down."""
    _accounted(60, 0, 13, name="L3-coverage.jsonl", coverage={
        "attached": "/v1/chat",
        "unattached_here": "/v1/responses",
        "excluded_by_design": "/v1/embeddings,/healthz",
        "n_attached": 1,
        "n_unattached": 1,
        "basis": "enumerated from the proxy route table at startup; every route "
                 "registered on the listener is listed in exactly one of the three "
                 "fields, and coverage_test.sh exercises each in both directions",
    })


def l4():
    """Everything above, plus the rules the verdicts were computed under."""
    _accounted(60, 3, 14, policy=True, name="L4-policybound.jsonl", coverage={
        "attached": "/v1/chat,/v1/responses",
        "unattached_here": "",
        "excluded_by_design": "/v1/embeddings,/healthz",
        "n_attached": 2,
        "n_unattached": 0,
        "basis": "enumerated from the proxy route table at startup; every route "
                 "registered on the listener is listed in exactly one of the three "
                 "fields, and coverage_test.sh exercises each in both directions",
    })


if __name__ == "__main__":
    print("VLC-1 worked examples:")
    l0(); l1(); l2(); l2_looks_complete(); l3(); l4()

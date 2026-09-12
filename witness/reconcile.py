#!/usr/bin/env python3
"""
The witness tier -- reconcile an agent's own transcript against the kernel's record.

    ./reconcile.py --claims agent.jsonl --journal sentinel.jsonl --scope scope.json

WHY THIS EXISTS
---------------
METR and Redwood's investigation of the 2026 Hugging Face incident found agents
that "hack out of the container and replace the system executing tool calls",
letting them ISSUE ONE COMMAND WHILE RUNNING ANOTHER and rewrite what the
transcript said they did.  Confirmed in at least 7% of transcripts; the
investigators note the cases they caught were crude, and that competent spoofing
"may have been harder to detect by design".  Separately ~10% of the activity was
never captured at all, partly through container resets that destroyed evidence.

Every audit trail in the AI stack today is written by, or beside, the process
being audited.  A tool-call log, an SDK trace, a gateway record: all of them are
produced inside the blast radius.  When the auditee controls the recorder, the
record is a claim.

This reconciles TWO independent records:

    the CLAIM   -- the agent's own transcript, produced inside the blast radius
    the WITNESS -- the sentinel journal, produced by a kernel probe the governed
                   session cannot write to, hash-chained, with its coverage and
                   its losses declared (VLC-1 L4)

and reports three things:

    CORROBORATED          both records agree
    UNCORROBORATED CLAIM  the transcript asserts an action the kernel never saw
                          -> fabricated activity, or a tool that did nothing
    UNWITNESSED-BY-CLAIM  the kernel saw an action the transcript never mentions
                          -> hidden activity: the spoof signature

Neither direction alone is enough.  A spoof that claims A and runs B produces
one of each, and only a both-directions check sees the pair.

SCOPE
-----
A kernel journal contains every open a Python interpreter makes at import time.
Reconciling against all of it is noise, and a reconciler that reports thousands
of "unclaimed" dynamic-linker reads is one nobody runs twice.  So the scope is
DECLARED, in a scope file, and echoed into the report -- the same discipline
VLC-1 clause 6 demands of a coverage declaration, applied to the reconciler
itself.  A finding outside the declared scope is not a finding, and a scope that
excludes everything reconciles trivially and says so.
"""
import argparse, json, os, posixpath, re, sys

VERSION = "witness/reconcile 1.1"


# --------------------------------------------------------------------------
# Paths in a sentinel journal are POSIX paths, because they came out of a Linux
# kernel, no matter what machine is reading the journal afterwards.  Using
# os.path here was a real bug: on Windows os.path.normpath("/etc/hostname")
# returns "\\etc\\hostname", the scope regexes stopped matching, and an HONEST
# run reported divergences -- a reconciler crying wolf, which is the one
# failure mode that makes people stop running it.  Found by running the suite
# on Windows, 2026-09-12.
# --------------------------------------------------------------------------
def norm(p):
    """Normalise a path the way the producer wrote it: POSIX, always."""
    return posixpath.normpath(str(p).replace("\\", "/"))


def base(p):
    """Last component, tolerant of either separator."""
    return posixpath.basename(str(p).replace("\\", "/"))


def load_jsonl(path, strip_chain=True):
    """Read JSONL.  Sentinel records carry a trailing ,"h":"..." chain member;
    json.loads handles it fine, so nothing special is needed -- but a record
    that does not parse is reported rather than skipped silently."""
    out, bad = [], 0
    if not os.path.exists(path):
        raise SystemExit(f"not found: {path}")
    for i, line in enumerate(open(path, encoding="utf-8", errors="replace")):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            bad += 1
    return out, bad


# --------------------------------------------------------------------------
# what the agent SAYS it did
# --------------------------------------------------------------------------
def claimed_effects(claims, scope):
    """Project an agent transcript onto the kernel effects it implies.

    The mapping is deliberately shallow and declared in the scope file, because
    guessing what a tool call 'should' have done is how a reconciler starts
    inventing findings.  A tool whose mapping is not declared is reported as
    UNMAPPED and excluded from both directions.
    """
    m = scope.get("claim_map", {})
    execs, opens, conns, unmapped = set(), set(), set(), []
    for c in claims:
        t = c.get(scope.get("claim_tool_field", "tool"))
        spec = m.get(str(t))
        if spec is None:
            unmapped.append(t)
            continue
        kind = spec.get("effect")
        if kind == "exec":
            cmd = str(c.get(spec.get("field", "command"), ""))
            # the claimed binary is the first word, resolved to a basename:
            # the transcript says `cat /etc/hostname`, the kernel says
            # /usr/bin/cat, and comparing basenames is the honest join.
            tok = cmd.strip().split()
            if tok:
                execs.add(base(tok[0]))
        elif kind == "open":
            p = c.get(spec.get("field", "path"))
            if p:
                opens.add(norm(p))
        elif kind == "connect":
            h = c.get(spec.get("field", "host"))
            if h:
                conns.add(str(h))
        elif kind == "none":
            pass
    return execs, opens, conns, unmapped


# --------------------------------------------------------------------------
# what the kernel SAW
# --------------------------------------------------------------------------
def witnessed_effects(journal, scope):
    ex_excl = [re.compile(r) for r in scope.get("exec_exclude", [])]
    op_incl = [re.compile(r) for r in scope.get("open_include", [])]
    op_excl = [re.compile(r) for r in scope.get("open_exclude", [])]
    watch_conn = bool(scope.get("connect_in_scope", True))
    sess = scope.get("session")

    execs, opens, conns = set(), set(), set()
    n_total, n_scoped = 0, 0
    for r in journal:
        cls = r.get("class")
        if cls in (None, "H0", "HEAD", "GAP", "COVERAGE", "EPOCH"):
            continue
        if sess is not None and r.get("sess") not in (None, sess):
            continue
        n_total += 1
        if cls == "exec":
            p = str(r.get("path", ""))
            if any(x.search(p) for x in ex_excl):
                continue
            execs.add(base(p)); n_scoped += 1
        elif cls in ("file_read", "dir_open"):
            p = norm(r.get("path", ""))
            if op_incl and not any(x.search(p) for x in op_incl):
                continue
            # Runtime housekeeping a transcript will never mention and no
            # auditor wants reported: excluded BY NAME, in the scope file, so
            # the exclusion is visible in the report and can be argued with.
            if any(x.search(p) for x in op_excl):
                continue
            opens.add(p); n_scoped += 1
        elif cls == "connect" and watch_conn:
            conns.add(str(r.get("daddr", ""))); n_scoped += 1
    return execs, opens, conns, n_total, n_scoped


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=VERSION)
    ap.add_argument("--claims", required=True, help="the agent's own transcript (JSONL)")
    ap.add_argument("--journal", required=True, help="the kernel witness (sentinel JSONL)")
    ap.add_argument("--scope", required=True, help="declared reconciliation scope (JSON)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-agreement", action="store_true",
                    help="exit non-zero if the two records diverge at all")
    a = ap.parse_args()

    scope = json.load(open(a.scope))
    claims, bad_c = load_jsonl(a.claims)
    journal, bad_j = load_jsonl(a.journal)

    c_ex, c_op, c_cn, unmapped = claimed_effects(claims, scope)
    w_ex, w_op, w_cn, n_tot, n_scoped = witnessed_effects(journal, scope)

    findings = []
    for kind, cl, wt in (("exec", c_ex, w_ex), ("open", c_op, w_op), ("connect", c_cn, w_cn)):
        for x in sorted(cl - wt):
            findings.append({"severity": "UNCORROBORATED CLAIM", "kind": kind, "what": x,
                             "meaning": "the transcript asserts this and the kernel never saw it"})
        for x in sorted(wt - cl):
            findings.append({"severity": "UNWITNESSED-BY-CLAIM", "kind": kind, "what": x,
                             "meaning": "the kernel saw this and the transcript does not mention it"})
    corroborated = len(c_ex & w_ex) + len(c_op & w_op) + len(c_cn & w_cn)

    spoof = any(f["severity"] == "UNCORROBORATED CLAIM" for f in findings) and \
            any(f["severity"] == "UNWITNESSED-BY-CLAIM" for f in findings)

    report = {
        "tool": VERSION,
        "claims_file": a.claims, "journal_file": a.journal,
        "scope": {k: scope.get(k) for k in
                  ("name", "session", "exec_exclude", "open_include", "open_exclude",
                   "connect_in_scope")},
        "claim_records": len(claims), "journal_records": n_tot,
        "journal_records_in_scope": n_scoped,
        "unparseable": {"claims": bad_c, "journal": bad_j},
        "unmapped_tools": sorted(set(map(str, unmapped))),
        "corroborated": corroborated,
        "findings": findings,
        "substitution_signature": spoof,
    }

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{VERSION}")
        print(f"  claim record  : {a.claims}  ({len(claims)} records, written by the audited process)")
        print(f"  kernel witness: {a.journal}  ({n_tot} records, {n_scoped} in scope)")
        print(f"  scope         : {scope.get('name','(unnamed)')}")
        for k in ("exec_exclude", "open_include", "open_exclude", "connect_in_scope"):
            print(f"      {k:<16} {scope.get(k)}")
        if report["unmapped_tools"]:
            print(f"  UNMAPPED TOOLS (excluded both ways): {', '.join(report['unmapped_tools'])}")
        print()
        print(f"  corroborated  : {corroborated}")
        if not findings:
            print("  divergences   : none — the two records agree over the declared scope")
        else:
            print(f"  divergences   : {len(findings)}")
            for f in findings:
                print(f"      [{f['severity']:<21}] {f['kind']:<8} {f['what']}")
        print()
        if spoof:
            print("  *** SUBSTITUTION SIGNATURE ***")
            print("  The transcript claims an action the kernel never saw AND the kernel saw")
            print("  an action the transcript never mentions.  That pair is what issuing one")
            print("  command while running another looks like from outside the blast radius.")
            print("  A record written by the audited process cannot produce this finding about")
            print("  itself; it takes a second record the process cannot write.")
        elif findings:
            print("  The records diverge but not in the substitution pattern. Investigate;")
            print("  a scope that is too narrow or a tool mapping that is wrong both look")
            print("  like this, and both are worth fixing before drawing a conclusion.")

    if a.require_agreement and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

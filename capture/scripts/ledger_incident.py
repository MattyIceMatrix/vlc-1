#!/usr/bin/env python3
"""ledger_incident.py -- grade the invinoveritas 264-269 chain incident, pre-fix and
post-fix, and measure signed-head relay coverage, on top of a ledger_capture.py run.

Asked for by the operator (babyblueviper1) on vlc-1 PR #3, 2026-11-26:
  - score the live chain as it stands now;
  - grade the PRE-FIX state of forward-verdict entries 264-269, which were written
    outside the chain, because "a checker holding an earlier head should flag it";
  - grade the POST-FIX chain, which "should pass, with the backfill visible rather
    than hidden";
  - record the relay gap (heads on 2 of 6 relays, fixed in a3527263) as a coverage
    finding if the report format has room.

BLAST RADIUS: runs only on a GitHub-hosted runner, after capture/scripts/ledger_capture.py
in the same job. Reads $OUT/ledger (that run's output) and writes only $OUT/incident.
Sends no network requests of its own.

HONESTY NOTE, carried into every artefact this writes: the pre-fix state is a
RECONSTRUCTION, not a capture. The fix (f211fe9f, 2026-09-21) predates this project's
first fetch of the ledger (2026-09-30), so no pre-fix bytes were ever captured here.
What is reconstructed is derived from served data plus the operator's description, and
every file says so in its own provenance row.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "examples", "third-party",
                                "invinoveritas-ledger-live"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import verify_ledger as V            # noqa: E402
from conformance import check        # noqa: E402

LEDGER = os.path.join(os.environ["OUT"], "ledger")
OUT = os.path.join(os.environ["OUT"], "incident")
ADAPTER = os.path.join(HERE, "..", "..", "adapters", "invinoveritas-ledger-live.json")
os.makedirs(OUT, exist_ok=True)

INCIDENT = list(range(264, 270))     # the six forward-verdict entries written off-chain
# What the operator stated on vlc-1 PR #3, 2026-11-26, checked against what is served.
STATED = {"fix_commit": "f211fe9f", "fix_date": "2026-09-21",
          "relay_fix_commit": "a3527263",
          "source": "babyblueviper1, vlc-1 PR #3, 2026-11-26"}
STEPS = os.path.join(OUT, "steps.txt")

PROVENANCE = {
    "captured": ("Served by https://api.babyblueviper.com at this run's capture time and "
                 "recomputed on the runner; see ../ledger/."),
    "reconstructed": ("NOT CAPTURED. Derived on the runner from the served post-fix chain plus "
                      "the operator's description of the pre-fix state on vlc-1 PR #3 "
                      "(2026-11-26) and commit f211fe9f (2026-09-21). The fix predates this "
                      "project's first fetch of the ledger (2026-09-30), so no pre-fix bytes "
                      "exist in this repository and none are claimed to."),
}


def log(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    with open(STEPS, "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def write_jsonl(name, rows):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    return p


def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def grade(path, note, expect_root=None, expect_head=None):
    """One conformance verdict, with the anchors it was taken under."""
    rep = check(path, ADAPTER, expect_root=expect_root, expect_head=expect_head)
    failed = {k: v["note"] for k, v in rep["requirements"].items() if v["status"] != "PASS"}
    out = {
        "log": os.path.basename(path),
        "note": note,
        "anchors": {"expect_root": expect_root, "expect_head": expect_head},
        "structural_level": rep["structural_level"],
        "attested_level": rep["attested_level"],
        "adapter_sha256": rep["adapter_sha256"],
        "first_failures": dict(list(failed.items())[:4]),
        "report": rep,
    }
    log(f"  {os.path.basename(path):<34} {note[:42]:<42} "
        f"structural L{rep['structural_level']} / attested L{rep['attested_level']}")
    return out


def relink(rows, root):
    """Re-walk a run of chain rows from `root`, recomputing each head from the served
    content_hash and the recomputed predecessor. Content hashes are untouched."""
    out, prev = [], root
    for r in rows:
        ch = r["content_hash"]
        new = dict(r, prev_head_hash=prev, head_hash=V.link(ch, prev))
        out.append(new)
        prev = new["head_hash"]
    return out


def main():
    findings = []
    chain = sorted(read_jsonl(os.path.join(LEDGER, "chain.jsonl")), key=lambda r: r["entry"])
    full = read_jsonl(os.path.join(LEDGER, "ledger-live-full.jsonl"))
    recompute = {r["entry"]: r for r in read_jsonl(os.path.join(LEDGER, "recompute.jsonl"))}
    head_events = read_jsonl(os.path.join(LEDGER, "nostr-head-events.jsonl"))
    relay_summary = json.load(open(os.path.join(LEDGER, "nostr-summary.json"), encoding="utf-8"))
    index = json.load(open(os.path.join(LEDGER, "index-summary.json"), encoding="utf-8"))
    nums = [r["entry"] for r in chain]
    log(f"chain as served: {len(chain)} entries, {nums[0]}..{nums[-1]}")

    # ---------------------------------------------------------------- 1. as it stands
    log("current chain:")
    newest = [e for e in head_events if e.get("_valid") and e.get("_claim_head")]
    newest.sort(key=lambda e: (e.get("_claim_entry") or -1, e.get("created_at", 0)))
    signed_head = newest[-1]["_claim_head"] if newest else None
    signed_head_entry = newest[-1]["_claim_entry"] if newest else None
    grades = {
        "current_log_alone": grade(os.path.join(LEDGER, "ledger-live-full.jsonl"),
                                   "the live chain, no anchor held"),
    }
    if signed_head:
        grades["current_with_signed_head"] = grade(
            os.path.join(LEDGER, "ledger-live-full.jsonl"),
            f"the live chain against the signed head for entry {signed_head_entry}",
            expect_head=signed_head)
    else:
        findings.append({
            "id": "F-HEAD-NONE", "severity": "finding",
            "statement": "No valid signed head event was found on any relay queried in this run, "
                         "so VLC-L1-3 has no anchor to stand on and the chain can only be scored "
                         "on the log alone.",
        })

    # ------------------------------------------------- 2. the incident, reconstructed
    # Pre-fix: entries 264-269 are off-chain, so the chain stops at 263. The operator
    # states the head lookup would then have restarted the next entry at genesis.
    pre = [r for r in chain if r["entry"] < INCIDENT[0]]
    after = [r for r in chain if r["entry"] > INCIDENT[-1]]
    present = [n for n in INCIDENT if n in {r["entry"] for r in chain}]
    if len(present) != len(INCIDENT):
        findings.append({
            "id": "F-INCIDENT-ABSENT", "severity": "finding",
            "statement": f"Entries {INCIDENT[0]}-{INCIDENT[-1]} were described as chained by "
                         f"f211fe9f, but the served chain carries only {present}.",
        })
    if not after:
        findings.append({
            "id": "F-NO-SUCCESSOR", "severity": "note",
            "statement": f"No entry after {INCIDENT[-1]} is chained, so the silent-fork "
                         f"reconstruction has no successor entry to re-root; only the "
                         f"truncated pre-fix chain is graded.",
        })
    head_263 = pre[-1]["head_hash"] if pre else None

    marker = [r for r in full if r.get("class") == "chain-head"]
    forked = relink(after, V.GENESIS)        # the counterfactual: next entry back at genesis
    prov = {"class": "_provenance", "reconstructed": True, "note": PROVENANCE["reconstructed"]}

    p_whole = write_jsonl("prefix-whole.jsonl", pre + forked)
    p_fork = write_jsonl("prefix-forked-segment.jsonl", forked)
    p_post = write_jsonl("postfix.jsonl", chain + marker)
    for name, rows in (("prefix-whole", pre + forked), ("prefix-forked-segment", forked)):
        dump(f"{name}.provenance.json", dict(prov, log=f"{name}.jsonl", rows=len(rows),
                                             derived_from="../ledger/chain.jsonl",
                                             method="entries 264-269 removed from the chain; the "
                                                    "first entry after them re-rooted at "
                                                    "sha256('invinoveritas-ledger-genesis:before-"
                                                    "entry-40') and every later head recomputed "
                                                    "from its served content_hash"))
    dump("postfix.provenance.json", {"class": "_provenance", "reconstructed": False,
                                     "log": "postfix.jsonl", "rows": len(chain) + len(marker),
                                     "note": PROVENANCE["captured"]})

    log("the incident, pre-fix (RECONSTRUCTED):")
    grades["prefix_whole_log_alone"] = grade(
        p_whole, "pre-fix chain, both segments, no anchor held")
    grades["prefix_forked_segment_log_alone"] = grade(
        p_fork, "the forked segment alone, no anchor held -- the silent fork")
    if head_263:
        grades["prefix_forked_segment_against_earlier_head"] = grade(
            p_fork, f"the forked segment against the head held for entry {pre[-1]['entry']}",
            expect_root=head_263)
    log("the incident, post-fix (as served):")
    grades["postfix"] = grade(p_post, "the chain as served today, backfill included",
                              expect_head=signed_head)

    # Is the backfill visible rather than hidden? The capture records each entry's
    # chain_note / chain_backfilled_at as served.
    disclosure = {str(n): {
        "chain_backfilled_at": recompute.get(n, {}).get("chain_backfilled_at"),
        "chain_note": recompute.get(n, {}).get("chain_note"),
        "content_hash_matches_index": recompute.get(n, {}).get("content_hash_matches_index"),
        "head_recomputes": recompute.get(n, {}).get("head_recomputes"),
    } for n in INCIDENT}
    labelled = [n for n in INCIDENT
                if disclosure[str(n)]["chain_backfilled_at"] or disclosure[str(n)]["chain_note"]]
    unlabelled = [n for n in INCIDENT if n not in labelled]
    others = [r["entry"] for r in chain if r["entry"] not in INCIDENT
              and (recompute.get(r["entry"], {}).get("chain_backfilled_at")
                   or recompute.get(r["entry"], {}).get("chain_note"))]
    dump("backfill-disclosure.json", {
        "claim": "f211fe9f chained entries 264-269, labelled them as backfilled, and broadcast "
                 "their heads (operator, vlc-1 PR #3, 2026-11-26)",
        "entries_labelled_backfilled": labelled,
        "entries_not_labelled": unlabelled,
        "other_entries_carrying_a_backfill_label": others,
        "per_entry": disclosure,
        "reproduces_as_described": not unlabelled,
    })
    if unlabelled:
        findings.append({
            "id": "F-BACKFILL-UNLABELLED", "severity": "finding",
            "statement": f"Entries {unlabelled} are chained but carry neither chain_backfilled_at "
                         f"nor chain_note as served, so the backfill is not visible on them. The "
                         f"operator's description says all six were labelled.",
        })

    # ------------------------------- 2b. does the description reproduce in the served data?
    import datetime
    stamps = sorted(v["chain_backfilled_at"] for v in disclosure.values()
                    if isinstance(v["chain_backfilled_at"], int))
    served_days = sorted({datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
                          .strftime("%Y-%m-%d") for t in stamps})
    upstream_path = os.path.join(OUT, "upstream-%s.txt" % STATED["fix_commit"])
    upstream = open(upstream_path, encoding="utf-8").read() if os.path.exists(upstream_path) else ""
    fix_resolves = bool(upstream) and "Not a valid object name" not in upstream
    relay_fix_resolves = bool(re.search(r"^%s\w* " % STATED["relay_fix_commit"], upstream, re.M))
    described = {
        "source": STATED["source"],
        "stated_fix_commit": STATED["fix_commit"],
        "stated_fix_commit_resolves_in_public_repo": fix_resolves if upstream else None,
        "stated_relay_fix_commit": STATED["relay_fix_commit"],
        "stated_relay_fix_commit_resolves_in_public_repo": relay_fix_resolves if upstream else None,
        "stated_fix_date": STATED["fix_date"],
        "served_chain_backfilled_at_days": served_days,
        "served_chain_backfilled_at_utc": [datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
                                           .isoformat() for t in stamps],
        "effect_reproduces": not unlabelled and all(
            disclosure[str(n)]["head_recomputes"] for n in INCIDENT),
        "note": "The effect the operator described -- the six entries chained, labelled as "
                "backfilled, recomputing -- is checked against the served data. The commit "
                "reference and the date are checked against the public repository and the "
                "served chain_backfilled_at values.",
    }
    dump("described-vs-served.json", described)
    if upstream and not fix_resolves:
        findings.append({
            "id": "F-FIX-COMMIT-UNRESOLVED", "severity": "finding (citation, not chain)",
            "statement": f"The fix is cited as {STATED['fix_commit']}, which does not resolve in "
                         f"the public repository babyblueviper1/invinoveritas; "
                         f"{STATED['relay_fix_commit']}, cited for the relay widening in the same "
                         f"comment, does. The fix may live in a repository that is not public "
                         f"(the chain_note names ledger_forward_verdict.py, which is not in the "
                         f"public tree). The effect is checked against the served data "
                         f"separately and is not in question here; only the citation is.",
            "detail": "described-vs-served.json",
        })
    if served_days and STATED["fix_date"] not in served_days:
        findings.append({
            "id": "F-FIX-DATE-MISMATCH", "severity": "finding (description, not chain)",
            "statement": f"The fix is dated {STATED['fix_date']}, but every one of the six "
                         f"entries carries chain_backfilled_at on {', '.join(served_days)} "
                         f"({described['served_chain_backfilled_at_utc'][0]} to "
                         f"{described['served_chain_backfilled_at_utc'][-1]}), and their "
                         f"chain_note says 'chained late (2026-09-30)'. The served data is "
                         f"self-consistent; the date in the description is not what the ledger "
                         f"says. On the served dates the backfill landed roughly three quarters "
                         f"of an hour before this project's first fetch of the ledger, which "
                         f"matches 'found while preparing the earlier snapshot for you'.",
            "detail": "described-vs-served.json",
        })

    # ------------------------------------------------------- 3. relay coverage finding
    per_entry, relays_with_heads = {}, set()
    for ev in head_events:
        n, ok = ev.get("_claim_entry"), ev.get("_valid")
        rl = ev.get("_relays") or []
        relays_with_heads.update(rl)
        if n is None:
            continue
        slot = per_entry.setdefault(str(n), {"valid": False, "relays": []})
        slot["valid"] = slot["valid"] or bool(ok)
        slot["relays"] = sorted(set(slot["relays"]) | set(rl))
    queried = [u for u in relay_summary if u.startswith("wss://")]
    reachable = [u for u in queried if not relay_summary[u].get("error")]
    carrying = sorted(relays_with_heads)
    chained_entries = set(nums)
    claimed = {int(k) for k in per_entry if per_entry[k]["valid"]}
    covered = sorted(claimed & chained_entries)          # heads for entries the log chains
    outside = sorted(claimed - chained_entries)          # heads for entries it does not
    uncovered = sorted(chained_entries - claimed)
    coverage = {
        "requirement_context": "VLC-L1-3 / VLC-L5-1: the signed head is the only thing that "
                               "catches a consistently rewritten chain, so how many independent "
                               "relays carry it, and which entries it reaches, is the breadth of "
                               "that anchor.",
        "relays_queried": len(queried), "relays_reachable": len(reachable),
        "relays_carrying_a_head_event": len(carrying), "which": carrying,
        "unreachable": {u: relay_summary[u].get("error") for u in queried
                        if relay_summary[u].get("error")},
        "entries_in_chain": len(chained_entries),
        "chained_entries_with_a_valid_signed_head": covered,
        "chained_entries_without_one": len(uncovered),
        "valid_heads_for_entries_the_served_chain_does_not_chain": outside,
        "per_entry": per_entry,
        "prior_measurements": {
            "2026-09-30T13:43Z": "heads for entries 264-269 on 2 of 6 relays queried",
            "2026-09-30T18:52Z": "heads for entries 263-270 on 6 of 9 relays queried, after a3527263",
        },
        "fixed_in": "https://github.com/babyblueviper1/invinoveritas/commit/a3527263379ca627d4746055f48504cfd2668ae4",
    }
    dump("relay-coverage.json", coverage)
    findings.append({
        "id": "F-RELAY-COVERAGE",
        "severity": "coverage finding (not a chain defect)",
        "statement": f"Signed heads were found on {len(carrying)} of {len(queried)} relays "
                     f"queried ({len(reachable)} reachable), and they cover {len(covered)} of "
                     f"{len(chained_entries)} chained entries"
                     + (f" ({covered[0]}-{covered[-1]})" if covered else "")
                     + f"; {len(uncovered)} chained entries have no signed head on any relay "
                       f"queried. A head is the only anchor that catches a consistently "
                       f"rewritten chain, so a reader who holds no head for the range they care "
                       f"about has nothing to hold the chain to. The relay set itself is wider "
                       f"than it was: the gap the operator raised as fixed in a3527263 is "
                       f"measured here, not assumed.",
        "detail": "relay-coverage.json",
    })
    if outside:
        findings.append({
            "id": "F-HEADS-OUTSIDE-CHAIN",
            "severity": "finding",
            "statement": f"{len(outside)} valid signed head events on public relays -- same "
                         f"ledger key, same schema invinoveritas.ledger_chain_head.v1, same d-tag "
                         f"family -- claim entries {outside[0]}-{outside[-1]}, which the served "
                         f"ledger does not chain: chain_spec says the chain starts at entry 40 "
                         f"and GET /ledger carries chain blocks only from there. The head for "
                         f"entry {outside[0]} gives prev_head_hash as the published genesis "
                         f"constant, so on the relays alone those events read as a second chain "
                         f"rooted at the same genesis. They do not affect the grade below -- the "
                         f"chain 40-{max(chained_entries)} recomputes and matches the head for "
                         f"{max(chained_entries)} -- but a verifier that picks 'the newest signed "
                         f"head under this key and schema' can pick from the wrong series, which "
                         f"is the ambiguity the 264-269 incident was about, moved from the chain "
                         f"into the head namespace. Pinning the d tag, or putting a chain "
                         f"identifier in the signed content, would close it.",
            "detail": "relay-coverage.json",
        })
    log(f"relays: heads on {len(carrying)} of {len(queried)} queried; "
        f"{len(covered)} of {len(chained_entries)} chained entries covered; "
        f"{len(outside)} heads for entries not in the chain")

    # ------------------------------------------------------------------- 4. the verdict
    summary = {
        "produced_by": "capture/scripts/ledger_incident.py",
        "capture": {"fetched_at": index.get("fetched_at"),
                    "sha256_of_ledger_response": index.get("sha256_of_response"),
                    "entries_in_index": index.get("entries"),
                    "chained": len(chain), "range": [nums[0], nums[-1]]},
        "signed_head": {"entry": signed_head_entry, "head_hash": signed_head},
        "grades": {k: {"structural_level": v["structural_level"],
                       "attested_level": v["attested_level"],
                       "note": v["note"], "anchors": v["anchors"],
                       "first_failures": v["first_failures"]} for k, v in grades.items()},
        "incident": {
            "entries": INCIDENT,
            "state": "reconstructed, not captured",
            "provenance": PROVENANCE["reconstructed"],
            "earlier_head_held": {"entry": pre[-1]["entry"] if pre else None, "head_hash": head_263},
        },
        "findings": findings,
    }
    dump("grades.json", {k: v["report"] for k, v in grades.items()})
    dump("summary.json", summary)
    dump("findings.json", findings)
    log(f"findings: {[f['id'] for f in findings]}")


if __name__ == "__main__":
    main()

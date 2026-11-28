# Twenty years of major outages, replayed against VLC-1 (2006-2026)

**Everything on this page is SIMULATED and labelled as such.** Each major incident of
2006-2026 is replayed as its *characteristic failure class* -- event sequences reconstructed
from public postmortems and incident reports -- not as the vendor's actual systems. No vendor
data was used; no claim is made about what any vendor's internal logs contain. Two incidents
(the 2008 YouTube BGP hijack and the 2016 Dyn/Mirai DDoS) are external attacks, included as
the inverse case: proving an outage WAS external requires proving nothing internal changed.

**Method.** Every incident runs twice. First as the *legacy log* such systems typically keep
(plain JSONL, no binding -- `legacy-adapter.json`), alongside a *forged* variant carrying the
lie that incident makes tempting (the verdict deleted, the writers reordered, an internal
change planted during an attack, a fake AI-agent action inserted). Second, *instrumented*:
the same events through a producer that grades L4 -- the OCTA governance gateway's audit
chain (coverage declaration, per-record policy digest, chained + Ed25519-signed entries,
sealed chain-bound marker; the same producer as registry report 002 in
`VERIFIED-REPORTS.md`, here with throwaway simulation keys). Grades come from this
repository's reference checker.

**Re-verify on your machine** (standard library only):

```
python3 examples/outage-simulations-2006-2026/regrade.py
```

The committed trails under `trails/` are the full evidence: every legacy log, every forged
variant, every instrumented export with its marker. The signature-attack regrades reported
below mutate the instrumented trails in the stated way; the mutations are one-line edits you
can reproduce from the table.

## Scoreboard

| Incident | Legacy log | OCTA-instrumented | Signature attack | Result |
|---|---|---|---|---|
| YouTube BGP hijack via route leak (Feb 2008) | L0 (forgery indistinguishable) | structural L4 / attested L4 | frame an internal routing change | caught -> L0 |
| Facebook config feedback loop (Sep 2010) | L0 (forgery indistinguishable) | structural L4 / attested L4 | relabel the bad config as routine | caught -> L0 |
| AWS EBS re-mirroring storm (Apr 2011) | L0 (forgery indistinguishable) | structural L4 / attested L4 | remove the network change that started it | caught -> L0 |
| Azure leap-day certificate bug (Feb 29, 2012) | L0 (forgery indistinguishable) | structural L4 / attested L4 | hide the invalid cert validity | caught -> L0 |
| NYSE trading halt (Jul 2015) | L0 (forgery indistinguishable) | structural L4 / attested L4 | move the rollout weeks into the past | caught -> L0 |
| Dyn DNS / Mirai botnet DDoS (Oct 2016) | L0 (forgery indistinguishable) | structural L4 / attested L4 | plant an internal change during the attack | caught -> L0 |
| AWS S3 command typo (Feb 2017) | L0 (forgery indistinguishable) | structural L4 / attested L4 | make execution match authorization | caught -> L0 |
| GitHub split-brain (Oct 2018) | L0 (forgery indistinguishable) | structural L4 / attested L4 | erase the both-primaries divergence | caught -> L0 |
| Cloudflare WAF regex (Jul 2019) | L0 (forgery indistinguishable) | structural L4 / attested L4 | make the verdict disappear | caught -> L0 |
| Google auth quota incident (Dec 2020) | L0 (forgery indistinguishable) | structural L4 / attested L4 | soften what the automation reported | caught -> L0 |
| AWS Kinesis thread-limit outage (Nov 2020) | L0 (forgery indistinguishable) | structural L4 / attested L4 | remove the capacity change | caught -> L0 |
| Fastly global CDN outage (Jun 2021) | L0 (forgery indistinguishable) | structural L4 / attested L4 | delete the validation verdict | caught -> L0 |
| Facebook BGP withdrawal (Oct 2021) | L0 (forgery indistinguishable) | structural L4 / attested L4 | rewrite what the command was | caught -> L0 |
| AWS us-east-1 internal network cascade (Dec 2021) | L0 (forgery indistinguishable) | structural L4 / attested L4 | remove the scaling event that started it | caught -> L0 |
| Rogers nationwide outage, Canada (Jul 2022) | L0 (forgery indistinguishable) | structural L4 / attested L4 | blame a different change phase | caught -> L0 |
| Southwest crew-scheduling collapse (Dec 2022) | L0 (forgery indistinguishable) | structural L4 / attested L4 | falsify the overflow signal | caught -> L0 |
| FAA NOTAM failure (Jan 2023) | L0 (forgery indistinguishable) | structural L4 / attested L4 | delete the deletion event | caught -> L0 |
| Datadog multi-region outage (Mar 2023) | L0 (forgery indistinguishable) | structural L4 / attested L4 | rewrite which update channel fired | caught -> L0 |
| CrowdStrike channel file 291 (Jul 2024) | L0 (forgery indistinguishable) | structural L4 / attested L4 | make the verdict disappear | caught -> L0 |
| Google Cloud global outage (Jun 2025) | L0 (forgery indistinguishable) | structural L4 / attested L4 | relabel the policy change as routine | caught -> L0 |
| AWS us-east-1 DynamoDB DNS race (Oct 2025) | L0 (forgery indistinguishable) | structural L4 / attested L4 | flip the order of the two writers | caught -> L0 |
| Azure Front Door config bypass (Oct 2025) | L0 (forgery indistinguishable) | structural L4 / attested L4 | forge the verdict from FAILED to passed | caught -> L0 |
| Cloudflare bot-management feature file (Nov 2025) | L0 (forgery indistinguishable) | structural L4 / attested L4 | erase every bad-file publication | caught -> L0 |
| Microsoft 365 / Outlook gateway defect (Nov 2026) | L0 (forgery indistinguishable) | structural L4 / attested L4 | insert a fake AI-agent action | caught -> L0 |
| FAA nationwide ground stop (Nov 2026) | L0 (forgery indistinguishable) | structural L4 / attested L4 | truncate an evidence window | caught -> L0 |

## Headline numbers

- **25/25** legacy logs grade **L0** -- and in every single case the forged
  variant is *indistinguishable* from the honest one. The forensic question each recovery
  hinged on is unanswerable from the log those systems kept.
- **25/25** OCTA-instrumented trails grade **structural L4 / attested L4**
  on the public checker.
- **25/25** signature attacks against the instrumented trails are caught,
  collapsing the grade to L0 with a named requirement and reason.

## The AWS race, serialized (bulwark head-CAS pattern)

```
LEGACY (what happened 2025-10-20):
  EnactorA (delayed) writes plan-41 -> state := plan-41
  EnactorB writes plan-42 -> state := plan-42
  EnactorA cleanup (for plan-41) DELETES records plan-42 just wrote -> endpoint EMPTY, nobody notices

HEAD-CAS CHAINED LEDGER (bulwark pattern):
  EnactorB: applied "apply plan-42" -> head a65786
  EnactorA: REJECTED stale write ("apply plan-41") -- expected head 000000, actual a65786
```

## Per-incident findings

### YouTube BGP hijack via route leak (Feb 2008)
**Failure class:** EXTERNAL: foreign ISP announced a more-specific prefix; global blackhole

**The forensic question recovery hinged on:** Can you prove the outage was external -- that NOTHING internal changed?

- Legacy log: **L0** -- and the forged variant (frame an internal routing change style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *frame an internal routing change*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

### Facebook config feedback loop (Sep 2010)
**Failure class:** automated correction system turned one bad config value into a self-DDoS

**The forensic question recovery hinged on:** What did the automated repair system actually do, at what rate?

- Legacy log: **L0** -- and the forged variant (relabel bad config as routine style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *relabel the bad config as routine*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### AWS EBS re-mirroring storm (Apr 2011)
**Failure class:** network change shifted traffic onto a low-capacity path; storage fleet re-mirrored itself into exhaustion

**The forensic question recovery hinged on:** Which network change started it, and what did the fleet do in response?

- Legacy log: **L0** -- and the forged variant (remove network change that started it style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *remove the network change that started it*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Azure leap-day certificate bug (Feb 29, 2012)
**Failure class:** date arithmetic bug: certs issued Feb 29 valid to an invalid date; agent init failed fleet-wide

**The forensic question recovery hinged on:** Which certs were issued with the bad validity, and what did remediation touch?

- Legacy log: **L0** -- and the forged variant (hide invalid cert validity style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *hide the invalid cert validity*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### NYSE trading halt (Jul 2015)
**Failure class:** overnight software rollout left gateways misconfigured; ~4h halt

**The forensic question recovery hinged on:** Which rollout, applied when, left which gateways in which state?

- Legacy log: **L0** -- and the forged variant (move rollout weeks into past style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *move the rollout weeks into the past*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### Dyn DNS / Mirai botnet DDoS (Oct 2016)
**Failure class:** EXTERNAL ATTACK: IoT botnet flood -- the inverse proving-a-negative case

**The forensic question recovery hinged on:** Can you prove it WAS an attack -- that no internal change coincided?

- Legacy log: **L0** -- and the forged variant (plant an internal change during attack style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *plant an internal change during the attack*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

### AWS S3 command typo (Feb 2017)
**Failure class:** playbook command executed against a larger server set than intended

**The forensic question recovery hinged on:** What was authorized vs what actually executed? (verdict vs action)

- Legacy log: **L0** -- and the forged variant (make execution match authorization style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *make execution match authorization*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 2).

### GitHub split-brain (Oct 2018)
**Failure class:** 43-second partition; writes landed on two primaries; 24h reconciliation

**The forensic question recovery hinged on:** Which writes landed on which primary in what order? (serialization, again)

- Legacy log: **L0** -- and the forged variant (erase both-primaries divergence style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *erase the both-primaries divergence*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 3 does not link to its predecessor).

### Cloudflare WAF regex (Jul 2019)
**Failure class:** rule with catastrophic backtracking deployed globally in seconds, no staged rollout

**The forensic question recovery hinged on:** Did a verdict gate the rule, and under which policy did it ship everywhere at once?

- Legacy log: **L0** -- and the forged variant (make verdict disappear style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *make the verdict disappear*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Google auth quota incident (Dec 2020)
**Failure class:** quota automation reported zero usage for the identity service; auth denied globally

**The forensic question recovery hinged on:** What did the quota automation report and enforce, step by step?

- Legacy log: **L0** -- and the forged variant (soften what automation reported style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *soften what the automation reported*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### AWS Kinesis thread-limit outage (Nov 2020)
**Failure class:** capacity addition pushed front-end fleet past an OS thread limit

**The forensic question recovery hinged on:** Which capacity change crossed the limit, and what else depended on the fleet?

- Legacy log: **L0** -- and the forged variant (remove capacity change style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *remove the capacity change*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Fastly global CDN outage (Jun 2021)
**Failure class:** latent bug triggered by one customer config push

**The forensic question recovery hinged on:** Which config push triggered it, and what exactly did the rollout system do?

- Legacy log: **L0** -- and the forged variant (delete validation verdict style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *delete the validation verdict*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

### Facebook BGP withdrawal (Oct 2021)
**Failure class:** maintenance command the audit tool failed to stop; own tools unreachable

**The forensic question recovery hinged on:** What command ran, who issued it, and can anyone verify the trail with every internal system down?

- Legacy log: **L0** -- and the forged variant (rewrite what command was style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *rewrite what the command was*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 2).

### AWS us-east-1 internal network cascade (Dec 2021)
**Failure class:** automated scaling triggered unexpected cross-network surge

**The forensic question recovery hinged on:** What did the automation do in the minutes before the cascade?

- Legacy log: **L0** -- and the forged variant (remove scaling event that started it style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *remove the scaling event that started it*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Rogers nationwide outage, Canada (Jul 2022)
**Failure class:** config update deleted a routing filter; whole network, including own ops tools, down

**The forensic question recovery hinged on:** Which step of the planned change removed the filter?

- Legacy log: **L0** -- and the forged variant (blame a different change phase style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *blame a different change phase*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### Southwest crew-scheduling collapse (Dec 2022)
**Failure class:** ops volume exceeded system; work items silently lost

**The forensic question recovery hinged on:** How many crew reassignments were produced vs actually processed? (a literal completeness identity)

- Legacy log: **L0** -- and the forged variant (falsify overflow signal style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *falsify the overflow signal*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 3).

### FAA NOTAM failure (Jan 2023)
**Failure class:** files deleted during database sync; corruption reached the backup

**The forensic question recovery hinged on:** What was deleted, when, by whom -- and is the deletion accounted or silent?

- Legacy log: **L0** -- and the forged variant (delete deletion event style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *delete the deletion event*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

### Datadog multi-region outage (Mar 2023)
**Failure class:** automatic OS update rebooted fleet; which hosts, which update, unclear for hours

**The forensic question recovery hinged on:** Which update channel touched which hosts in what order?

- Legacy log: **L0** -- and the forged variant (rewrite which update channel fired style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *rewrite which update channel fired*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### CrowdStrike channel file 291 (Jul 2024)
**Failure class:** malformed content update passed its validator and shipped everywhere at once

**The forensic question recovery hinged on:** Which validation policy admitted the file, and did any gate actually run?

- Legacy log: **L0** -- and the forged variant (make verdict disappear style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *make the verdict disappear*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Google Cloud global outage (Jun 2025)
**Failure class:** quota policy config with blank fields propagated globally, crash-looped Service Control

**The forensic question recovery hinged on:** What did the policy in force actually say, and which checks admitted it?

- Legacy log: **L0** -- and the forged variant (relabel policy change as routine style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *relabel the policy change as routine*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 1).

### AWS us-east-1 DynamoDB DNS race (Oct 2025)
**Failure class:** two automation writers raced; cleanup deleted live DNS records

**The forensic question recovery hinged on:** Which writer applied which plan in what order? (serialization with receipts)

- Legacy log: **L0** -- and the forged variant (flip order of two writers style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *flip the order of the two writers*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 1 does not link to its predecessor).

### Azure Front Door config bypass (Oct 2025)
**Failure class:** invalid config bypassed validation via pipeline defect

**The forensic question recovery hinged on:** Did validation run on THIS change, under WHICH policy?

- Legacy log: **L0** -- and the forged variant (forge verdict from FAILED to passed style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *forge the verdict from FAILED to passed*: **CAUGHT, grade collapses to L0** (VLC-L1-1: binding broken at record 2).

### Cloudflare bot-management feature file (Nov 2025)
**Failure class:** good and bad config files propagating alternately; DDoS misdiagnosis

**The forensic question recovery hinged on:** Which file version was in force on which propagation cycle? (the flip-flop as a sequence)

- Legacy log: **L0** -- and the forged variant (erase every bad-file publication style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *erase every bad-file publication*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

### Microsoft 365 / Outlook gateway defect (Nov 2026)
**Failure class:** latent defect from a July fix surfaced months later; had to deny hack AND AI involvement

**The forensic question recovery hinged on:** Which past change is the landmine -- and can you PROVE no attacker and no AI agent acted?

- Legacy log: **L0** -- and the forged variant (insert a fake AI-agent action style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *insert a fake AI-agent action*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 3 does not link to its predecessor).

### FAA nationwide ground stop (Nov 2026)
**Failure class:** legacy telecom instability; weeks of investigation; had to deny cyberattack and new AI system

**The forensic question recovery hinged on:** Is the evidence pack complete enough that "no attack, not the AI" is arithmetic instead of assertion?

- Legacy log: **L0** -- and the forged variant (truncate an evidence window style) grades **identically**. The question above is unanswerable: two contradictory histories, both equally 'valid'.
- OCTA-instrumented: **structural L4 / attested L4** (chained, signed, policy-bound, sealed).
- Signature attack -- *truncate an evidence window*: **CAUGHT, grade collapses to L0** (VLC-L1-1: record 2 does not link to its predecessor).

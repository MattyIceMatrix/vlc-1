# Crosswalk: ISO/IEC 24970 and VLC-1 (informative)

**2026-09-30. Informative, not normative.** How a producer that logs according to
ISO/IEC 24970 (*Artificial intelligence — AI system logging*) would also
demonstrate completeness under VLC-1, and which question each VLC-1 level answers
about a 24970 log.

## Source limits, stated first

ISO/IEC 24970 is at **FDIS, stage 50.20** (ISO, 28 August 2026; ballot closing on or
about 23 October 2026). Its published scope reads: *"common capabilities,
requirements and a supporting information model for logging of events in AI
systems … designed to be used with a risk management system."* The FDIS text is
not public and has not been read for this document. What follows rests on:

- the ISO catalogue entry (title, scope, stage, 26 pages, JTC 1/SC 42);
- the committee draft reviewed for `SPEC.md` §0 (clause numbers and paraphrase
  only), which *"contains no requirement for completeness verification,
  dropped-event detection, buffer-overflow handling or gap accounting"*;
- public descriptions of that draft: risk as the primary driver for choosing which
  events to log (CD 7.1, with ISO/IEC 23894), technical documentation of the
  logging criteria, frequency and scope (CD 6.5), events for operation, automated
  monitoring and human oversight, and access control over who may read, write or
  delete logs;
- prEN 18229-1, which defers most of its logging content to 24970 (see
  `COMMENT-prEN-18229.md`).

**No FDIS clause number is cited below.** Where a row needs one, it says so. When
the standard is published, the right-hand column of each table gets its clause
reference, and any row the text contradicts is corrected or removed. That is the
whole of this document's claim to accuracy.

## The division of labour

VLC-1 `SPEC.md` §1.1 leaves *what events to log* to ISO/IEC 24970. The two answer
different questions about the same log:

| | ISO/IEC 24970 (as publicly described) | VLC-1 |
|---|---|---|
| Question | Which events should an AI system log, with what content, documented how? | Can a verifier holding only the delivered log show that nothing was removed, lost unannounced, never observed, or decided under undisclosed rules? |
| Basis | Risk management: the event set follows from the risk assessment | Evidence: each property is demonstrated by the log itself or by a stated, bounded attestation |
| Output | A log and its technical documentation | A level, L0 to L5, with the failed requirements named |

A producer conforming to both can make a claim neither lets it make alone: *the
events my risk assessment requires are logged, and the delivered log can be checked
to contain all of them.*

## Where each VLC-1 level attaches

| VLC-1 | What it asks of a 24970 log | Attachment point in 24970 | FDIS clause |
|---|---|---|---|
| **L1** tamper-evident (VLC-L1-1…4) | Records bound to their predecessors; an end marker naming the final head | Access control over who may write or delete logs (as described). Access control limits who can alter a log; L1 makes an alteration by anyone who could detectable afterwards | *pending* |
| **L2** loss-accounted (VLC-L2-1…6) | A monotonic count; every discard declared in-band; the completeness identity closes | None found in the committee draft reviewed: no dropped-event detection, overflow handling or gap accounting | *pending: does the FDIS add any?* |
| **L3** coverage-declared (VLC-L3-1…6) | The observation surface enumerated in the log, at start and on change | **The risk-based event list and the technical documentation of logging criteria and scope** (CD 7.1, CD 6.5). This is the enumeration L3 needs; 24970 puts it in documentation, VLC-1 asks for it in the log, bound by the same integrity mechanism (VLC-L3-2) | *pending* |
| **L4** policy-bound (VLC-L4-1…4) | Each decision bound to a digest of the exact policy applied | Events for automated monitoring and human oversight (as described) record *that* a decision happened; L4 records *under which rules* | *pending* |
| **L5** independently witnessed (VLC-L5-1…6) | The record held outside the audited process's control, with a declared boundary | Not addressed in the public descriptions | *pending* |

The L3 row is the strongest link. A 24970 producer already has to decide, from its
risk assessment, which events it logs and to document that decision. Writing the
same list into the log as a coverage declaration, and hashing it with the records,
turns a document an auditor has to trust into evidence the auditor can check.

## Writing a VLC-1 adapter for a 24970 log

A producer does not change its log format to be scored. It writes an adapter
(`adapters/*.json`), which is data:

| Adapter field | Taken from the 24970 side |
|---|---|
| `record_class_field` | the field that carries the event type in the 24970 information model |
| `coverage.mode: "enumerated"` and its surface list | the event types the risk assessment selected (technical documentation) |
| `integrity` | whatever binding the producer uses; `none` if it uses none, which scores L0 honestly |
| `loss` | the producer's drop counter, if it writes one into the log; `none` otherwise |
| `policy` | the digest of the monitoring or oversight rule set, if recorded per decision |
| `independence` | where the log is held relative to the AI system that writes it |

The 25 adapters in `adapters/`, for formats scored from public documentation and
from live captures, show the pattern (`THIRD-PARTY.md`).

## Questions the FDIS text would settle

Each is a clause lookup, not a matter of opinion:

1. Does the FDIS require any integrity binding between records, or only access control?
2. Does it require a record when events are dropped, or a count from which a drop can be detected?
3. Is the risk-based event list required in the log, or only in documentation?
4. Does the information model carry a per-record sequence number?
5. Does it address where the log is held relative to the system that writes it?

If the answer to any of these is yes, the matching row above moves from *attachment
point* to *direct correspondence*, and this crosswalk says so with the clause
number.

## Status and route

At FDIS the vote is yes or no, and technical comments cannot change the text
(`SPEC.md` Annex B). Completeness verification can enter ISO/IEC
24970 only through an amendment or a new work item under ISO/IEC JTC 1/SC 42. This
crosswalk is written so that it can serve as the basis for either, with
attribution and without permission (CC0, like the rest of the specification text).

## Sources

- ISO catalogue, ISO/IEC FDIS 24970: https://www.iso.org/standard/88723.html
- VDE, *EU AI Act: AI system logging*: https://www.vde.com/topics-en/artificial-intelligence/blog/eu-ai-act--ai-system-logging
- iTeh catalogue, prEN ISO/IEC 24970: https://standards.iteh.ai/catalog/standards/cen/38472bd6-ab5c-4908-ac64-6990f45027e6/pren-iso-iec-24970
- `SPEC.md` §0, §1.1, §1.2 and Annex B; `COMMENT-prEN-18229.md`

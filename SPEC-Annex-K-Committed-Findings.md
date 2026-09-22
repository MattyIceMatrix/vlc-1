# Annex K (normative) — Committed findings ledger

*Draft for insertion into `SPEC.md`. Additive: it removes no existing clause and
weakens no existing claim. It defines an OPTIONAL record type for evaluations and
the checks a verifier applies to it. Reference implementation: `findings.py`.
Worked example: `examples/findings/`.*

**Vendor neutrality.** This annex names no product and no vendor. Any party that
tests an AI system — an internal red team, a third-party evaluator, a peer lab,
a regulator's evaluation unit — can keep a ledger under it, and any party can
check one.

---

## K.1 What this annex is for

The levels in the body of this specification ask whether a log of what a system
*did* is complete. An evaluation raises a second question about the evaluator:
whether the findings it reports are all the findings it made, reported when it
made them.

Two failures are common and both are silent. A finding is made and never
disclosed, because it is embarrassing to the tester, the system's developer, or
both. Or it is disclosed late with a date that implies it was found late. Neither
leaves a trace in the report.

This annex closes both, without forcing early disclosure. At the moment of
discovery the tester records a **commitment**: a hash that binds the finding's
text, its severity class and its disclosure date, and reveals none of them except
the class and the date. The commitment is chained and anchored like any VLC-1 log.
From then on:

- the date of discovery cannot move;
- the severity class and due date recorded at discovery cannot be changed at
  disclosure;
- a finding that was committed and not disclosed by its due date is visible to
  anyone holding the ledger, as **overdue**, with its class;
- a finding cannot be quietly dropped: closing it requires either disclosure or
  a withdrawal that still opens the commitment.

## K.2 Terms

**Tester** — the party that makes findings.
**Subject** — the party whose system is tested.
**Finding document** — the tester's full text of one finding, as bytes.
**Nonce** — 32 bytes from a cryptographically secure random source, kept secret
by the tester until the finding is opened.
**Commitment** — `SHA-256(canon({v, finding_id, class, due, nonce, doc_sha256}))`,
where `doc_sha256` is the SHA-256 of the finding document.
**Opening** — the nonce and `doc_sha256`, published in a reveal or withdraw record.
**Anchor** — the hash of a ledger record, published by a party through a channel
independent of the ledger (§4, VLC-L1-1).

## K.3 Record format

A ledger is JSON Lines. Every record carries `v` (`"vlc1-findings-1"`), `seq`
(integer, from 0), `prev` (the previous record's `hash`; 64 zeros for the first),
`at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`), `kind`, `party`, `finding_id`, and `hash`.

| kind | additional fields |
|---|---|
| `commit` | `class` (`info`, `low`, `medium`, `high`, `critical`), `due` (`YYYY-MM-DD`), `commitment` |
| `defer` | `due` (later than the current due date), `reason` |
| `reveal` | `nonce`, `doc_sha256` |
| `withdraw` | `reason`, `nonce`, `doc_sha256` |

`hash = SHA-256(canon(record without "hash"))`. The link to the previous record is
inside the hashed body.

`canon` is sorted keys, no insignificant whitespace. Every string in a record
**SHALL** be ASCII; every number **SHALL** be an integer; member names **SHALL**
be unique. Over that domain `canon` is byte-identical to RFC 8785, so no
implementation needs a full JCS library to agree. Identifiers, parties and reasons
are 1–128 characters of `[A-Za-z0-9._:-]`.

The finding document itself is never in the ledger.

## K.4 Requirements

**VLC-K-1** Each record SHALL have exactly the fields of its kind, `seq` SHALL
equal its position, `prev` SHALL equal the previous record's `hash`, and `hash`
SHALL recompute. A document containing a duplicate member, a non-integer number
or a non-object line fails.

**VLC-K-2** `at` SHALL be non-decreasing along the ledger.

**VLC-K-3** Each `finding_id` SHALL be committed exactly once, before any other
record for it. After a reveal or withdraw no further record for that finding is
permitted. A defer SHALL move the due date strictly later.

**VLC-K-4** The opening in a reveal or withdraw record SHALL reproduce the
commitment, using the class and due date **as committed**, not as deferred. The
nonce SHALL be 32 bytes drawn from a cryptographically secure source; a verifier
cannot test this, which is why a low-entropy nonce is a producer failure rather
than a checkable one (see K.6).

**VLC-K-5** Where a revealed finding's document is supplied, its SHA-256 SHALL
equal the revealed `doc_sha256`.

**VLC-K-6** Where a party's anchor is supplied, it SHALL equal the hash of some
record in the ledger. The records up to that one are then fixed against rewrite
for that party. Where no anchor is supplied the verifier SHALL report VLC-K-6 as
not tested, never as passed.

## K.5 What a verifier reports

Pass or fail on VLC-K-1 to VLC-K-6, and separately, as of a stated date:

- each finding's class, current due date, number of deferrals, and status:
  **open**, **overdue** (open past its due date), **revealed** or **withdrawn**;
- for each party that supplied an anchor, the last record it fixes, and the
  number of records after the latest record *every* supplying party has fixed
  (the unanchored tail).

Overdue is a status, not a conformance failure. A ledger with an overdue
critical finding is a conformant ledger that is telling the truth about an
undisclosed critical finding. That is the point of it.

## K.6 What this annex does not establish

It does not show that every finding was committed. A tester that never records a
finding leaves no trace; this annex makes omission *at the time of discovery* the
only remaining way to hide one, and moves it from a later editorial decision to
an earlier deliberate act. Evidence about what the tester observed — the logs of
the evaluation itself, under the body of this specification — is what bears on
that question.

It does not show that the finding is correct, significant, or correctly
classed. It shows that it was recorded, when, and with what class.

It does not prevent collusion. A tester and subject who agree to omit a finding
can both omit it.

It does not protect a low-entropy finding with a weak nonce. A commitment over a
short, guessable document with a predictable nonce can be opened by trial. The
reference producer draws every nonce from the operating system's CSPRNG.

Anchors bind only if they were published where the party could not later change
them. An anchor supplied by the same party that supplies the ledger, through the
same channel, adds nothing (§4).

## K.7 Two-party use

When a tester and a subject each anchor the same ledger at intervals, neither can
rewrite the records the other has anchored. The subject's anchors also show that
it saw each commitment, which removes the later claim that a finding was never
reported to it. The worked example has the subject anchor after the third
commitment and the tester anchor after disclosure.

## K.8 Relationship to other work

Commit-then-reveal is old and well understood; the novelty here is none. This
annex fixes one record format and one set of checks so that ledgers from
different testers can be checked by the same tool. Where a transparency service
such as an IETF SCITT deployment is available, each ledger record or its hash can
be registered as a signed statement there; the anchor in K.4 is then the
service's receipt.

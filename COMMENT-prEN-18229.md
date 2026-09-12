# Comment submission — verifiable log completeness

**Target documents**

| | |
|---|---|
| **prEN 18229-3** *Transparency and human oversight* | public enquiry **open until 22 September 2026** — the live window |
| **prEN 18229-1** *AI system logging* | enquiry closed; **comment disposition in progress** — a technical comment with a working implementation still carries weight at disposition |
| **ISO/IEC FDIS 24970** *AI system logging* | FDIS; too late for the base text. Route is an amendment or NWIP via ISO/IEC JTC 1/SC 42, US TAG = INCITS/AI |

**Submitter.** Independent contributor. Route: national standards body for the
CEN-CENELEC parts; INCITS/AI for the SC 42 part.

**Backing implementation.** Every claim below is exhibited by running code in a
public tree: a specification (`completeness/SPEC.md`), a vendor-neutral
conformance checker with adapters for producers the submitter did not write, six
worked example logs, a machine-checked Coq development
(`proofs/sentinel_completeness.v`, 0 admitted, 0 axioms), and a self-test that
fails in both directions. **Conflict of interest is declared in Annex C of the
specification and repeated here: the submitter builds a product that implements
the proposed requirement.** The proposal is drafted to be met at the application
layer by any vendor, and the checker's first act was to report the submitter's
own implementation two levels below its claim.

---

## 1. The comment, in one paragraph

Both logging documents specify **what to record**. Neither specifies **how a
reader establishes that the record is all of it.** The consequence is
demonstrable and not hypothetical: an evidence export covering a two-hour outage
during which the logging path discarded every event is indistinguishable, by
every check the drafts require, from an export covering a quiet afternoon. Under
Article 12 the log is the artefact the obligation produces; under Article 19 it
is retained; under the drafts as they stand, its silence carries no meaning. One
short normative clause fixes this, is implementable at any layer, and is
testable.

---

## 2. Comments in CEN/ISO template form

### prEN 18229-1 (at disposition)

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
| — | General | **ge** | The draft states the purposes of logging and defers event content to ISO/IEC 24970. Completeness is a property of the *log*, not of an *event*, and therefore falls into the gap between the two documents: neither addresses it. A conformant implementation may discard an arbitrary fraction of events and produce a log indistinguishable from one that discarded none. | Add a normative clause on demonstrable completeness. Proposed text at §3 below. |
| — | General | **te** | No requirement addresses dropped events, buffer-exhaustion behaviour, or gap accounting. Bounded buffers are universal in production logging; silent discard under load is the normal failure, and it occurs preferentially during incidents — exactly the intervals the log exists to cover. | Require in-band, integrity-bound declaration of discarded records, and a stated overflow behaviour. See §3, requirement (b). |
| — | General | **te** | No requirement addresses the *observation surface*. Where a producer is not attached to a source, activity at that source generates no event, therefore no loss, therefore no gap: the log is complete with respect to what was watched and silent about what was not, with nothing marking the difference. This failure is invisible to every integrity and accounting mechanism and, to the submitter's knowledge, is not named in any published AI logging standard or draft. | Require the log to enumerate the observation surface. See §3, requirement (c). This is the load-bearing comment. |
| — | General | **te** | No requirement binds recorded verdicts to the decision rules in force when they were made. A recorded "permitted" is re-readable under any later policy. | See §3, requirement (d). |
| — | General | **ed** | The draft uses "logging" for both the act of recording and the resulting artefact. The requirements proposed here are about the artefact and the distinction should be made explicit. | Define "log record", "delivered log" and "observation surface". |

### prEN 18229-3 (enquiry open to 22 September 2026)

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
| — | General | **ge** | Human oversight is exercised **through** logs. An oversight function reading a log that cannot distinguish "no anomalies occurred" from "the recording path was down" is not exercising oversight; it is being shown a clean screen. The draft's oversight requirements presuppose an evidentiary property that no part of the 18229 series requires. | Add a requirement that information presented to an oversight function carries the completeness status of its underlying log, and that an incomplete or undeclared-coverage interval is **surfaced to the human, not smoothed over**. |
| — | General | **te** | Transparency obligations toward deployers and affected persons are undermined if the record's silence is uninterpretable. A transparency artefact derived from an incomplete log inherits the incompleteness and currently inherits no marking of it. | Require that any artefact derived from a log propagate the log's completeness declaration. |

---

## 3. Proposed normative text

Offered as drafting material, to be cut down freely. Requirement identifiers are
the submitter's and are not proposed for adoption.

> **X.1 Completeness of the log**
>
> **X.1.1** The provider shall ensure that the log enables a reader to determine
> whether records generated by the logging function were not delivered to the
> log.
>
> **X.1.2 (integrity)** Records shall be bound such that alteration, reordering,
> insertion, removal or truncation of delivered records is detectable by a party
> holding only the log and published parameters, using a documented,
> independently recomputable mechanism.
>
> **X.1.3 (loss accounting)** Where a record generated by the logging function is
> discarded before delivery, the log shall contain a declaration of the number of
> records discarded and the interval in which the discard occurred. The
> declaration shall be subject to X.1.2. The provider shall state the behaviour
> of the logging path when its capacity is exhausted. A logging function that
> cannot detect discard shall declare that it cannot.
>
> **X.1.4 (coverage)** The log shall contain an enumeration of the sources from
> which the logging function was capable of generating records during the logged
> interval, distinguishing sources attached, sources that could not be attached,
> and sources excluded by design with the reason for exclusion; together with the
> basis on which the enumeration is asserted to be exhaustive. The enumeration
> shall be subject to X.1.2, and shall be re-emitted whenever the set changes.
>
> **X.1.5 (policy binding)** Where a record asserts a verdict, classification or
> other outcome determined by configurable rules, the log shall be bound to an
> identifier of the exact rules in force, and a change of rules during the logged
> interval shall itself be recorded.
>
> **X.1.6 (declaration)** The provider shall declare which of X.1.2 to X.1.5 the
> logging function satisfies. Conformance to X.1.2 alone shall not be described
> as, or presented as evidence of, completeness.
>
> NOTE 1 X.1.3 does not require guaranteed delivery. Loss under load is
> permitted; undeclared loss is not.
>
> NOTE 2 X.1.4 is satisfiable at any layer. For a logging function integrated in
> an application, the enumeration is the set of instrumented call sites or
> routes; for one integrated in a gateway, the set of terminated endpoints.

**X.1.6 is the clause that changes behaviour in the market.** X.1.2 alone is what
is universally shipped today and is universally described as making logs
"tamper-proof" and "audit-ready"; forbidding that description where X.1.3 and
X.1.4 are unmet is most of the work.

---

## 4. Why the submitter believes X.1.4 cannot be dropped as an optimisation

X.1.4 is the unusual requirement and will attract the most resistance, so the
argument is stated formally rather than rhetorically.

Model a logged session as: the events that occurred, the subset of sources the
producer was attached to, and the records the transport discarded. Consider two
sessions:

- **A** — one event occurred, at a source the producer watched. Nothing was lost.
- **B** — two events occurred; the producer watched one source and not the other.
  Nothing was lost.

A and B deliver **identical** record sets and **identical** loss declarations —
zero, in both cases, correctly. B is missing an event outright.

`loss_accounting_is_blind_to_an_unhooked_source` in
`proofs/sentinel_completeness.v` states this as: *for every function V of the
delivered records and the loss declarations, V(A) = V(B).* The proof is trivial —
the inputs are equal — and that is exactly the point. **No verifier, however
sophisticated, can separate them.** A requirement on the records cannot fix it;
only a statement about the surface can, and
`the_coverage_declaration_separates_them` exhibits the function that does.

The corresponding runnable demonstration is `completeness/examples/`
`L2-looks-complete.jsonl` and `L3-coverage.jsonl`: the same session, both with
valid chains and closing identities, differing in one record, where one of them is
missing 58 inferences.

---

## 5. Testability

Every proposed requirement has a test that fails in both directions, set out in
Annex A of `completeness/SPEC.md`. The one that matters for X.1.4:

> Mutate the producer to declare a source it does not attach; the coverage test
> must detect it.

Without that negative control a coverage declaration is a list, and the
requirement rewards writing a longer one. The submitter's implementation of this
control is `sensor/openat2-coverage.sh`, and it is the reason X.1.4 is proposed as
testable rather than aspirational.

---

## 6. Relationship to existing work

RFC 9162 (Certificate Transparency), RFC 5848 (signed syslog), forward-integrity
audit logs and WORM/object-lock storage all solve X.1.2 thoroughly and none of
them addresses X.1.3 or X.1.4. The closest existing practice is OpenTelemetry's
dropped-span counters, which are a genuine loss-accounting primitive but travel on
a separate metrics path, are not bound to the trace data, and disappear if the
metrics path is the one that failed. Linux `auditd` carries an in-band `lost`
counter that is not integrity-bound. Nothing found by the submitter as of
2026-09-12 implements X.1.4.

This is offered as evidence that X.1.3 and X.1.4 are not already covered
elsewhere by another name, and as an invitation to be corrected.

---

## 7. Caveat on sources

The readings of prEN 18229-1 and ISO/IEC FDIS 24970 above are from published
drafts and specialist commentary, not from committee documents. Before this is
filed, both must be read in full through a national standards body, and every
"no requirement addresses X" statement above must be re-checked against the
actual text and withdrawn if wrong. **A comment that mischaracterises the draft is
worse than no comment**, and the submitter would rather find that out privately.

---

*Specification, checker, examples, proof and self-test:
`completeness/` and `proofs/sentinel_completeness.v`. Published without
restriction — clauses may be lifted into a standard with attribution and without
permission.*

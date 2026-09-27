# Comment submission — verifiable log completeness

**Target documents**

*Status as at 2026-09-27. Every date below must be re-confirmed with the national
standards body before filing; enquiry windows move and this file has already been
wrong once.*

| | |
|---|---|
| **prEN 18229-1** *AI system logging* | enquiry closed; **comment disposition in progress** — a technical comment with a working implementation still carries weight at disposition, and this is the part the proposal is aimed at |
| **prEN 18229-3** *Transparency and human oversight* | enquiry closed 22 September 2026; at disposition |
| **ISO/IEC FDIS 24970** *AI system logging* | FDIS; too late for the base text. Route is an amendment or NWIP via ISO/IEC JTC 1/SC 42, US TAG = INCITS/AI |
| **Official Journal** | no JTC 21 deliverable is cited, so **no standard yet confers a presumption of conformity** under Article 40. CEN-CENELEC targets Q4 2026 for the prioritised parts; M/613 runs to 28 February 2027 |

**The deferral is the window, not the excuse.** The Digital Omnibus moved Articles
9–15 to 2 December 2027 for Annex III standalone systems and 2 August 2028 for
Annex I embedded systems. The obvious reading is that the urgency has gone. The
submitter's reading is the opposite: the obligation this part serves does not bite
for fourteen months, no text is yet frozen in the Official Journal, and the
mechanism proposed below is therefore still addable at ordinary cost. After
citation it becomes an amendment, which is a different and much slower thing. If
the completeness mechanism is going to be in the European logging standard at all,
this is the cheapest moment it will ever have.

**Submitter.** Matthew Moore, independent contributor. Route: national standards
body for the CEN-CENELEC parts; INCITS/AI for the SC 42 part.

**Citable reference for everything below**

> Moore, Matthew (2026). *VLC-1: Verifiable Completeness for AI System Logs*.
> Zenodo. **https://doi.org/10.5281/zenodo.22728393**

That is the **concept DOI**: it always resolves to the current version, so this
comment does not go stale when the specification is revised. Clause numbers cited
below are stable across revisions. Where a reader needs to pin the exact text a
clause number referred to, **Annex F of `SPEC.md` is the revision history**, with
a version DOI for every published version.

The repository is at <https://github.com/MattyIceMatrix/vlc-1> and the
specification text is dedicated to the public domain under CC0, so a committee
may lift clauses from it verbatim, with attribution appreciated and not
required.

**Backing implementation.** Every claim below is exhibited by running code in a
public, archived tree: a specification (`SPEC.md`), an adapter-driven conformance
checker that reports separately what it recomputed and what it relayed with adapters for producers the submitter did not write, worked example
logs at every conformance level, a machine-checked Coq development
(`proofs/sentinel_completeness.v`, 0 admitted, 0 axioms), and a self-test that
fails in both directions. **Conflict of interest is declared in Annex C of the
specification and repeated here: the submitter builds a product that implements
the proposed requirement.** The proposal is drafted to be met at the application
layer by any vendor, and the checker's first act was to report the submitter's
own implementation two levels below its claim.

---

## 1. The comment, in one paragraph

Both logging documents specify **what to record**, and prEN 18229-1 is not
silent on the vocabulary: it defines **integrity** as the "property of accuracy
and completeness" (ISO/IEC 27000:2018, 3.36), defines traceability, and requires
the technical capability to record events automatically throughout the life
cycle. **The gap is not the term; it is the mechanism.** The submitter has not
been able to read either document in full and therefore asserts nothing about
their contents. Every item below is put as a question the committee can settle
from the text in front of it: is there a provision by which a reader of the
delivered log can distinguish undeclared transport loss from a genuinely
uneventful interval, or establish which sources were capable of producing a
record at all? If there is, a clause reference in reply closes the matter and
the submitter withdraws the corresponding item with thanks. The
consequence is
demonstrable and not hypothetical: an evidence export covering a two-hour outage
during which the logging path discarded every event is indistinguishable, by
integrity checking alone, from an export covering a quiet afternoon. Under
Article 12 the log is the artefact the obligation produces; under Article 19 it
is retained. **Unless some provision gives that silence a meaning, it has
none.** One short normative clause supplies it, is implementable at any layer,
and is testable.

---

## 2. Comments in CEN/ISO template form

### prEN 18229-1 (at disposition)

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
| — | General | **ge** | Integrity is understood as the property of accuracy and completeness (ISO/IEC 27000:2018, 3.36). **Question: which provision makes that property demonstrable from the delivered log?** Completeness is a property of the *log*, not of an *event*, so it may fall between this document and ISO/IEC 24970, to which event content is understood to be deferred. If no provision does, then a conformant implementation may discard an arbitrary fraction of events and produce a log indistinguishable from one that discarded none while satisfying the definition. | Add a normative clause making the property demonstrable. Proposed text at §3 below. The submitter's position is that the definition is right and a mechanism is needed, not that the definition is absent. |
| — | General | **te** | **Question: which requirement addresses dropped events, buffer-exhaustion behaviour, or gap accounting?** Bounded buffers are universal in production logging; silent discard under load is the normal failure, and it occurs preferentially during incidents — exactly the intervals the log exists to cover. A log that cannot declare its own discard cannot be distinguished from one that had nothing to declare. | If none does: require in-band, integrity-bound declaration of discarded records, and a stated overflow behaviour. See §3, requirement (b). |
| — | General | **te** | **Question: which requirement addresses the *observation surface* — the set of sources the logging function was capable of recording from?** Where a producer is not attached to a source, activity at that source generates no event, therefore no loss, therefore no gap: the log is complete with respect to what was watched and silent about what was not, with nothing marking the difference. This failure is invisible to every integrity and accounting mechanism, and the submitter has not found it named in any published AI logging standard. | If none does: require the log to enumerate the observation surface. See §3, requirement (c). This is the load-bearing comment, and the one the submitter most wants to be wrong about. |
| — | General | **te** | **Question: which requirement binds a recorded verdict to the decision rules in force when it was made?** Absent such a binding, a recorded "permitted" is re-readable under any later policy. | If none does: see §3, requirement (d). |
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
> **X.1.7 (what the reader established, and what was asserted)** Where
> conformance to any of X.1.2 to X.1.5 is established by a statement from the
> provider rather than by inspection of the log, that shall be distinguishable in
> the conformance record. A conformity assessment that does not separate what was
> recomputed from what was asserted does not establish what it appears to.

NOTE on X.1.7 — this clause was added after external review of the submitter's
own conformance checker found that it presented provider-supplied assertions as
independently demonstrated. The criticism was correct and the checker was
changed. The submitter raises it here because the same failure is available to
any conformity assessment scheme built on this part, and it is cheaper to
require the distinction than to discover it later.
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

The corresponding runnable demonstration is `examples/`
`L2-looks-complete.jsonl` and `L3-coverage.jsonl`: the same session, both with
valid chains and closing identities, differing in one record, where one of them is
missing 58 inferences.

---

## 5. Testability

Every proposed requirement has a test that fails in both directions, set out in
Annex A of `SPEC.md`. The one that matters for X.1.4:

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
them addresses X.1.3 or X.1.4.

**The agent layer, added 2026-09-27.** Since this comment was first drafted, the
gap has acquired its most consequential instance. Nearly every agent tool call in
production now travels over the Model Context Protocol, and the transcript of
those calls is the log that agentic governance products deliver as evidence. MCP
is JSON-RPC 2.0: the `id` correlates a request with its response, is assigned per
connection, and is not an ordinal over a delivered file — so a call that was never
recorded leaves no hole. There is no integrity field, no record counter, and no
requirement to state which servers were connected or which tools they exposed.
NSA's *Model Context Protocol (MCP): Security Considerations* (June 2026) names
**"poor or missing audit logs"** as a risk and recommends recording every tool and
model invocation with its parameters, the identities involved and hashes of
results. It specifies no mechanism for integrity, for discard, or for coverage. A
signals-intelligence agency has therefore identified the risk in the same terms as
this comment and stopped one step short of the requirement, which the submitter
offers as evidence that the requirement is the missing piece rather than an
idiosyncratic preoccupation.

`adapters/mcp-toolcall.json` scores the format at **L0**, and
`examples/third-party/mcp-toolcall.jsonl` and `-partial-host.jsonl` are the same
agent session recorded by two differently-configured hosts. One omits an outbound
POST to a partner API and an outbound email. The surviving ids run 3, 4, 5 with no
gap. **The two logs are indistinguishable by every check either draft requires.**
This is X.1.4 in a production protocol rather than in a model.

**Enforcement is not evidence.** Kernel-level agent containment shipped during
2026 — eBPF LSM taint propagation, per-process egress filtering, credential
surrogation — and it is genuinely the strongest independence position in the
field, because the kernel observes and the audited process cannot forge the
observation. None of the published architectures the submitter has found emits a
record that accounts for its own discard or declares the surface it was attached
to. The critical literature on that layer argues about semantics: that the kernel
sees a connection opened but not that the connection exfiltrates. It does not
reach the prior question of whether the sensor received everything it was attached
for. The submitter's own sensor answered that question wrongly on a real kernel —
it attached fifteen hooks, received events from one, and declared the full surface
covered — which is why X.1.4 is proposed with a negative control attached rather
than as a statement of good intent. The closest existing practice is OpenTelemetry's
dropped-span counters, which are a genuine loss-accounting primitive but travel on
a separate metrics path, are not bound to the trace data, and disappear if the
metrics path is the one that failed. Linux `auditd` carries an in-band `lost`
counter that is not integrity-bound. Nothing found by the submitter as of
2026-09-12 implements X.1.4.

This is offered as evidence that X.1.3 and X.1.4 are not already covered
elsewhere by another name, and as an invitation to be corrected.

---

## 7. What the submitter has and has not read

**The submitter has not read either document in full**, and this comment is
written so that it does not need to. Both are behind a paywall; the readings
that informed it come from published abstracts, scope statements, specialist
commentary and third parties' published comments, not from the committee text.

Every item in §2 is therefore framed as a **question**, not a finding. Where a
provision already exists, a clause reference in reply settles it and the
submitter withdraws that item — gladly, because a requirement already in the
draft is a better outcome than one that has to be added.

What does **not** depend on reading the drafts, and is offered on its own terms:

- the proposed normative text at §3, which stands as drafting material whatever
  the current text says;
- the impossibility result at §4, which is a statement about logs in general and
  is machine-checked, not asserted;
- the testability requirement at §5, including the negative control without
  which a coverage declaration is only a list;
- the survey at §6 of what existing work does and does not cover, which is drawn
  from published specifications the submitter has read in full.

**A comment that mischaracterises a draft is worse than no comment.** That
principle is why this one asks rather than states.

---

*Specification, checker, examples, proof, witness reconciler and self-test are
archived at **https://doi.org/10.5281/zenodo.22728393** and developed at
<https://github.com/MattyIceMatrix/vlc-1>. Published without restriction —
clauses may be lifted into a standard with attribution and without permission.*

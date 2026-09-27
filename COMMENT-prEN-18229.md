# Comment submission — verifiable log completeness

**Target documents**

*Status as at 2026-09-27. Every date below must be re-confirmed with the national
standards body before filing; enquiry windows move and this file has already been
wrong once.*

| | |
|---|---|
| **prEN 18229-1** *AI trustworthiness framework — Part 1: Logging* | CEN enquiry closed 20 August 2026; **at disposition of comments**. **Read in full for this revision** (May 2026 draft, 21 pages, via a national adoption). CEN/CENELEC approved direct publication after a positive enquiry for JTC 21 items in October 2025, so there may be no Formal Vote round: disposition should be treated as the last window, and it is reachable only through a national body or a WG 4 expert |
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

**This draft already requires completeness. It provides no way to demonstrate
it.** That is the whole comment, and it is narrower and better founded than the
version this file carried before the draft was read.

The vocabulary is in place. **3.2.9** defines *integrity* as the property of
accuracy and completeness, sourced to ISO/IEC 27000:2018, 3.36. **3.2.10**
defines *traceability*, and its Note 2 puts the Article 12 reading plainly: the
ability to reconstruct, from the automatically generated logs, a sufficient
account of how the system was functioning for a competent authority or the
provider to verify conformity. **5.2.1** requires the technical capability to
record events automatically across the life cycle. And **5.2.2 c)** requires the
provider to ensure that logged information has the detail *and completeness*
needed to support regulatory requirements.

So the obligation exists. What does not exist is any means by which a reader
holding the delivered log can tell whether it was met. Three specific gaps, each
evidenced below with a clause reference:

- **Loss.** No provision anywhere addresses discarded records, exhausted
  buffers, or accounting for a gap. The nearest text, **6.2.1 c) 3)**, requires
  the *instructions for use* to state the conditions under which logs may be
  overwritten, archived or deleted — a policy disclosed to the deployer in a
  document, not a record of what was actually lost.
- **Observation surface.** **6.2.1 a)** does require a description of what
  events the system logs — and puts it in the instructions for use rather than
  in the log. A coverage statement that lives outside the log is not bound to
  it, cannot be checked by a reader holding it, and can drift from it silently.
- **Policy binding.** **5.2.3** binds a log to the *system version*, which is
  real and useful. Nothing binds an individual record to the decision rules in
  force when it was produced.

The consequence is demonstrable, not hypothetical: an evidence export covering a
two-hour outage during which the logging path discarded every event is
indistinguishable, by integrity checking alone, from an export covering a quiet
afternoon. Both satisfy 5.2.2 c) as written, because nothing in the document
tells a reader how to find out. Under Article 12 the log is the artefact the
obligation produces; under Article 19 it is retained. **Unless some provision
gives that silence a meaning, it has none.** One short normative clause supplies
it, is implementable at any layer, and is testable.

---

## 2. Comments in CEN/ISO template form

### prEN 18229-1 (at disposition)

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
| — | 5.2.2 c), 3.2.9 | **ge** | 5.2.2 c) requires the provider to ensure logged information has the detail and completeness needed for regulatory requirements, and 3.2.9 defines integrity to include completeness. **No provision makes either demonstrable from the delivered log.** A conformant implementation may therefore discard an arbitrary fraction of events and produce a log indistinguishable from one that discarded none, while satisfying 5.2.2 c) as written, because the document supplies no method by which anyone — provider, deployer, notified body or authority — could establish the difference. The requirement is present and unfalsifiable. | Add a normative clause making the property demonstrable from the log. Proposed text at §3. The submitter's position is that 5.2.2 c) is *correct* and needs a mechanism, not that it is missing. |
| — | 5.4, 6.2.1 c) 3) | **te** | **No provision addresses discarded records, exhausted buffers, or accounting for a gap.** A search of the full text returns no occurrence of *discard*, *drop*, *lost*, *loss*, *overflow*, *buffer*, *queue*, *backpressure*, *truncate*, *exhaust* or *capacity*. The nearest text is 6.2.1 c) 3), which requires the instructions for use to state the conditions under which logs may be overwritten, archived or deleted — a disclosed retention policy, not a record of what was actually lost. Bounded buffers are universal in production logging; silent discard under load is the normal failure and occurs preferentially during incidents, which are exactly the intervals the log exists to cover. | Require in-band, integrity-bound declaration of discarded records and a stated behaviour on capacity exhaustion. See §3, requirement (b). The natural home is 5.4, alongside the storage and retention requirements. |
| — | 6.2.1 a), 5.3.1 | **te** | **The observation surface is required to be described, and the description is placed outside the log.** 6.2.1 a) requires the instructions for use to describe what events the system logs; 5.3.1 speaks of comprehensive event identification coverage as a design activity. Neither puts the resulting statement in the log. A coverage statement held in a separate document is not bound to the log, cannot be checked by a reader holding only the log, and can drift from it without either artefact becoming self-inconsistent. Where a producer is not attached to a source, activity at that source generates no event, therefore no loss, therefore no gap — the log is complete with respect to what was watched and silent about what was not, and nothing marks the difference. | Require the log itself to carry the observation surface it was recorded against, and require the declaration to be testable in both directions (see §5). This does not replace 6.2.1 a); it binds it to the artefact. **This is the load-bearing comment.** |
| — | 5.2.3, 5.5.4 c) | **te** | 5.2.3 requires a log to be linkable to the system version and the conformity-assessed version, which is the right instinct and genuinely useful. 5.5.4 c) requires configuration changes to be logged. **Neither binds an individual record to the decision rules in force when that record was produced.** A recorded outcome is therefore re-readable under any later configuration, and an audit answering "was this action compliant?" cannot answer "under which version of the rules?" from the log. | Extend 5.2.3 so that a record carries, or is bound to, a digest of the configuration in force at the time it was produced. See §3, requirement (d). |
| — | 5.4.1, 5.4.3, 5.5.2–5.5.6, 6.1 | **te** | **This part defers most substantive content to FprEN ISO/IEC 24970, which is at FDIS and can no longer be technically amended.** Information to log goes to 24970 9.1; log protection to 5.7.2.1 and 10.6; technical documentation to 6.5; nearly every event type in 5.5 to Clause 8. If a completeness mechanism is thought to belong in 24970, it cannot now be put there before publication. **That makes this document the only remaining place it can be added at ordinary cost**, and makes the disposition of these comments the last opportunity before an amendment cycle. | Either add the mechanism here (§3), or add a normative reference to a completeness requirement with a placeholder for the 24970 amendment, so the obligation is not lost between two documents. |
| — | Annex ZA, Table ZA.1 | **ge** | Table ZA.1 maps **Article 12(1)** — the core obligation to enable automatic recording of events over the lifetime — to **clause 5.4 alone**. 5.4 comprises three short subclauses, two of which defer to 24970. Article 11 already carries an explicit remark limiting its coverage; Article 12(1) carries none, so the table presents unqualified coverage of the central record-keeping duty by a clause that specifies very little on its own. | Either broaden the 12(1) mapping to the clauses that actually carry the obligation, or add a remark in the same form as the Article 11 entry stating the limits of coverage. An overstated Annex ZA is a risk to the presumption of conformity itself. |
| — | All pages | **ed** | The running header on every page of the body reads **prEN 18226-1:2026 (E)**. The document is prEN 18229-1. | Correct the header throughout. |
| — | 3.2 | **ed** | The draft uses "logging" for both the act of recording and the resulting artefact, and has no term for the delivered artefact a reader actually holds. The requirements proposed here are about that artefact. | Define *log record*, *delivered log* and *observation surface* in 3.2. |

### prEN 18229-3 (enquiry closed 22 September 2026; at disposition)

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
*Part 3 has not been read. Both rows below are therefore put as questions, on
the same terms the Part 1 comments were put before that draft was obtained.*

| MB | Clause | Type | Comment | Proposed change |
|---|---|---|---|---|
| — | General | **ge** | Human oversight is exercised **through** logs. An oversight function reading a log that cannot distinguish "no anomalies occurred" from "the recording path was down" is not exercising oversight; it is being shown a clean screen. **Question: does this Part require that information presented to an oversight function carry the completeness status of the log it derives from?** Note that Part 1 does require completeness — at 5.2.2 c) — so the property being relied on here is one the series already asks for; what is at issue is whether it reaches the human. | If it does not: add a requirement that an incomplete or undeclared-coverage interval is **surfaced to the oversight function, not smoothed over**. |
| — | General | **te** | Transparency obligations toward deployers and affected persons are undermined if the record's silence is uninterpretable. A transparency artefact derived from an incomplete log inherits the incompleteness. **Question: does this Part require such an artefact to carry any marking of the completeness of its source?** | If it does not: require any artefact derived from a log to propagate that log's completeness declaration. |

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

**prEN 18229-1 has now been read in full** (May 2026 draft, 21 pages of CEN
content, obtained through a national adoption). Every clause reference in §2 was
checked against that text. **prEN 18229-3 has not been read**, so the two
comments on it remain questions and are marked as such.

An earlier revision of this comment asserted, on the basis of published
commentary rather than the text, that the draft contained no requirement on
integrity, completeness, loss accounting or coverage. Two of those four were
wrong and are **withdrawn here rather than quietly dropped**:

| Earlier assertion | Outcome after reading |
|---|---|
| No requirement on integrity | **Withdrawn.** 3.2.9 defines integrity as accuracy and completeness, sourced to ISO/IEC 27000:2018, 3.36, and it is used normatively at 5.6.1. |
| No requirement on completeness | **Withdrawn.** 5.2.2 c) requires it directly. The comment now argues that it is required and not made demonstrable, which is a narrower and stronger point. |
| No requirement addressing loss | **Stands.** Confirmed by full-text search; the terms do not appear. |
| No coverage declaration | **Reframed, not withdrawn.** 6.2.1 a) requires the description and places it in the instructions for use rather than in the log. |

One further item from that earlier revision — an assertion about broken
cross-references — is **withdrawn**: the cross-references into FprEN ISO/IEC
24970 are internally consistent as drafted. The only editorial defect the
submitter can evidence is the running header, reported at §2.

Two related documents remain unread and nothing is asserted about either:
**FprEN ISO/IEC 24970**, to which this part defers most substantive content, and
**FprEN 18286**. Where a comment above turns on what 24970 contains, it is
phrased so that it does not depend on the answer.

What does **not** depend on reading any draft, and is offered on its own terms:

- the proposed normative text at §3, which stands as drafting material whatever
  the current text says;
- the impossibility result at §4, which is a statement about logs in general and
  is machine-checked, not asserted;
- the testability requirement at §5, including the negative control without
  which a coverage declaration is only a list;
- the survey at §6 of what existing work does and does not cover, drawn from
  published specifications the submitter has read in full.

**A comment that mischaracterises a draft is worse than no comment.** That
principle is why the earlier revision asked rather than stated, and why the
withdrawals above are printed rather than edited out.

*No verbatim text from the draft appears in this file. Clause numbers and
paraphrase only: the copy consulted is licensed to one named reader and is not
redistributable.*

---

*Specification, checker, examples, proof, witness reconciler and self-test are
archived at **https://doi.org/10.5281/zenodo.22728393** and developed at
<https://github.com/MattyIceMatrix/vlc-1>. Published without restriction —
clauses may be lifted into a standard with attribution and without permission.*

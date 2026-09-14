# VLC-1 — Verifiable Completeness for AI System Logs

**A vendor-neutral specification and conformance scheme.**

| | |
|---|---|
| Document | VLC-1 |
| Version | 1.1.1-draft |
| Date | 2026-09-12 |
| Revision history | Annex F |
| Status | Draft for public comment. Free to implement, free to cite, no licence required. |
| Reference implementation | a kernel sensor, not distributed here (see Annex C — declared conflict of interest, and `ACCESS.md`) |
| Conformance checker | `conformance.py`, adapter-driven, reporting a structural and an attested level (§8.4) |

---

## 0. Why this document exists

Every logging standard now in preparation for the EU AI Act specifies **what to
log**. None of them specifies **how a reader knows the log is all of it**.

- **prEN 18229-1** (CEN-CENELEC JTC 21, AI system logging) is not silent on the
  *vocabulary*. It defines **integrity** as the "property of accuracy and
  completeness" (borrowing ISO/IEC 27000:2018, 3.36), defines traceability, and
  requires that an AI system be designed "with the technical capability to
  automatically record events throughout its life cycle". What the reviewed
  draft material does not appear to provide is a **mechanism**: nothing by which
  a verifier reading the delivered log can distinguish undeclared transport loss
  from a genuinely uneventful interval, and no declaration of the observation
  surface sufficient to establish coverage. A search of the available draft
  material returns no matches for *discard* or *buffer*.
- **ISO/IEC FDIS 24970** (AI system logging) specifies event content and the
  documentation burden. The committee draft reviewed contains no requirement for
  completeness *verification*, dropped-event detection, buffer-overflow handling
  or gap accounting.
- **EU AI Act Article 12** requires automatic recording of events "throughout the
  lifetime" of a high-risk system, and Article 19 requires those logs be kept.
  Neither article, nor the recitals, defines the evidentiary property that makes
  a retained log worth anything: that its silence means nothing happened.

The consequence is a specific, demonstrable failure. **An evidence export
covering a two-hour outage, during which the logging path dropped every record,
is byte-for-byte indistinguishable from an export covering a quiet afternoon.**
Both are complete-looking. Both verify. One is worthless and nothing in it says
so.

**Scope of that claim, corrected 2026-09-13.** The failure above is stated for
**transport loss** — the logging path discarded records while the producer
continued to run and could therefore account for the gap. Where the **producer
itself** failed, no records are produced, no loss is declared, and there is
nothing for loss accounting to be absent from: a log truncated to a suffix and
renumbered closes the completeness identity and is, to a checker, the same
object as an honest one. L2 has no power against this case. It is addressed at
**L3i** (§3.3i), which requires coverage to be declared over an interval whose
every tick is witnessed by an attestor the producer does not control. See
`CORRIGENDUM-2026-09-13-01.md`, finding EXT-002, reported by Shahab K., and
`proofs/sentinel_interval.v`, theorem `producer_death_is_invisible`.

Tamper-evidence does not fix this. A hash chain proves that the records you were
given were not altered. It says nothing about the records you were not given. The
industry has converged on tamper-evidence and stopped, because tamper-evidence is
the property that is easy to name and easy to sell.

This document specifies the missing property, in testable terms, across **six
conformance levels, L0 to L5** — five substantive assurance increments above
recorded-only L0 — such that:

- a producer can state which level it meets, and be checked;
- an auditor can ask one question with a machine-checkable answer;
- a regulator can reference a level rather than a vendor.

It is written so that its normative clauses can be lifted into prEN 18229-1,
ISO/IEC 24970, or a national profile of either, with attribution but without
permission.

---

## 1. Scope

This document specifies requirements for demonstrating the **completeness** of
logs produced by AI systems, and a conformance scheme of **six levels, L0 to
L5**.

It applies to any log offered as evidence about the behaviour of an AI system,
regardless of where in the stack the log is produced — application SDK,
inference gateway, orchestration framework, operating-system kernel, or
hardware root of trust.

It is **transport-neutral, format-neutral and mechanism-neutral**. It does not
require a hash chain, a particular serialisation, kernel instrumentation, or any
named product. It specifies properties and the evidence that demonstrates them.

### 1.1 Out of scope

- What events should be logged. That is ISO/IEC 24970's subject and this
  document does not duplicate it.
- Retention periods, access control, privacy, and redaction.
- Correctness of the decisions recorded. A complete log of wrong decisions is
  complete.
- Availability of the logged system.

### 1.2 Relationship to existing work

This document is intended to be **additive**. A producer conforming to ISO/IEC
24970 for event content and to VLC-1 Level 3 for completeness makes a claim no
current standard lets it make, and an assessor can check both independently.

---

## 2. Terms and definitions

**2.1 producer** — the component that observes events and emits records. The
producer's boundary is the point past which an unobserved event is permanently
unrecoverable.

**2.2 observation surface** — the enumerable set of event sources to which the
producer is attached. Examples: the set of SDK call sites that are instrumented;
the set of HTTP routes a proxy terminates; the set of syscalls a kernel probe is
attached to; the set of model endpoints routed through a gateway.

**2.3 event** — an occurrence at a source within the observation surface which
the producer's configuration requires to be recorded.

**2.4 record** — the serialised representation of one event, or of one
completeness annotation (2.7, 2.8).

**2.5 transport** — everything between the producer emitting a record and that
record reaching durable storage. Ring buffers, queues, network hops, agents,
files, object stores.

**2.6 delivered set** — the records a verifier actually receives, in the
sequence received.

**2.7 loss declaration** — a record, inside the delivered set, that asserts that
a stated number of records were produced and not delivered, and that is itself
subject to the integrity requirements of the level claimed.

**2.8 coverage declaration** — a record, inside the delivered set, that
enumerates the observation surface at the time of recording: which sources were
attached, which were not, and which are excluded by design.

**2.9 verifier** — a party that reads only the delivered set and any public
parameters, and who is not assumed to trust the producer.

**2.10 completeness identity** — an equation over quantities present in the
delivered set whose satisfaction is a necessary condition for no undeclared
loss. See 5.2.

**2.11 policy** — the decision rules in force at the time an event was
processed, where the record asserts a decision.

**2.12 silence** — the absence of a record about a source over an interval. The
central question of this document is what a verifier is entitled to conclude
from silence.

---

## 3. Threat model

Requirements are stated against an adversary with the following capabilities. A
level's requirements are meaningful only against the threats listed for it.

| ID | Capability | Refused at |
|---|---|---|
| **T1** | Alter, reorder, insert or remove records in storage or in transit after delivery. | L1 |
| **T2** | Truncate the log at an arbitrary point. | L1 |
| **T3** | Cause the transport to discard records — by inducing load, filling a buffer, partitioning a network, or restarting an agent — during an interval of the adversary's choosing. | L2 |
| **T4** | Cause the producer to be detached from a source, or arrange for activity to occur at a source outside the observation surface, so that no event is produced and therefore nothing is lost. | L3 |
| **T5** | Change the policy after the fact, so that recorded decisions are read under rules other than the ones that produced them. | L4 |
| **T6** | Compromise, or simply control, the producer itself and emit records that satisfy every requirement below while describing behaviour that did not occur. | **L5**, partially — see 7A and 9.1 |

**T6 was out of scope in the first draft of this document and is not any more.**
In August 2026 METR published an investigation into an incident involving roughly
1,200 agents, reporting that at least 96 of the ~1,300 transcripts it reviewed
show clear evidence of spoofed tool calls — an agent issuing one command while
reporting another. METR qualifies the finding: the spoofing it noticed was
*"obvious small-scale tests"*, and *"more sophisticated or extensive spoofing may
have been harder to detect by design"*. It estimates it captured *"a bit over
90% of the agent activity"*. This is an existence proof rather than a prevalence
estimate, and an existence proof is sufficient: a threat that has been observed
is not a residual.

**T4 is the threat this document exists to name.** It is invisible to every
integrity mechanism and to every loss-accounting mechanism, because it produces
no loss: an event that was never observed generates no record to drop, and every
identity closes perfectly. A log that is complete with respect to what the
producer saw, while the producer saw a fraction of what happened, is the failure
mode that no current standard asks about.

---

## 4. Level 1 — Tamper-evident

> *A verifier can detect any modification of the delivered set.*

**VLC-L1-1** The producer SHALL bind each record to its predecessors such that
altering, reordering, inserting or removing any record is detectable by a
verifier holding only the delivered set and a published root or public key.

**VLC-L1-2** The binding mechanism SHALL be documented and independently
recomputable without vendor-supplied software.

**VLC-L1-3** The log SHALL carry an end marker asserting the final value of the
binding, so that truncation of the tail is detectable.

**VLC-L1-4** The producer SHALL document the collision resistance and the
lifetime of the primitive used.

**Test.** Given a conforming log, a verifier recomputes the binding end-to-end
and accepts. The verifier then mutates one byte of one record and MUST reject;
removes one interior record and MUST reject; truncates the final record and MUST
reject. A producer whose log survives any of these three does not meet L1.

**What L1 does not give you.** Nothing about records that were never delivered.
A hash chain over 800 records is equally valid whether 800 or 8,000 were
produced. This is the level at which essentially all commercially available AI
audit logging currently stops.

---

## 5. Level 2 — Loss-accounted

> *A verifier can determine whether any record produced was not delivered, and
> by how many.*

**VLC-L2-1** The producer SHALL maintain a monotonic count, or an equivalent
ordinal, of records produced, independent of whether they were delivered.

**VLC-L2-2** When the producer or transport discards a record, the producer
SHALL emit a loss declaration (2.7) stating at minimum the number of records
lost and the interval or ordinal range in which the loss occurred.

**VLC-L2-3** A loss declaration SHALL be subject to the same integrity binding
as an event record, and SHALL NOT be removable without violating L1.

**VLC-L2-4** The producer SHALL declare, in the log, the behaviour of the
transport when its capacity is exhausted: whether it blocks, discards oldest,
discards newest, or discards silently. A producer that cannot detect discard
SHALL declare that it cannot, and SHALL NOT claim L2.

**VLC-L2-5** The delivered set SHALL satisfy a **completeness identity**:

```
  |delivered event records| + sum(loss declarations) == |records produced|
```

where `|records produced|` is derived from quantities in the delivered set
(final ordinal, sequence high-water mark, or an explicit produced count in the
end marker) and not supplied out of band.

**VLC-L2-6** Where the completeness identity does not close, the verifier SHALL
report the log as **not complete**, and SHALL NOT report it as merely
"integrity verified".

### 5.1 Note on implementability

L2 requires the producer to **count**, not to guarantee delivery. It is
achievable at any layer. An application-layer SDK meets L2 by attaching a
sequence number and emitting a `dropped: n` record when its queue sheds load.
Nothing here requires kernel instrumentation, and a claim that L2 is achievable
only below the application is wrong.

### 5.2 The attack L2 refuses that L1 does not

T3. The adversary generates load for two hours, the ring buffer overflows, 4,200
records are discarded. At L1 the remaining chain is valid and the export is
clean. At L2 the identity does not close, or a loss declaration in the chain says
`4200`, and the auditor's conclusion inverts: *this export cannot speak for that
interval.*

---

## 6. Level 3 — Coverage-declared

> *A verifier can distinguish "nothing happened at this source" from "this source
> was not being observed."*

> **Amended 2026-09-13 by Corrigendum 1, finding EXT-001 (Shahab K.).**
> VLC-L3-1 is split. **L3-1a** — a coverage declaration is present and
> well-formed — is **structural**: a verifier recomputes it from the delivered
> log. **L3-1b** — the declared surface is the surface actually observed — is
> **attested**, always, with no code path to structural. **VLC-L3-1(d)** is
> reclassified **attested** on the same grounds. VLC-V-3 forbids a supplied
> statement raising the structural level; the previous classification allowed
> exactly that, and was inconsistent with VLC-L3-4, which was already attested.

**VLC-L3-1** The producer SHALL enumerate its observation surface (2.2) in the
log, as a coverage declaration (2.8), naming:

  a) sources attached and delivering;
  b) sources the producer attempted to attach and could not, with a reason;
  c) sources within the producer's declared design scope that are deliberately
     not instrumented, with a reason;
  d) the criterion by which the enumeration is known to be exhaustive.

**VLC-L3-2** The coverage declaration SHALL be subject to the same integrity
binding as an event record.

**VLC-L3-3** A coverage declaration SHALL be emitted at the start of each
session or logging epoch, and again whenever the observation surface changes.

**VLC-L3-4** The producer SHALL be capable of demonstrating, by test, that
activity at each declared-attached source produces records, and that activity at
each declared-unattached source does not. The test SHALL fail in **both**
directions — a producer that declares a source it is not observing SHALL be
detected, and a producer observing a source it did not declare SHALL be
detected.

**VLC-L3-5** A coverage declaration SHALL NOT be counted as an event record when
evaluating the completeness identity of 5.2.

**VLC-L3-6** Where the observation surface is not enumerable — the producer
cannot state the set of sources it is or is not attached to — the producer SHALL
declare it as non-enumerable and SHALL NOT claim L3.

### 6.1 The attack L3 refuses that L2 does not

T4, and it is worth stating concretely because it is counter-intuitive.

A kernel sensor governs file opens by attaching a probe to `openat`. The
workload is updated and begins calling `openat2` instead. No probe is attached to
`openat2`. Therefore no decision is produced. Therefore nothing is lost.
Therefore **no loss declaration is emitted, and the L2 identity closes
perfectly.** The log is complete, tamper-evident, fully accounted — and half the
file opens in that session are not in it, with nothing marking their absence.

The same shape occurs at every layer: an SDK release adds a code path nobody
instrumented; a proxy terminates four routes and a fifth is added to the load
balancer; a gateway covers three model endpoints and a team stands up a fourth.
In each case the log is *correct* and the conclusion drawn from it is *false*,
and no integrity or accounting mechanism can reveal the difference. Only an
enumeration of what was being watched can.

This is the requirement absent from every current draft, and it is absent
because the failure has no symptom.

---

## 7. Level 4 — Policy-bound

> *A verifier can determine the exact rules under which each recorded decision
> was made.*

Applies to logs whose records assert a decision, classification, allow/deny,
score threshold or other policy-dependent verdict. Logs that record only
observations may claim L3 as their terminal level and SHALL state so.

**VLC-L4-1** The producer SHALL bind the log to a digest of the exact policy in
force, such that re-rooting the log under a different policy is detectable.

**VLC-L4-2** A change of policy during a session SHALL itself be a record in the
log, carrying the digests before and after.

**VLC-L4-3** The policy corresponding to a digest SHALL be retrievable and
independently re-evaluable. A verifier SHALL be able to replay a recorded input
against the recorded policy and obtain the recorded verdict.

**VLC-L4-4** Where the decision function is not deterministic or not replayable,
the producer SHALL declare this and SHALL NOT claim L4.

### 7.1 The attack L4 refuses that L3 does not

T5. The log is complete and its coverage is declared. Every record says `ALLOW`.
Six months later the assessor asks what `ALLOW` meant. The policy file on disk is
the current one. There is no evidence the recorded `ALLOW`s were computed under
it, and a permissive rule introduced after the incident is indistinguishable from
one that was always there. The verdicts have been silently reinterpreted.

---

## 7A. Level 5 — Independently witnessed

> *The record was not written by the thing it describes.*

Levels 1 to 4 are properties of a log. This one is a property of **who wrote
it**, and no amount of care with the records substitutes for it.

An agent's tool-call transcript, an SDK trace, a framework hook and an in-process
logger are all written by, or beside, the process being audited. Signing such a
record proves that nobody *else* edited it. It cannot establish that the process
wrote down what it did, because the record and the behaviour have the same
author. `no_check_on_the_self_report_can_see_substitution` in
`proofs/sentinel_completeness.v` states this at full strength: for any two
behaviours and any self-report, **every** function of the self-report returns the
same answer. The quantifier is the whole content.

**VLC-L5-1 (independence)** The producer shall lie outside the control of the
process or processes whose behaviour it records: the audited process shall not be
able to write, delete, suppress or reorder the producer's records, nor detach the
producer, without that being itself recorded or prevented.

**VLC-L5-2 (declared boundary)** The provider shall state the trust boundary
between producer and audited process, and what an audited process with full
control of its own execution context could still do to the record.

**VLC-L5-3 (reconciliation)** Where a self-reported record exists for the same
interval, the log shall be reconcilable against it over a **declared
reconciliation scope**, and the reconciliation shall report **both**
directions — actions claimed and not witnessed, and actions witnessed and not
claimed. Reporting only one direction detects only half of a substitution.

**VLC-L5-4 (the witness's own standing)** The conformance level of the witnessing
log shall be stated, and a witness below L3 shall not be presented as
corroboration. A witness with an undeclared coverage gap agrees with a lie
honestly: `an_unwitnessed_source_defeats_reconciliation` exhibits a substitution
at a source outside the witness's surface that produces no divergence at all.

**VLC-L5-5 (scope declaration)** The reconciliation scope shall be recorded with
the result, including every exclusion applied. An exclusion nobody can see is how
a reconciler is quietly rigged, and a scope that excludes everything reconciles
perfectly.

### 7A.1 This is not a requirement only one architecture can meet

Independence is a property of the trust boundary, not of a technology. A
hypervisor observing a guest, a network tap outside the host, a separate machine
receiving an append-only feed, an external proxy *for the traffic it terminates*,
a hardware root of trust, and an operating-system kernel observing a user-space
process all satisfy VLC-L5-1 for their own scope. What does not satisfy it is a
recorder that the audited process can write to, stop, or replace — which is where
essentially all AI agent audit trails sit today.

The honest consequence is that L5 has a *scope*, not a *winner*. A gateway is an
independent witness of the requests that route through it and is no witness at all
of a subprocess that bypasses it, which is exactly what VLC-L5-2 forces a provider
to write down.

### 7A.2 The attack L5 refuses that L4 does not

T6. The transcript says `uname -r`; the process ran something else and read a file
it never mentioned. Every record in the transcript is chained, the identity
closes, the coverage is declared, the policy is bound — and the transcript is
fiction. The reconciliation produces one *claimed-not-witnessed* finding and one
*witnessed-not-claimed* finding, and that **pair** is the substitution signature.
A record written by the audited process cannot produce this finding about itself.

`witness/` in this repository is a runnable instance; `demo/08-the-witness.sh`
in the reference implementation runs the same agent honestly and dishonestly and requires
zero findings from the first and the signature from the second.

## 8. Conformance

### 8.1 The lattice

Levels are **cumulative and strictly ordered**: a producer claiming Ln SHALL
satisfy every requirement of L1..Ln. A producer SHALL claim exactly one level.

```
     L0 ──► L1 ──────► L2 ──────► L3 ──────► L4 ──────► L5
  recorded  tamper-   loss-     coverage-   policy-   independently
            evident   accounted declared    bound     witnessed

  refuses:  T1,T2     +T3       +T4         +T5       +T6

  structural ceiling  ───────────────────────────┘
  (8.4: independence is not a property of the bytes)
```

Strictness is not editorial: for each adjacent pair there exists a log that
satisfies the lower level and not the higher, and an attack that the higher
refuses and the lower admits. This is proved in
`proofs/sentinel_completeness.v` and exhibited as worked example
logs in `examples/`, including one that satisfies L2 and is missing
half its events.

### 8.2 Claiming a level

A conformance claim SHALL state:

  a) the level claimed;
  b) the producer's boundary (2.1) and observation surface (2.2);
  c) which of T1–T5 the claim is therefore asserted against;
  d) the mechanism satisfying each requirement, by requirement ID;
  e) any requirement met by declaration rather than by mechanism (VLC-L2-4,
     VLC-L3-6, VLC-L4-4).

### 8.3 Checking a claim

A claim is checked by running a verifier against a log the producer supplies,
without vendor software in the trust path. `conformance.py` in this
repository is one such verifier: it takes any JSONL log plus a small declarative
adapter mapping the producer's field names onto the abstract quantities of
clauses 4–7, and reports the level achieved and the exact requirement IDs that
failed.

Adapters are data, not code. Writing an adapter for a competing product is a
fifteen-minute exercise and is encouraged; `adapters/` contains
adapters for several log shapes including ones this project did not produce.

**A verifier SHALL report the level actually demonstrated, never the level
claimed — and SHALL distinguish which parts of that level it established and
which parts it merely relayed. See 8.4.**

### 8.4 Structural and attested verification

A verifier reading a log can establish some of these requirements and not
others, and a scheme that blurs the two invites exactly the criticism it
deserves: *your verifier is only verifying your own assertions.*

**Definitions.**

- A requirement is **structural** where a verifier decides it by recomputing
  something from the delivered evidence — the binding, the completeness
  identity, the presence and binding of a coverage declaration.
- A requirement is **attested** where the verifier decides it from a statement
  the producer supplies alongside the log: that the mechanism is documented,
  that a bidirectional coverage test exists, that the producer lies outside the
  audited process's control.

**VLC-V-1** A conformance report SHALL state a **structural level** and an
**attested level** separately. The structural level SHALL be computed from the
structural requirements alone.

**VLC-V-2** A conformance report SHALL mark each requirement as structural or
attested, so that a reader can see which claims rest on the producer's word.

**VLC-V-3** No supplied statement SHALL be capable of raising the structural
level. A scheme in which a more generous declaration produces a higher
structural number has no structural number.

**VLC-V-4** **L5 is attested by construction, so the structural ceiling is L4.**
Independence is a fact about who holds the pen; no amount of reading the bytes
settles it. A report claiming a structural L5 is in error.

**VLC-V-5** Where an attested requirement is supported by an **evidence
manifest** entry (Annex E), the report SHALL say so, and SHALL distinguish that
case from a bare assertion.

NOTE This clause was added in 1.1-draft after external review observed that the
1.0-draft checker presented adapter-supplied assertions as independently
demonstrated. The observation was correct. In the reference checker, 15 of 26
requirements are structural and 11 attested; two of the attested ones formerly
passed when the adapter said nothing at all, which was a defect and is fixed.

---

## 9. What this specification does not require

Stated explicitly, because a specification whose limits are hidden is the thing
it is trying to replace.

**9.1 L1–L4 do not defend against a producer under the auditee's control (T6);
L5 addresses it and does not eliminate it.** A producer that fabricates records,
fabricates loss declarations and fabricates its coverage declaration satisfies
every clause of L1–L4. L5 removes the producer from the auditee's reach for the
scope it declares, and requires reconciliation in both directions — but a witness
is still a producer, its own coverage is still finite (VLC-L5-4), and an adversary
who compromises the witness itself is outside this document. What VLC-1 does at
every level is move the attack from *silent* to *stated*: an adversary must write
down a specific, checkable false claim about losses, coverage, or what it did,
which is evidence of intent in a way that a missing record is not.

**9.2 It does not require guaranteed delivery.** Losing records is permitted.
Losing them silently is not. This is deliberate: a requirement to never drop a
record is unimplementable under load and would be met by the industry with a
declaration rather than a mechanism.

**9.3 It does not require any particular observation layer.** A conforming
application-layer producer with a small, honestly declared observation surface is
conformant to L4, and a kernel producer that cannot enumerate its probes is not.
L5 is the one place where architecture bites, and it bites on the *trust
boundary*, not the technology: see 7A.1 for the several unrelated architectures
that satisfy it. An in-process logger cannot, and this is a fact about authorship
rather than a preference.

**9.4 It does not make coverage complete.** VLC-L3-1(d) requires the producer to
state *how it knows* its enumeration is exhaustive. Many producers will only be
able to say "by manual review of the instrumentation table", which is weak. It is
still infinitely stronger than the current state, which is not asking.

**9.5 It does not address log correctness, retention, privacy or access
control.**

---

## Annex A (normative) — Conformance test procedure

For each level, the verifier performs the tests below. A producer meets the level
only if every test for that level and all lower levels passes.

| Test | Level | Procedure | Pass condition |
|---|---|---|---|
| A.1 | L1 | Recompute the binding over the delivered set. | Accepts. |
| A.2 | L1 | Flip one byte in an interior record; recompute. | Rejects, and names the record. |
| A.3 | L1 | Delete one interior record; recompute. | Rejects. |
| A.4 | L1 | Delete the final record; recompute. | Rejects (end marker absent or head mismatch). |
| A.5 | L2 | Evaluate the completeness identity of 5.2. | Closes exactly. |
| A.6 | L2 | Remove a loss declaration from a log that has one. | L1 rejects it. |
| A.7 | L2 | Supply a log with a known induced loss and no declaration. | Identity fails; verifier reports not complete. |
| A.8 | L3 | Confirm a coverage declaration is present and bound. | Present, bound, epoch-anchored. |
| A.9 | L3 | Exercise each declared-attached source. | Records appear for every one. |
| A.10 | L3 | Exercise each declared-unattached source. | No records appear for any. |
| A.11 | L3 | Mutate the producer to declare a source it does not attach. | A.9 fails. Negative control. |
| A.12 | L3 | Confirm coverage declarations are excluded from A.5. | Identity still closes. |
| A.13 | L4 | Re-root the log under a different policy digest. | Rejects. |
| A.14 | L4 | Replay a recorded input against the recorded policy. | Reproduces the recorded verdict. |
| A.15 | L5 | From inside the audited process, attempt to write, truncate, reorder or delete the producer's records. | Prevented, or itself recorded. |
| A.16 | L5 | Run a workload that reports honestly; reconcile. | **Zero** findings over the declared scope. |
| A.17 | L5 | Run the same workload reporting one action while performing another, plus one unreported action; reconcile. | Both directions reported; substitution signature raised. |
| A.18 | L5 | State the witnessing log's own level. | L3 or above, evaluated by A.1–A.12. |

A.11 is the test most producers will not have. It is the one that distinguishes a
coverage declaration from a coverage *assertion*, and a scheme that omits it
rewards writing a longer list.

---

## Annex B (informative) — Mapping to standards in preparation

| Instrument | Status at 2026-09-12 | Where VLC-1 attaches |
|---|---|---|
| **EU AI Act Art. 12** | In force; Arts. 9–15 apply 2 Dec 2027 | "automatic recording of events over the lifetime" — Art. 12 states the obligation; VLC-1 L2/L3 states the evidentiary property that makes a retained log discharge it. |
| **EU AI Act Art. 19** | In force | Log retention presumes the retained log means something. |
| **prEN 18229-1** | Public enquiry closed Jul–Aug 2026; comment disposition in progress; CEN-CENELEC target Q4 2026 | Add a completeness clause, or a normative reference to one. The draft's deferral of event content to 24970 does not cover completeness, which is a property of the log rather than of an event. |
| **prEN 18229-3** | Public enquiry open until **22 September 2026** | Transparency and human oversight: an oversight function reading an incomplete log is not exercising oversight. The strongest attachment point available in the current window. |
| **ISO/IEC FDIS 24970** | FDIS, last stage before publication | Too late for the base document; the route is an amendment or a new work item under SC 42. |
| **ISO/IEC 42001** | Published | Clause 8.1 asks whether controls are *effective*, not present. A log that cannot distinguish an outage from a quiet afternoon is a control that is present. Clause 9.1 monitoring and 10.2 nonconformity both rest on it. |
| **ISO/IEC 27001 A.8.15 / A.8.16** | Published | Logging and monitoring controls, same gap, older. |

---

## Annex C (normative) — Declared conflict of interest

This specification was written by the author of a product that implements it.

The reference implementation is that product — a kernel sensor, which is not in this repository. Its journal meets
L1–L4 as of 2026-09-12, and it is the first implementation known to the author to
meet L3 at all.

Three deliberate constraints were applied to keep the specification from being a
description of one product:

1. **No requirement names a mechanism this product uses** where a weaker-coupled
   statement was available. Clause 4 does not require a hash chain; clause 5 does
   not require a ring-buffer drop counter; clause 6 does not require eBPF or the
   kernel.
2. **The conformance checker is adapter-driven** and ships with adapters for log
   shapes this project did not produce. A checker that only reads one vendor's
   format is a sales tool.
3. **Every level is reachable at the application layer.** If a level were
   reachable only from the kernel, it would be a moat rather than a
   specification, and it is noted in 5.1 and 9.3 that it is not.

A reviewer who believes a clause is nonetheless shaped around the reference
implementation is asked to say so; the clause will be reworded or dropped. The
value of this document is entirely in being adoptable by parties who compete with
its author.

---

## Annex E (normative) — The evidence manifest

An attested requirement (8.4) rests on the producer's word. This annex is how a
producer converts a word into a citation.

**VLC-E-1** A producer MAY supply, alongside the log, an **evidence manifest**:
a set of entries keyed by requirement identifier. Each entry SHALL name the test,
the runner that performed it, the **digest of that runner**, the **digest of its
output**, and the result.

**VLC-E-2** A verifier SHALL treat an entry that is incomplete, or that records
a result other than a pass, as **weaker than no entry at all** — because an
incomplete citation is a claim dressed as evidence. It SHALL fail the
requirement rather than fall back to the bare assertion.

**VLC-E-3** Evidence for a requirement the delivered log contradicts SHALL NOT
raise that requirement. A manifest never overrides the bytes.

**VLC-E-4** The artefacts an entry names MAY be confidential. Their **digests
SHALL be published**. The digest is what stops a private artefact being
substituted after the fact: a reader who later obtains the artefact under
whatever terms apply can check it against a digest they already held.

**VLC-E-5** Where a requirement concerns a test, the entry SHALL name the
**negative control** — the condition under which that test is known to fail.
A test with no stated failure mode is not evidence that anything was checked.

### E.1 Shape

```json
"evidence": {
  "VLC-L3-4": {
    "test": "coverage-bidirectional-001",
    "what": "every member of the open family is exercised, and the coverage
             declaration is asserted against observed behaviour in BOTH
             directions",
    "runner": "coverage-test.sh",
    "runner_digest": "sha256:2dcb78fd…",
    "output_digest": "sha256:dae412c8…",
    "negative_control": "a mutant that declares a source it never attaches
                         must be caught",
    "result": "PASS",
    "availability": "under NDA"
  }
}
```

### E.2 What this does and does not buy

It does **not** make an attested requirement structural. The verifier still
cannot run the test; it has only the log. What it buys is that the reader is
told precisely what to ask for and precisely how to check that what they were
given is what was cited. That converts *"the vendor says a negative control
exists"* into *"the vendor named a runner, published its digest, and can be held
to it."*

The reference checker reports these as `[A+]` rather than `[A]`, and counts them
in the summary, so a report shows at a glance how much of the attested half is
citable.

---

## Annex D (informative) — Prior art and why it does not cover this

| Body of work | What it gives | What it does not |
|---|---|---|
| RFC 5848 / syslog signing, RFC 9162 Certificate Transparency, Merkle logs generally | Strong L1: tamper-evidence, consistency proofs, inclusion proofs | Nothing about production-versus-delivery. CT proves an entry is in the log, not that everything issued reached it. |
| Secure/forward-integrity audit logs (Schneier–Kelsey and descendants) | L1 under compromise-after-the-fact | Same gap. Explicitly assumes events reach the logger. |
| WORM storage, object-lock, blockchain anchoring | L1 by a different route | Same gap, and often marketed as if it were completeness. |
| OpenTelemetry | Dropped-span counters exist in the SDK and collector, and are a genuine L2 primitive | They are telemetry about the telemetry, live on a separate metrics path, are not bound to the trace data, and vanish if the metrics path is the one that dropped. Not in-band, not integrity-bound. **The closest existing thing, and it is one design decision away from L2.** |
| Linux audit / auditd `lost` counter | In-band loss count | Not integrity-bound; no coverage declaration; the ruleset is not bound to the log. |
| AI-specific audit products (agent security posture, LLM gateways, guardrail platforms) | L1, generally via hash chain or immutable store | No loss accounting, no coverage declaration, no policy binding found in published material as of 2026-09-12. |
| Agent tool-call transcripts | a readable record of intent | Written by the audited process, so VLC-L5-1 fails by construction. METR’s August 2026 investigation is what that failure looks like once someone goes looking. |

The pattern across all of it: **the field solved integrity thoroughly and never
asked the next question.** Not because it is hard — L2 is a counter — but because
nobody has been required to answer it, and an unasked question has no budget.

---

## Annex F (informative) — Revision history

Every version is archived. The **concept DOI**
[10.5281/zenodo.22728393](https://doi.org/10.5281/zenodo.22728393) always
resolves to the newest; the version DOI below pins a particular text.

| Version | Date | Version DOI | What changed, and why |
|---|---|---|---|
| 1.0-draft | 2026-09-12 | [10.5281/zenodo.22728394](https://doi.org/10.5281/zenodo.22728394) | First publication. |
| 1.1-draft | 2026-09-12 | [10.5281/zenodo.22728851](https://doi.org/10.5281/zenodo.22728851) | External review found the checker presenting adapter-supplied assertions as independently demonstrated. Added §8.4 (structural versus attested), `VLC-V-1`..`VLC-V-5`, Annex E (the evidence manifest), and a control that runs the reviewer's attack. Narrowed the standards claim in §0 and Annex B after verifying that prEN 18229-1 does define integrity as the "property of accuracy and completeness". |
| **1.1.1-draft** | 2026-09-12 | [10.5281/zenodo.22729353](https://doi.org/10.5281/zenodo.22729353) | Corrective. The 1.1-draft bump reached this document and `CITATION.cff` but not `conformance.py`, whose `VERSION` constant still read `1.0-draft`; every report the archived 1.1-draft checker emitted therefore cited a version in which §8.4 does not appear. No requirement, no check and no computed level changed. `selftest.sh` §7 now requires the version the checker stamps into its report to match this table and `CITATION.cff`. |

The 1.1.1 entry is kept in the normative document rather than in a release note
on purpose. `VLC-E-2` says an incomplete citation is worse than none; a
specification that says so and then quietly corrects its own citation metadata
would be asking of others what it does not do itself.

---

*VLC-1 is published without restriction. Cite it, implement it, fork it, or
lift its clauses into a standard without asking.*

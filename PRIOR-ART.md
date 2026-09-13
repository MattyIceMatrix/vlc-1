# Prior art and related work

*For the public specification. Vendor-neutral.*
*Added 2026-09-13. Revised twice the same day as reading deepened.*

> **Basis.** arXiv:2606.04193 read in full. arXiv:2602.20214 read to its
> contributions and invariants. arXiv:2606.12320 abstract only. All other
> entries from documentation or press materials. No cited system has been
> evaluated by running it. Corrections are welcome and will be applied without
> argument.

This specification did not state its motivating problem first. Three
independent 2026 works name completeness as a goal. **None of them makes it
recomputable by a reader of a delivered record**, and that distinction is the
whole of what is claimed here.

## Completeness as a kernel invariant

**Jing Zhang, "Right to History: A Sovereignty Kernel for Verifiable AI Agent
Execution", arXiv:2602.20214 [cs.CR], February 2026, CC BY 4.0.**

PunkGo is a Rust sovereignty kernel placing a verified kernel rather than the
model as the trusted computing base, unifying RFC 6962 Merkle audit logs,
capability-based isolation, energy-budget governance and a `hold_on`
human-approval mechanism. It formalises five invariants — Append-Only,
**Completeness**, Integrity, Boundary Enforcement, Energy Conservation — with
structured proof sketches, and reports adversarial testing and measured latency.

**This precedes the present specification by seven months and names completeness
as a first-class invariant.** No priority is claimed over the principle, the
kernel-as-TCB architecture, the capability boundary, or the human-approval
mechanism, each of which appears there first.

The distinction claimed here is narrow: PunkGo's Completeness invariant is a
property of the **producer's construction** — the kernel records all legitimate
actions. This specification defines completeness as a property a **reader of a
delivered record** can recompute, without trusting the producer, including
across declared intervals of loss. The two are complementary: a PunkGo log would
be a natural subject for a conformance assessment under this specification.

A second distinction, offered without overstatement: the invariants there are
supported by structured proof sketches. The ordering of levels here is
machine-checked, with the proof bound to the reference implementation by
exhaustive differential.

## Self-authorship and the retrieval gap

**Juan Figuera, "Notarized Agents: Receiver-Attested Confidential Receipts for
AI Agent Actions", arXiv:2606.04193 [cs.CR], 2 June 2026, CC BY 4.0.** Read in
full.

States the problem this specification's L5 addresses, in the same terms and
three months earlier: *the entity producing the activity log is the same entity
whose activity is being logged*, and a compromised agent *can omit, alter, or
fabricate its own traces*. **No priority is claimed over this argument.**

His §6 separates per-receipt verifiability from set-completeness and states the
retrieval gap: an inclusion proof answers whether a receipt is in the log, not
whether the log returned every matching receipt. **No priority is claimed over
that statement either.** He offers three mechanisms — authenticated query
results, full log audit, multi-log redundancy — each placing the burden on the
log. **L2 here closes the identity from the producer side instead**, via a
monotonic issuance counter and in-chain loss declarations, so that a withheld
record is detectable from the returned set alone. That fourth mechanism is the
contribution claimed.

§4.4 independently proposes binding revocation to a transparency log's
integrated time rather than signer-asserted time, to defeat backdating. Annex H
reaches the same conclusion by another route; no priority is claimed on the
observation, only on its machine-checked form.

## Runtime governance architectures

**Krti Tallam, "A Five-Plane Reference Architecture for Runtime Governance of
Production AI Agents", arXiv:2606.12320 [cs.AI], 10 June 2026.** Abstract only.
Stop-anywhere mediation, capability attenuation through delegation chains, audit
as a structured evidence substrate, with evidence reconstructability reported on
every trial. Overlaps the enforcement and evidence concerns here substantially.
**No claim of priority is made.**

## Transparency receipt standardisation

The **IETF SCITT working group** (draft-ietf-scitt-architecture,
draft-ietf-scitt-scrapi) standardises COSE_Sign1 transparency receipts, with
SCRAPI directed at authenticated query results. Adjacent receipt work includes
Signet, Agent Receipts, Pipelock, Agent Passport System,
draft-farley-acta-signed-receipts and draft-nivalto-agentroa. None examined
here. This specification is written to be complementary to a transparency-receipt
framework rather than an alternative to one.

## Long-term validity and hardware roots

**Guardtime KSI** (~2007 onward) achieves non-expiring signatures using hash
functions and periodic public publication, so migration is unnecessary for those
signatures; Annex H's re-anchoring is the general construction for suites that
do depend on migratable assumptions, and hash-only schemes satisfy it trivially.

**EQTY Lab Verifiable Compute** (December 2024, with Intel and NVIDIA) produces
TEE-attested, publicly time-anchored certificates for AI operations. Annex I is
written so that such certificates are a conformant root of trust for the
coverage claim.

## Foundational

Certificate Transparency (RFC 6962, RFC 9162), Crosby and Wallach's
tamper-evident logging, CONIKS, seL4's verified capability isolation, and
witness cosigning (Syta et al.) are the substrate all of the above build on.

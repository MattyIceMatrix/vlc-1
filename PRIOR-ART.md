# Prior art and related work

*For the public specification. Vendor-neutral.*
*Added 2026-09-13. Revised 2026-09-13 (twice) and 2026-09-19.*

> **Basis.** arXiv:2606.04193 read in full. arXiv:2606.12320 read in full.
> arXiv:2602.20214 read to its contributions and invariants. IETF drafts read
> from their datatracker pages and abstracts; draft-kamimura-scitt-refusal-events
> §7.2 read in full; draft-kamimura-vap-framework-00 body **not yet read in
> full**. All other entries from documentation or press materials. No cited
> system has been evaluated by running it. Corrections are welcome and will be
> applied without argument.

This specification did not state its motivating problem first. At least five
independent 2026 works name completeness as a goal or invariant. **In every one
the property is established by the producer, or holds only over records that
were logged. None of them lets a reader of a delivered record establish, from
that record alone, that a record is missing** — and that single distinction is
the whole of what is claimed here.

## Completeness as a tiered conformance framework

**VeritasChain Standards Organization (Kamimura),** *Verifiable AI Provenance
Framework*, `draft-kamimura-vap-framework-00`; with
`draft-ailex-vap-legal-ai-provenance-03` (March 2026),
`draft-kamimura-scitt-vcp-01`, and `draft-kamimura-scitt-refusal-events-02`
(January 2026). Open, vendor-neutral, published January 2026.

Defines hash-chain integrity, digital signatures, **unified conformance levels
(Bronze / Silver / Gold)**, external anchoring via RFC 3161 and SCITT, **a
Completeness Invariant pattern**, a standardised Evidence Pack, and a
*Negative Proof* concept for demonstrating that content was not generated.
States an intention to engage ISO/IEC JTC 1/SC 42. **This precedes the present
specification by eight months and holds the tiered-conformance posture, the
vendor-neutral principle, and the term "completeness" first. No priority is
claimed over any of them.**

The distinction claimed here is narrow and is stated in their own text.
`draft-kamimura-scitt-refusal-events-02` §7.2: *"The completeness invariant
provides detection for logged events: auditors can identify ATTEMPTs without
Outcomes. However, if an ATTEMPT is never logged, this specification cannot
detect the omission."* Their invariant is pairwise correlation over logged
events. This specification's L2 identity — a producer counter and in-chain loss
declarations, recomputed by the reader — detects a record that was never
delivered. Both frameworks concede the same outer limit: a producer that never
logs defeats both, and both point to attestation as the only repair.

## Transparency receipts for agent actions

**RFC 9943**, *An Architecture for Trustworthy and Transparent Digital Supply
Chains* (SCITT), and **RFC 9942**, *COSE Receipts* — both June 2026. The
substrate every profile below builds on. RFC 9943's discussion of issuer
participation notes that an issuer may selectively register some statements but
not all, and leaves the consequence to relying parties. This specification is
written to be complementary to a SCITT profile rather than an alternative to one.

**Steven Mih (Action State Group),** *An Agent Action Capsule Profile for
SCITT*, `draft-mih-scitt-agent-action-capsule-04` (August 2026). A
digest-committed record per agent action carrying its verdict — executed,
blocked, denied, errored, timed out — with an effect-state binding so an attempt
cannot be presented as a completion, **a capsule on every verdict including
refusals**, and an `attestation_mode` distinguishing anchored from unanchored
records. Reference implementation on PyPI, an independent Go verifier, frozen
conformance vectors, and a public interop table. **Records what occurred per
action; does not claim set-completeness. No priority is claimed over it**, and a
completeness extension to this profile is the form this specification's
contribution most naturally takes within the IETF.

Also on the same substrate, none examined here beyond their abstracts:
`draft-emirdag-scitt-ai-agent-execution-00` (agent interaction records with an
independent evidence custodian), `draft-dawkins-scitt-ai-article50-00` (EU AI
Act Article 50 receipts), `draft-rampalli-scitt-capsule-provenance-binding-00`,
and TRACE (an EAT-based trust record binding TEE evidence and tool transcript).

## Completeness as a kernel invariant

**Jing Zhang,** *Right to History: A Sovereignty Kernel for Verifiable AI Agent
Execution*, arXiv:2602.20214 (February 2026, CC BY 4.0). A Rust sovereignty
kernel as TCB, RFC 6962 Merkle audit logs, capability-based isolation, a
human-approval mechanism, and five invariants including Completeness, with
proof sketches and adversarial testing. **Precedes this specification by seven
months. No priority is claimed** over the kernel-as-TCB architecture, the
capability boundary, the approval mechanism, or completeness as an invariant.
Its Completeness is a property of the kernel's construction; this
specification's is a property a reader recomputes from a delivered record.

## Self-authorship and the retrieval gap

**Juan Figuera,** *Notarized Agents: Receiver-Attested Confidential Receipts for
AI Agent Actions*, arXiv:2606.04193 (2 June 2026, CC BY 4.0). Read in full.
States the self-authorship argument this specification's L5 addresses — the
entity producing the log is the entity whose activity is logged — and the
per-receipt versus set-completeness distinction, three months earlier. **No
priority is claimed over either.** His §6 offers three mechanisms for
set-completeness, each placing the burden on the log; this specification's L2
places it on the producer instead. His §4.4 independently proposes log-integrated
time over signer-asserted time to defeat backdating; Annex H reaches the same
conclusion by another route.

## Runtime governance architectures

**Krti Tallam,** *A Five-Plane Reference Architecture for Runtime Governance of
Production AI Agents*, arXiv:2606.12320 (10 June 2026). Read in full. Names
audit opacity as a threat, distinguishes audit from logging, and defines an
evidence substrate with a reconstructability property under partial
information, argued structurally. Overlaps the enforcement and evidence concerns
here substantially. **No claim of priority is made.**

## Integrity of what is present

**Attested Intelligence Holdings,** *Attested Governance Artifacts* (patent
pending, USPTO 19/433,835, filed December 2025). Signed, hash-chained receipts
and offline-verifiable evidence bundles. Their own statement of scope: *"A
verified bundle proves the integrity of every receipt present. It does not
prove the operator recorded every action."* That is the boundary this
specification addresses from the other side.

## Long-term validity and hardware roots

**Guardtime KSI** (~2007 onward): non-expiring hash-only signatures with
periodic publication; Annex H's re-anchoring is the general construction for
suites that depend on migratable assumptions, and hash-only schemes satisfy it
trivially. **EQTY Lab Verifiable Compute** (December 2024, with Intel and
NVIDIA): TEE-attested, time-anchored certificates for AI operations; Annex I
treats such certificates as a conformant root of trust.

## Foundational

Certificate Transparency (RFC 6962, RFC 9162), Crosby and Wallach's
tamper-evident logging, CONIKS, seL4's verified capability isolation, and
witness cosigning (Syta et al.).

## Revisions

- **2026-09-13** — created, from abstracts.
- **2026-09-13** — revised after reading arXiv:2606.04193 (Figuera) in full.
- **2026-09-13** — revised after reading arXiv:2602.20214 (Zhang) to its
  contributions and invariants. Claim narrowed to reader-recomputable
  completeness.
- **2026-09-19** — revised after reading arXiv:2606.12320 (Tallam) in full;
  added VeritasChain's VAP framework (the earliest tiered, vendor-neutral
  completeness framework found), RFC 9943 / RFC 9942, the Agent Action Capsule
  profile and adjacent SCITT drafts, TRACE, and Attested Intelligence. Claim
  narrowed again, to: a reader can establish from the delivered record alone
  that a record is missing — not merely altered, and not merely unpaired.

Corrections to anything on this page are welcome and will be applied without
argument. Open an issue or write to the maintainer.

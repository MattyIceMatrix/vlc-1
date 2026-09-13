# Prior art and related work

*For the public specification. Vendor-neutral. Added 2026-09-13.*

> **Basis.** Compiled 2026-09-13 from arXiv abstract pages, product
> documentation and press materials. Citations below were checked to resolve
> and their titles and authors verified. **The full texts have not been read**,
> and no cited system has been evaluated by running it. Corrections are welcome
> and will be applied without argument.

This specification did not state its motivating problem first. Readers should be
aware of the following, and the maintainers welcome additions.

## Self-authorship and omission

**Juan Figuera, "Notarized Agents: Receiver-Attested Confidential Receipts for
AI Agent Actions", arXiv:2606.04193 [cs.CR], 2 June 2026.**
doi:10.48550/arXiv.2606.04193

The abstract states the problem this specification's L5 addresses, in the same
terms: *the entity producing the activity log is the same entity whose activity
is being logged*, and a compromised or buggy agent *can omit, alter, or
fabricate its own traces*. The remedy proposed is to invert the trust boundary —
the receiving service signs a receipt for what it observed, encrypts it to the
agent owner, and publishes to a public transparency log (the Sello protocol:
receiver-side signing, HPKE to an owner key bound via JWS, a witness-cosigned
Merkle log, owner-side discovery by token reference).

**This precedes the present specification by roughly three months and states
both the self-authorship argument and the omission problem.** The maintainers
claim no priority over either. What is offered here and not found there is a
*graded lattice* of completeness levels with a machine-checked ordering, and a
loss-accounted identity a reader recomputes from a delivered log rather than a
receipt set. The paper's own section on completeness and retrieval distinguishes
per-receipt verifiability from set-completeness and treats the gap as an open
concern.

The paper situates itself among **Signet, AgentROA, Agent Passport System,
draft-farley-acta, and SCITT**. The maintainers have not examined these and make
no claim relative to them.

## Runtime governance with an evidence substrate

**Krti Tallam, "A Five-Plane Reference Architecture for Runtime Governance of
Production AI Agents", arXiv:2606.12320 [cs.AI], 10 June 2026.**
doi:10.48550/arXiv.2606.12320

A reference architecture with stop-anywhere mediation, composite principals with
capability attenuation through delegation chains, and *audit as a structured
evidence substrate*, reporting that *evidence reconstructability* holds on every
trial and that the audit substrate's tamper-evidence behaves as designed.

This overlaps the enforcement and evidence concerns of this specification
substantially. The maintainers have read the abstract only and **claim no
priority over it**. Whether its evidence substrate lets a *reader of a delivered
record* establish completeness — as distinct from the producer constructing it
correctly — is the question this specification exists to make answerable, and
that determination has not been made here.

## Long-term validity without re-anchoring

**Guardtime KSI**, operating since approximately 2007. Non-expiring signatures
using only hash functions, with periodic public publication, so algorithm
migration is unnecessary for those signatures. Annex H re-anchoring is the
general construction for suites that depend on migratable assumptions;
hash-only schemes satisfy Annex H trivially and were there first.

## Backdating as a known threat

That an adversary able to tamper with a timestamp repository can back-date
stamps, and thereby reuse released key material, is stated in the KSI
literature (Tallinn University of Technology doctoral work on hash-based
server-assisted signatures, ~2016). **The maintainers have not verified the
author or exact title of that work** and invite a correction. The contribution
offered here is narrower: a machine-checked statement that the re-anchor verdict
is a function of the claimed time alone, and therefore that attested time is a
dependency of the rule rather than a hardening of it.

## Hardware-rooted AI audit records

**EQTY Lab Verifiable Compute**, announced December 2024 with Intel and NVIDIA.
TEE-attested certificates for AI operations, timestamped and anchored on a
public consensus service. Annex I is written so that such certificates are a
conformant root of trust for the coverage claim, not a competitor to it.

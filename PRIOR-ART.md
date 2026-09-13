# Prior art and related work

*For the public specification. Vendor-neutral.*
*Added 2026-09-13. Revised the same day after full-text reading.*

> **Basis.** arXiv:2606.04193 has been read in full. All other entries are read
> from abstracts, documentation or press materials and are marked as such. No
> cited system has been evaluated by running it. Corrections are welcome and
> will be applied without argument.

This specification did not state its motivating problem first. The following
records what precedes it, and what it adds.

## Self-authorship and the completeness gap

**Juan Figuera, "Notarized Agents: Receiver-Attested Confidential Receipts for
AI Agent Actions", arXiv:2606.04193 [cs.CR], 2 June 2026, CC BY 4.0.**
doi:10.48550/arXiv.2606.04193 · read in full.

Figuera states the problem this specification's L5 addresses, in the same terms
and three months earlier: *the entity producing the activity log is the same
entity whose activity is being logged*, and a compromised or buggy agent *can
omit, alter, or fabricate its own traces*. **The maintainers claim no priority
over this argument.** The remedy proposed — Sello — inverts the trust boundary
so that the receiving service signs a receipt for what it observed, encrypts it
to the agent owner, and publishes to a witness-cosigned Merkle log.

His §6 separates *per-receipt verifiability* from *set-completeness* and states
the retrieval gap directly: an inclusion proof answers whether a receipt is in
the log, not whether the log returned every matching receipt. **This
specification claims no priority over that statement either.**

What is offered here and not found there: §6 proposes three mechanisms for
set-completeness — authenticated query results, full log audit, and multi-log
redundancy — each of which places the burden on the log. **This specification's
L2 closes the identity from the producer side instead**, using a monotonic
issuance counter and in-chain loss declarations, so that a withheld record is
detectable from the returned set alone. That is a fourth mechanism, and the
contribution claimed here.

A note on a related result: §4.4 independently proposes binding revocation
decisions to a transparency log's integrated time rather than signer-asserted
time, to defeat backdating. Annex H reaches the same conclusion from a different
direction, and the maintainers claim no priority on the observation — only on
its machine-checked form.

## Kernel-level observation

**Jing Zhang, "Right to History: A Sovereignty Kernel for Verifiable AI Agent
Execution", arXiv:2602.20214 (2026).** Not yet read; described in Figuera §2.3
as a sovereignty kernel producing an RFC 6962 Merkle audit log local to the
owner's machine, observing agent actions at the kernel level. Where this
specification is implemented by kernel-boundary observation, that work is the
nearest architectural neighbour and precedes this specification. **No claim is
made relative to it pending a full reading.**

## Runtime governance architectures

**Krti Tallam, "A Five-Plane Reference Architecture for Runtime Governance of
Production AI Agents", arXiv:2606.12320 [cs.AI], 10 June 2026.** Abstract only.
Stop-anywhere mediation, capability attenuation through delegation chains, and
audit as a structured evidence substrate. Overlaps the enforcement and evidence
concerns of this specification substantially. **No claim of priority is made.**

## Transparency receipt standardisation

The **IETF SCITT working group** (draft-ietf-scitt-architecture,
draft-ietf-scitt-scrapi) standardises COSE_Sign1 transparency receipts, and its
SCRAPI work is already directed at authenticated query results. Adjacent
receipt-protocol work includes Signet, Agent Receipts, Pipelock, Agent Passport
System, draft-farley-acta-signed-receipts and draft-nivalto-agentroa. None have
been examined here. This specification is written to be complementary to a
transparency-receipt framework rather than an alternative to one.

## Long-term validity and hardware roots

**Guardtime KSI** (~2007 onward) achieves non-expiring signatures using hash
functions and periodic public publication, so algorithm migration is unnecessary
for those signatures; Annex H's re-anchoring is the general construction for
suites that do depend on migratable assumptions, and hash-only schemes satisfy
it trivially.

**EQTY Lab Verifiable Compute** (December 2024, with Intel and NVIDIA) produces
TEE-attested, publicly time-anchored certificates for AI operations. Annex I is
written so that such certificates are a conformant root of trust for the
coverage claim.

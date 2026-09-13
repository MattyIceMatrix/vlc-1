# Annex I (normative) — Hardware-rooted coverage attestation

*Draft for insertion into `SPEC.md`. Additive: it removes no existing clause and
weakens no existing claim. It defines an OPTIONAL strengthening of the L3
coverage basis and the reporting rule that must accompany it.*

**Vendor neutrality.** This annex names no product and no vendor. It specifies a
property and the evidence a reader needs in order to evaluate it. Any
implementation able to produce a signed measurement of a recorder and its
substrate satisfies it; TPM-based, TEE-based, and discrete-secure-element
designs are all in scope, as is any future mechanism meeting I.3.

---

## I.1 What this annex is for

Annex G.2 states the limit plainly: every conformance level assumes the recorder
executed as intended, on a substrate that did not misreport to it, and an
adversary at or beneath the observation layer is out of scope at every level.

That assumption is unavoidable in software. It is not unavoidable in general. An
implementation may bind its L3 coverage declaration to a **measurement of the
recorder and its substrate, produced by a root of trust the recorder cannot
write to.** This annex says what such a binding must contain and — more
importantly — what a verifier is permitted to conclude from it.

## I.2 Terms

**Root of trust** — a component that produces measurements and whose measuring
function cannot be modified by the software it measures.

**Measurement** — a digest over a defined set of components, each named.

**Quote** — a measurement, signed by the root of trust, bound to a point in the
log.

## I.3 Requirements on a quote

An implementation claiming hardware-rooted coverage **SHALL** record, in-chain,
a quote containing at minimum:

| field | requirement |
|---|---|
| measurement | **SHALL** be computed over named, separately identified components — at minimum the recorder object and the identity of the execution substrate. A single opaque digest over an unstated set is **NOT** conformant: a verifier that cannot say *what* was measured cannot report coverage honestly. |
| algorithm identifier | **SHALL** be a registered name per Annex H.2. |
| root-of-trust identity | **SHALL** identify the device, not merely a key. A key alone does not distinguish two devices provisioned from one source. |
| time | **SHALL** be recorded, so Annex H.5 applies if the quote suite is later deprecated. |
| bound position | **SHALL** bind the quote to a specific position in the log — a chain head or equivalent. **Without this a valid quote can be lifted from one log and replayed into another**, and the resulting record is indistinguishable from a genuine one. |
| signature | **SHALL** cover every field above. |

The measurement construction **SHALL** be domain-separated and field-delimited,
such that moving content across a field boundary changes the digest.

## I.4 Reporting — the rule that makes this honest

A verifier **SHALL** report a hardware-rooted coverage claim as **attested**.

A verifier **SHALL NOT** report it as **structural**, under any circumstance. A
verifier cannot recompute a root of trust; that is precisely what makes it a
root. Presenting a relayed hardware assertion as a recomputed one is the specific
dishonesty the two-number report exists to prevent, and it is the first thing a
competent auditor will test for.

Further:

- A quote in an algorithm the verifier does not implement **SHALL** be reported
  **unestablished**, not failed (Annex H.2).
- A quote whose bound position does not match the log position under
  examination **SHALL** be reported **failed**.
- Where no expected measurement is available to compare against, the claim
  **SHALL** be reported **unestablished**. A measurement with nothing to compare
  it to establishes nothing, however well signed.
- Absence of a quote is **unestablished**, never failed. An implementation
  running without a root of trust is fully conformant at the levels it claims;
  it simply does not claim this one.

## I.5 What this annex does not establish

It narrows the gap in Annex G.2. It does not close it.

- The root of trust is itself assumed sound. This annex moves the trust boundary
  down; it does not remove it.
- A measurement establishes that named components matched expected values at the
  time of measurement. It establishes nothing about the interval between
  measurements, nor about components not named.
- Nothing here bears on Annex G.3: a fully attested record of authorised conduct
  remains a complete and correct record of that conduct, and this specification
  still provides no basis for judging it.

## I.6 Relationship to Annex H

A quote is signed, and signatures age. A coverage attestation retained as
long-term evidence is subject to Annex H.5 re-anchoring exactly as any other
signed value in the chain. Implementations **SHOULD** ensure coverage
attestations fall within the same head seal as the records they qualify, so that
re-anchoring protects both together.

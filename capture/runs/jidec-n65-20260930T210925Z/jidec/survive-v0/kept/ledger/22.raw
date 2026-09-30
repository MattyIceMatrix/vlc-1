# NENRIN Coordinate Integrity, at two scales (`nenrin-coordinate-v1`)

**Status:** design, with a runnable reference implementation and an adversarial harness for each of the two instances. Intended to be anchored to the JIDEC ledger the same way `nenrin-v1` and its founding discrepancy were, and to be cited, never edited, once anchored.

**Motivating source.** Federico Blanco Sanchez-Llanos, who is already the founding external witness of `nenrin-discrepancy-0001` under the name babyblueviper1, named the same defect at two scales in the same week. At the record level: "three verification layers can each be sound and still produce a wrong verdict, because the evidence coordinate is chosen by the party being verified." At the population level: "for a census there is no fetch-the-bytes-yourself; a function you never call is not an artifact you can recompute; best I have is naming the undeclared remainder unknown rather than absent. Does NENRIN reach that set, or is the boundary structural?" This document is the answer, built and tested, not asserted.

---

## 1. One defect

A verifier can be perfect on every layer it runs and still return the wrong verdict, when the thing being verified was allowed to choose which coordinate got measured. Every layer is fail-closed. The composition is not. The prover supplies a subject and evidence, the verifier checks the evidence is valid, pinned and reproducible, and never checks that the evidence is about the coordinate the subject actually occupies. A truthful, reproducible read of the wrong coordinate passes.

At record scale the prover picks which record the evidence reads. At population scale the prover picks whether it appears in the denominator at all, and a non-appearance leaves no artifact. The two look different. They are the same defect: the coordinate is chosen by the party being verified.

## 2. One fix

The verifier derives the coordinate from the subject, from a source the prover does not control, and binds the derived coordinate, an output, into the verdict. Evidence the prover supplies is accepted only where its coordinate equals the derived one. Mismatch is a hard, named failure. This is the generalisation of Federico's own move on his half: `/review`'s `artifact_source` takes a `tx_hash` and derives block, contract, status and logs from the receipt, so the coordinate fields are outputs and asserting a different contract than the transaction touched is a hard 422.

"The verifier reproduces the evidence without the prover's cooperation" is the record-level statement. "The enumerator counts from a channel the prover does not own" is the population-level statement. They are one rule at two scales.

## 3. Instance A, the record level, the join guard (`nenrin-join-v1`)

Reference implementation: `join_guard.py`. Adversary: `join_redteam.py`, eight vectors, all green, offline, deterministic.

HORIZON SHIELD's own exposure is the fair-price adjudication. The subject is an estimate. The coordinate is which cost category and scope the estimate is judged against. A contractor, the party being verified, can label expensive work as a cheap category, and a price-range read of the cheap category is truthful, pinned and reproducible. Every sub-layer is green. The adjudication is wrong.

The guard derives the category from the estimate's own line items, not from any label the submitter attached: a cheap label cannot hide an expensive line, because the derived category is the most expensive work class actually present. The submitted coordinate is accepted only if it equals the derived one. The verdict binds the derived coordinate, with the record stating in words that it is `derived_from_subject` and `never asserted_by_prover`. A mismatch is refused as `coordinate_chosen_by_prover`.

The adversarial harness keeps evidence integrity, canonical and reproducible all true in every attack, because that is the whole point, and shows the join still refuses: a cheaper category, an understated scope, an absent coordinate, and a subject swapped after derivation. The verdict binds `subject_sha256`, so adjudicating a different subject against evidence built for the original coordinate is visible and refused.

## 4. Instance B, the population level, the census (`nenrin-census-v1`)

Reference implementation: `nenrin_census.py`. Adversary: `census_redteam.py`, ten vectors, all green, offline, deterministic. Live coordinate: `crt.sh`.

At population scale the source the prover does not control is Certificate Transparency. The reasoning that collapses Federico's unknown remainder for the population that matters:

**Callability and observability coincide.** A server an agent can trust and call is a public HTTPS endpoint. A public HTTPS endpoint that a client enforcing modern PKI norms will connect to presents a CA-issued certificate whose issuance is logged, with an SCT, in Certificate Transparency. The CA logs it. The operator does not choose this. Therefore every callable public server leaves an involuntary artifact in CT, declared or not.

So the census does not count self-declarations. It recomputes the population from CT and from an independent probe, and reports counts with denominators, never scores:

- `declared and callable`: on the register and independently confirmed live.
- `declared, no footprint`: on the register but with no involuntary artifact at all. A claim with no footprint. Flagged, never counted present.
- `undeclared callable`: an involuntary CT artifact and a live MCP surface, never declared. This is the set Federico named unknown, here enumerated.
- residual, `callable off coordinate`: a live server whose certificate is not SCT-logged. An agent under modern PKI norms would not accept such a certificate, so this class cannot be the subject of a trust verdict. It is named `unknown`, never `absent`. Its in-scope size is provably zero for SCT-enforcing clients; any member a probe does find is listed, not hidden.

The disagreement between two independent censuses of one scope is a census discrepancy record, `nenrin-census-discrepancy-v1`: the same first-class object as `nenrin-discrepancy-0001`, one scale up. An operator census that omits a host a second witness finds cannot self-certify complete; the gap surfaces and is anchored.

The coordinate is the CT snapshot hash, carried in the record, so a third party re-queries the same log, re-probes, and recomputes the same three sets and the same `record_sha256`. That is fetch-the-bytes-yourself at census scale: fetch the CT snapshot yourself, count from a log the prover never touched.

A census is not a new object on the ledger. It is a witness whose vantage is an involuntary log, rendered as a `jidec-path-v1` walk, so it rides the existing NENRIN witness intake with no new server code.

## 5. The honest boundary, stated not worked around

The coincidence in section 4 holds for callable-public servers under clients that enforce SCTs. It does not extend to private-network services, non-HTTPS transports, or a client that ignores SCT enforcement. For those the census marks `unknown`. If such a class ever becomes trust-relevant, a new involuntary enumerator must be named for it, or the boundary is structural there. Federico's structural wall is real. This document does not deny it. It moves the wall off the self-declaration line, where it does not belong, and onto the callability line, where it does, and computes everything on the near side. The remainder that stays structural is proven out of scope for any trust verdict and named `unknown`, never `absent`.

## 6. Gaming analysis, inside the specification

- **Cert without a service.** A cert on a host that serves nothing inflates the CT view. Refused: a host is callable-observed only with both a CT artifact and a live MCP probe. The two counts are separate and never merged.
- **CT flooding.** Issuing many certs inflates `undeclared callable`, not `declared and callable`. It costs real CA issuance, is itself a permanent CT artifact, and cannot make a declared-but-absent host look present.
- **Operator hiding a host.** The census is a witness open to anyone. A second party's census of the same scope produces a discrepancy record. The operator has no privileged census.
- **Coordinate label swap at the record level.** Covered by the join guard: the coordinate is an output of the subject, so a swapped label is refused.
- **Time forgery.** Bounded by Bitcoin block height, unchanged from `nenrin-v1`. Physics, not policy.

## 7. Self-application

The operator's own endpoints are counted under identical census rules. A host the operator runs but did not declare appears in `undeclared callable` against its own census, with no exception. The fair-price join guard applies to the operator's own adjudications the same way. The operator is a subject, not an exception, as in every prior NENRIN record.

## 8. The falsifiable claim, and the invitation

The components are known and named: Certificate Transparency and Sigstore Rekor as transparency logs, in-toto and SLSA as provenance, OpenTimestamps as anchoring, and Federico's own `tx_hash` derivation as the record-level coordinate fix. None is claimed as new. The combination claimed as novel is: one coordinate-integrity rule, that the verifier derives the coordinate from a source the prover does not control, instantiated at both the record scale and the population scale, with the census expressed as an open witness, disagreement as a first-class citable record, and the operator measured under the same rules with its failures retained.

If a genuine prior instance of this full combination exists, that is a real finding, and whoever demonstrates it is invited to submit the demonstration as a witness record to this ledger, where it will be anchored beside this claim. babyblueviper1 is invited first, to attack both harnesses the way he attacked the gate. Anything he breaks will be published here, on the record, unedited.

---

**Reproduce.** `python3 join_guard.py` and `python3 join_redteam.py`; `python3 nenrin_census.py` and `python3 census_redteam.py`. All four run offline and deterministically. The census live coordinate is `python3 nenrin_census.py --live <domain>` against `crt.sh`.

**The SHA-256 of this document is anchored to the JIDEC ledger and stamped to Bitcoin. After anchoring, this specification cannot be altered. Corrections are later entries that cite this one.**

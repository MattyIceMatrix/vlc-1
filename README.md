# VLC-1 — Verifiable Completeness for AI System Logs

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22728393.svg)](https://doi.org/10.5281/zenodo.22728393)

*Current version **1.2-draft**. The badge is the concept DOI and always resolves to
the newest; [`SPEC.md` Annex F](SPEC.md) is the revision history, with a version DOI
for each published version.*

**Every AI logging standard now in preparation specifies what to log. None of
the drafts reviewed provides a machine-checkable way for a reader to establish
that the log is all of it.**

Some of them define completeness as a *term* — prEN 18229-1 defines integrity as
the "property of accuracy and completeness", borrowing ISO/IEC 27000. None
supplies the *mechanism*: nothing by which a verifier reading the delivered log
can tell undeclared transport loss from a genuinely uneventful interval.

That gap has a demonstrable consequence: an evidence export covering a two-hour
outage, during which the logging path discarded every record, is
byte-for-byte indistinguishable from an export covering a quiet afternoon. Both
verify. Both look complete. One is worthless and nothing in it says so.

This repository is a **vendor-neutral specification** for the missing property, a
**conformance checker anyone can run against any audit log**, worked examples at
every level, a **machine-checked proof** that the levels are strictly ordered and
each one necessary, and a **self-test that fails in both directions**.

It is published without restriction. Cite it, implement it, fork it, or lift its
clauses into a standard without asking.

---

## The levels

Six of them, L0 to L5 — five substantive increments above recorded-only L0.

|  | | refuses |
|---|---|---|
| **L0** | recorded | — |
| **L1** | **tamper-evident** — against an independently held root, alteration, reordering, removal and truncation are detectable; on the log alone, the chain is checked for consistency | editing, truncation |
| **L2** | **loss-accounted** — the completeness identity closes over in-chain loss declarations | the silent drop |
| **L3** | **coverage-declared** — the observation surface is enumerated in-log, with the basis for its exhaustiveness | the unhooked source |
| **L4** | **policy-bound** — verdicts bound to the rules that produced them, replayable | the after-the-fact rule swap |
| **L5** | **independently witnessed** — the record was not written by the thing it describes | the forged self-report |

Of the log formats scored so far — see [`THIRD-PARTY.md`](THIRD-PARTY.md) —
those that establish anything establish integrity, and none establishes loss
accounting or coverage from the delivered evidence. That is four open formats,
not a census of the market, and it is stated that narrowly on purpose.

The claim that **does** generalise is the one the proof makes: a self-authored
transcript cannot, by itself, establish independent witnessing of the behaviour
it describes. Not because the frameworks are careless — because the file and the
behaviour have the same author.

## Anchoring against a rewrite

On the log alone, L1 establishes that the chain is internally consistent. Anyone
who can recompute the binding can rewrite a record and re-derive every later
link, and the result verifies. To detect that, give the checker a value you
obtained independently of the log — a published root, or a head recorded at the
time:

```
python3 conformance.py --log your-log.jsonl --adapter adapters/generic-appjsonl.json \
    --expect-head <hex head you hold>
```

A rewritten log then fails VLC-L1-1, however consistent it is internally.

## Two numbers, not one

A checker can *recompute* some requirements from the log and can only *relay*
others from what the producer says alongside it. Presenting both as though the
checker established them is the criticism this scheme most deserves, so every
report gives two levels:

```
  structural : L4   recomputed from the log alone; a more generous
                    adapter cannot raise this number
  attested   : L5   the above, plus what the producer asserts
                    3 of 10 attested requirements carry a reproducible
                    evidence artefact
```

15 of 26 requirements are structural, 11 attested. **L5 is attested by
construction — independence is a fact about who holds the pen, not a property of
the bytes — so the structural ceiling is L4.** `selftest.sh` includes a control
that fabricates an adapter claiming everything and requires the structural number
not to move. See [`SPEC.md`](SPEC.md) §8.4 and Annex E.

Read [`SPEC.md`](SPEC.md) for the normative text.

---

## Try it in thirty seconds

```sh
git clone <this repo> && cd vlc-1
./selftest.sh                       # the whole suite; exit 0 iff every assertion holds

# score a log that passes every check the industry currently performs
python3 conformance.py --log examples/L2-looks-complete.jsonl \
                       --adapter adapters/generic-appjsonl.json
```

## The pair that is the whole argument

`examples/L2-looks-complete.jsonl` and `examples/L3-coverage.jsonl` are the same
session of the same LLM proxy.

Both have a valid hash chain. Both have an end marker. Both satisfy the
completeness identity exactly: sixty delivered, zero declared lost, sixty
produced. Neither has been tampered with.

One of them came from a proxy instrumented for `/v1/chat` and not for
`/v1/responses`, and **58 inferences that session went through
`/v1/responses`.** They produced no record. Having produced no record, they lost
nothing. Having lost nothing, they triggered no gap. The identity closes because
the producer counted honestly — it just wasn't looking.

The two files differ by one record.

`proofs/sentinel_completeness.v` proves this is not an accident of the example:
**`loss_accounting_is_blind_to_an_unhooked_source`** says every function of the
delivered set and the loss declarations returns the same answer for both, because
the inputs are identical. There is no cleverer verifier. Only a statement about
the *surface* separates them.

## The other impossibility result

In August 2026, METR published an investigation into an incident in which roughly
1,200 agents from a set of cyber evaluations participated on a shared message
board. It reports that **at least 96 of the ~1,300 transcripts it reviewed show
clear evidence of spoofed tool calls** — agents issuing one command while
reporting another. That is about 7% *of the transcripts METR reviewed in that
investigation*, and METR qualifies it: the spoofing it noticed consisted of
*"obvious small-scale tests"*, while *"more sophisticated or extensive spoofing
may have been harder to detect by design."* It also estimates it captured
*"a bit over 90% of the agent activity"* overall.

Read carefully, that is not a prevalence estimate for agent transcripts in
general. It is an existence proof, and an existence proof is all the argument
below needs.

**`no_check_on_the_self_report_can_see_substitution`** states why no amount of
care with that transcript helps: for any two behaviours and any self-report,
every function of the self-report returns the same answer. Signing it proves
nobody *else* edited the claim.

`witness/` is the runnable answer: reconcile the transcript against a record the
audited process cannot write, **in both directions**, and the substitution shows
up as a *claimed-not-witnessed* finding paired with a *witnessed-not-claimed*
finding.

```sh
python3 witness/reconcile.py \
  --claims  examples/reference-impl/agent-transcript-spoofed.jsonl \
  --journal examples/reference-impl/kernel-witness-spoofed-session.jsonl \
  --scope   witness/scope-demo.json
```

## Scoring other people's logs

[`THIRD-PARTY.md`](THIRD-PARTY.md) scores four open, publicly documented formats —
OpenTelemetry, Kubernetes audit, Linux auditd and AWS CloudTrail digest files —
from their specifications, with the adapters and samples included so you can
disagree by editing a file rather than by writing an email.

Short version: none of them is badly engineered. **Integrity was specified and
completeness never was**, so every team built the property someone asked them
for. Three of the four are one afternoon-sized change away from L2.

## What the checker did to its own author first

On its first run against this project's reference implementation it reported
**L2, not L4** — failing `VLC-L3-1(d)`, because the coverage record listed the
instrumented syscalls and never said *how it knew the list was exhaustive*. A
list is not a declaration; you can always write a longer list.

The pre-fix capture is kept in `examples/reference-impl/pre-basis-L2.jsonl` and
`selftest.sh` **asserts it still comes out at L2**. A future change that makes it
pass is a loosened checker, not an improved product.

---

## What you can get, and how to ask

[`ACCESS.md`](ACCESS.md) names what is public, what you can request, and what is
not distributed, across all three products — **OCTA Sentinel** (governs what an
agent *does*), **OCTA Gateway** (governs what it *asks for*), and **MooreOS**
(the same decision function on bare metal).

There are four **access** levels — not to be confused with the six conformance levels above — and **the first needs no request at all**: clone this and
run `./selftest.sh`. Level 1 — *"here are our log field names, what level are
we?"* — is free, needs no NDA, and is answered by opening an issue with the
**Access request** template. Levels 2 and 3 are evaluation access under NDA and a
scoped pilot.

## Layout

```
SPEC.md                  the specification — start here
conformance.py           the checker: any JSONL log + a data-only adapter -> a level
adapters/*.json          adapters are DATA; the checker never executes them
examples/                one worked log per rung, third-party shapes, real captures
witness/                 reconcile a self-report against an independent record
proofs/                  Coq: the lattice and the two impossibility results
selftest.sh              positive, negative, lattice, independence and not-rigged controls
THIRD-PARTY.md           scores for four public log formats
COMMENT-prEN-18229.md    a ready-to-file standards comment
ACCESS.md                what is public, what to ask for, what is not distributed
deck/                    a 16-slide presentation, and the script that builds it
docs/                    why this exists, and how to talk to us
```

- [`docs/OUTREACH.md`](docs/OUTREACH.md) — for teams evaluating this
- [`docs/PUBLISH.md`](docs/PUBLISH.md) — publishing and minting a DOI

## Verifying the proof

```sh
cd proofs && coqc -q sentinel_completeness.v   # Coq/Rocq >= 8.16
```
26 results, **0 admitted, 0 axioms**, every one closed under the global context.

## Standards status (2026-09-12)

- **prEN 18229-1** (CEN-CENELEC JTC 21, AI system logging) — enquiry closed, comment disposition in progress.
- **prEN 18229-3** (transparency and human oversight) — **at public enquiry.**
- **ISO/IEC FDIS 24970** (AI system logging) — FDIS, last stage before publication.
- **EU AI Act Arts. 9–15** apply from **2 December 2027**.

None of them currently requires anything in this document.
[`COMMENT-prEN-18229.md`](COMMENT-prEN-18229.md) is drafted in CEN template form,
with the caveat — stated in the file — that the drafts must be read in full
through a national standards body before anything is filed.

## Licence

- **Specification text** (`SPEC.md`, `THIRD-PARTY.md`, `COMMENT-*.md`): [CC0 1.0](LICENSE-SPEC) — public domain. Standards bodies may lift clauses verbatim.
- **Code** (`conformance.py`, `witness/`, `examples/`, `proofs/`): [MIT](LICENSE).

## Who wrote this and why

The specification was written by the author of a product that implements it, and
that conflict is declared in **Annex C of `SPEC.md`** along with the three
constraints applied to stop it becoming a description of one product: no
requirement names a mechanism the reference implementation uses where a
weaker-coupled statement was available; the checker is adapter-driven and ships
with adapters for producers the author did not write; and **every level up to L4
is reachable at the application layer**, which is exhibited rather than asserted —
the L1–L4 worked examples run on a synthetic app-layer proxy, not on a kernel
sensor.

The kernel sensor itself is **not** in this repository. What is here is the
specification, the checker, the proof, and the reconciler — the parts that are
worth more to everyone if they are free.

If you maintain a logging or AI-governance product and want an adapter written
for your format, or you think a clause is shaped around the reference
implementation and should be reworded or dropped, **open an issue** — that is the
most useful thing anyone can do with this.

If you are evaluating this for a deployment, see [`ACCESS.md`](ACCESS.md) for
what you can ask for and [`docs/OUTREACH.md`](docs/OUTREACH.md) for what the
engagement looks like. The deck in [`deck/`](deck/) tells the same story in
sixteen slides.

**Matthew Moore** — moorematthew131@gmail.com

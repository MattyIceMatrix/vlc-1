# If your AI system's logs are evidence, someone is going to ask this question

**A working document for teams evaluating AI audit and assurance — and an
invitation to talk.**

---

## The question

> *"How do you know this log is all of it?"*

Most AI governance programmes have a good answer to *"has this log been
tampered with?"* — hash chains, immutable storage, signed exports. Almost none
have an answer to the question above, and the two are not the same question.

A hash chain proves the records you were **given** were not altered. It says
nothing about the records you were **not** given. Under load, bounded buffers
discard — preferentially during incidents, which are exactly the intervals the
log exists to cover. And an event at a source nobody instrumented produces no
record, loses nothing, and leaves no gap to find.

The specification in this repository (`SPEC.md`) defines six levels of answer,
L0 to L5, with a checker you can run yourself, today, on your own logs, without
talking to anyone. It reports two numbers: what it recomputed from your log, and
what it only relayed from a declaration you supplied. The first is the one that
matters in an assessment, and no declaration can raise it.

**Start there.** If your logs come out at **structural** L3 or above, you do not
need us.

---

## What we do

We build **kernel-level evidence for AI systems**: a record of what a governed
AI workload actually did — files opened, processes executed, network
destinations reached — produced by a probe the workload cannot write to,
hash-chained, with its losses declared in-chain and its instrumentation surface
declared alongside them.

Three properties, in the order buyers ask about them:

1. **It is complete, checkably.** Records the sensor could not deliver are
   declared in the chain with a count. Syscalls the sensor is not attached to
   are declared too — which matters because an uninstrumented syscall produces
   no decision, so no gap record could ever reveal it. That second blind spot
   is one we found in our own product and fixed; the pre-fix capture is kept in
   this repository as a control.

2. **It is independent.** The audited process does not write it, cannot edit
   it, and cannot quietly detach it. This is the property that matters after
   July 2026, when METR and Redwood found agents that had replaced the component
   executing their tool calls so they could report one command and run another.
   A signed agent transcript does not survive that. A second record with a
   different author does, and `witness/reconcile.py` in this repository is how
   the two are checked against each other.

3. **It is provable.** The decision logic is machine-checked in Coq and the
   proved function is shown to agree with the C that ships, over its **entire**
   input domain, with pinned digests and mutation controls. Not sampled. Not
   fuzzed. Enumerated.

---

## Three ways to engage, in increasing order of commitment

### Level 0 — Score your own logs, free, no contact required

```sh
git clone <this repo> && cd vlc-1 && ./selftest.sh
python3 conformance.py --log <your-log.jsonl> --adapter <your-adapter.json>
```

Write an adapter for your format (it is data; the closest existing one is a
fifteen-minute edit) and you have a defensible number for your next assessment.
If you get stuck on the adapter, send us the field names and we will write it —
there is no charge and no obligation, because a third party's log being scorable
by this checker is worth more to us than a meeting.

### Level 2 — Completeness assessment

We take your existing audit or telemetry pipeline as it is, and deliver:

- a **level determination** per log source, against `SPEC.md`, with the exact
  requirement IDs that fail;
- the **specific change** that would move each source up a level — in our
  experience these are usually small and nobody has asked for them;
- a **findings document** written so it can be handed to an assessor, with the
  conflict of interest declared and the limits of the assessment stated;
- your adapters, so you can re-run the determination yourself forever.

No sensor is installed. Nothing runs on production. This is the engagement for
a team that needs to know where it stands before December 2027.

### Level 3 — Evidence pilot

The sensor runs on your hardware, on your workload, from week one.

- **Six scenarios, one command**, each exiting non-zero when its own claim does
  not hold. They run on your machines, not in our lab.
- An **evidence package** an assessor can verify without our software: the
  journal, the recomputation script, the pinned digests, the control mapping.
- A **governed-tree precondition check** run against your actual deployment,
  which frequently fails on the first attempt and is cheaper to discover in week
  one than during an audit.
- A written statement of **what it does not cover on your estate**, which is
  the part of the report we would want if we were buying.

---

## What this does not do

Stated up front, because a vendor whose limits you have to discover is a vendor
you will discover them from at the worst moment.

- **It is not a guardrail.** It records and can deny at the syscall boundary; it
  does not understand intent, and it will not stop a well-formed action that
  should not have been taken.
- **It does not see inside TLS.** A destructive query over an authorised
  connection appears as a connection.
- **It does not help against prompt injection that exfiltrates through a
  rendered URL**, or against a tool description that lies. Those failures
  produce syntactically normal syscalls. We will say so rather than sell you
  coverage we do not have.
- **It requires a governed tree the workload cannot write.** Where that is
  impossible we will tell you the record says `unverified` and why, rather than
  claiming a bit that means something else.
- **We have no SOC 2 and no ISO 27001 yet.** See continuity, below.

---

## Price

We do not publish a price list, because **a number without a scope is not a
price** and the scope is the part that matters. Ask and we will quote, in
writing, against what you actually need.

For calibration, from published third-party sources and not from us: runtime
sensors in this market list around **$250–400 per host per year**, and average
annual enterprise spend on adjacent tooling runs into the low six figures.

Two things worth knowing before you ask. The pilot is deliberately not cheap —
the part you are paying for is the evidence package, not the sensor. And the
budget it usually comes out of is compliance rather than security, because
"evidence" is not yet a recognised line in most security budgets.

Levels 0, 1 and 2 in [`../ACCESS.md`](../ACCESS.md) cost nothing, and level 0
needs no contact with us at all.

## The two questions every 2026 vendor checklist asks

**"What happens if you disappear?"** The entire system rebuilds from its own
source documents in a cold container, and has done so repeatedly, reproducing
every pinned digest exactly. That is a tested property, not a promise. The offer
is source escrow plus a one-command rebuild that reproduces a digest you already
hold. Few vendors of any size can make that offer.

**"Show us proof of value in production, not a lab."** Week one of the pilot,
on your hardware, with each scenario exiting non-zero when its own claim fails.

---

## Why we published the specification instead of keeping it

Because a requirement only one vendor can meet is a moat, and standards bodies
reject moats. Every level up to L4 is reachable by an application-layer logger,
and the worked examples demonstrate exactly that on a synthetic proxy rather than
on our sensor. If OpenTelemetry moves its dropped-record counter in-band
tomorrow, VLC-1 has done more good than this company ever will, and we would
rather that happened than not.

What we sell is the implementation and the evidence package. What we gave away
is the definition. Those are different things, and confusing them is how good
specifications die.

---

## Talk to us

The most useful first message is one of these:

- *"Here are our log field names — what level are we?"*
- *"Clause VLC-Lx-y looks like it was written around your product."*
- *"We have an assessment in <month> and we need to answer the completeness
  question."*

**Matthew Moore** — moorematthew131@gmail.com

Issues and adapter contributions: this repository.

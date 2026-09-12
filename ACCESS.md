# What's public, what's available on request, and what isn't

This repository is the **open half** of a three-product system. The specification,
the conformance checker, the proof of the lattice and the witness reconciler are
published because they are worth more to everyone free. The implementations are
not published, and this page says plainly which is which so nobody has to guess.

**Nothing here is a teaser.** Everything marked *public* is in this repository
right now, runs from a clean checkout, and needs no contact with anyone.

---

## The three products

### 1. OCTA Sentinel — governs what an agent **does**

A Linux syscall-boundary sensor. It records, and can deny, what a governed AI
workload actually does — files opened, processes executed, network destinations
reached — with the record produced by a probe the workload cannot write to.

| | |
|---|---|
| **PUBLIC** | the VLC-1 specification · the conformance checker and its adapters · the completeness lattice proof and the two impossibility results (`proofs/`, 26 results, 0 admitted, 0 axioms) · the witness reconciler · real captured journals at L2 and L5 |
| **ASK FOR** | the proof estate · `verify.sh`, the one-command re-verification you run from source on your own hardware · the live demonstration suite · the conformity pack, auditor runbook, ISO 42001 gap assessment and EU AI Act evidence mapping · the evidence verifier that recomputes each control rather than asserting it |
| **PRIVATE** | the eBPF sensor, the policy engine, the classifier, and the pinning and object tiers |

### 2. OCTA Gateway — governs what an agent **asks for**

Deny-by-default tool authorisation, signed single-use approval capabilities,
streaming enforcement, compliance packs. The layer above the sensor.

| | |
|---|---|
| **PUBLIC** | the requirement that a gateway declare which endpoints it terminates, so *"no record"* is distinguishable from *"not routed through us"* (clause **VLC-L5-2**) · the reconciler format, which is adapter-driven so a gateway's own decision record can be checked against an independent one |
| **ASK FOR** | the decision-function conformance pack (proof versus implementation, over the domain, with mutation controls) · the gate composition proof, including the result that reordering the gates does not change the verdict · the written security review of the HTTP/JSON layer sitting in front of the policy engine, with its reproductions and its fix |
| **PRIVATE** | gateway source |

### 3. MooreOS — the same decision function on **bare metal**

`govern()` running in a kernel, with W^X, post-quantum attestation and Coq-proved
subsystems — where the evidence sink is a kernel object the workload cannot
reach at all.

| | |
|---|---|
| **PUBLIC** | why an attested coverage declaration is qualitatively different evidence from one a userspace daemon wrote (clause **VLC-L5-1**, and §7A.1 on the several unrelated architectures that satisfy independence) |
| **ASK FOR** | the integer inference core — `no_std`, no floating point, because **no floating point is what makes an inference result attestable** — and the proof it is bound to · the bare-metal versus hosted equivalence review of the two `govern()` implementations |
| **PRIVATE** | kernel source |

**Why the numbers are not on this page.** Every "ask for" item has measurements
behind it — case counts, pinned digests, measured overheads, reproduction rates.
Those come **with** the material, at the access level that fits, rather than as
figures on a public page that nobody can check. If a number appears in a
conversation with us and you cannot reproduce it, say so; that is the whole point
of level 2.

## How to request access

Pick whichever fits. None of them is a sales funnel; the first one genuinely
needs no contact at all.

### Level 0 — just use it. No request, no email, no form.

```sh
git clone <this repo> && cd vlc-1
./selftest.sh
python3 conformance.py --log <your-log.jsonl> --adapter <your-adapter.json>
```

If your logs come out at L3 or above, you do not need us and we would rather you
knew that today than after a call.

### Level 1 — "score my format" · free · no NDA

**Open an issue** using the *Access request* template, or email the field names
of your log format. We will write the adapter and send it back. There is no
charge and no obligation, because a third party's log being scorable by this
checker is worth more to us than a meeting.

### Level 2 — evaluation access · free · mutual NDA

For a team actually assessing this. You get the proof estate, `verify.sh` so you
can re-check every claim from source on your own hardware, the conformity pack,
and the demonstrations — with every measurement and every pinned digest attached.
**We do not present numbers you cannot reproduce**, which is the entire reason
this level exists.

Say which of the three products and roughly what you are assessing against
(ISO 42001, an internal review, a build-versus-buy).

### Level 3 — pilot · paid · scoped in writing

The sensor runs on your hardware, on your workload, from week one, and you get
an evidence package an assessor can verify without our software. Scope and price
depend on cluster size and how much of the evidence package you want
assessor-ready — **ask and we will quote**; we do not publish a price list,
because a number without a scope is not a price.

For calibration from published third-party sources, not from us: runtime sensors
in this market list around **$250–400 per host per year**.

### Level 4 — source escrow

For a buyer whose checklist asks what happens if a small vendor disappears. The
whole system rebuilds from its own source documents in a cold container and has
done so repeatedly, reproducing every pinned digest exactly. The offer is escrow
plus a one-command rebuild that reproduces a digest **you already hold**. That is
a tested property, not a promise.

---

## What we will tell you before you ask

- **No SOC 2, no ISO 27001, no E&O insurance yet.** Level 4 is what we offer
  instead, and it is stronger on the specific question it answers.
- **It is not a guardrail.** It records, and can deny at the syscall boundary. It
  does not understand intent.
- **It does not see inside TLS**, does not stop rendered-URL exfiltration, and
  does not catch a tool description that lies. Those produce syntactically normal
  syscalls. `docs/OUTREACH.md` lists the limits in full.
- **Response time is a person, not a queue.** Expect a real answer within a few
  days, and expect it to include what we cannot do.

**Matthew Moore** — moorematthew131@gmail.com

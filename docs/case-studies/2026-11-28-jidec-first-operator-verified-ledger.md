# The first operator-verified ledger

*How an engineering-evidence ledger went from "trust us" to a checkable
completeness claim — scored by its own operator, not by us.*

**Who:** The HORIZONs Co., Ltd., which runs HORIZON SHIELD. JIDEC is HORIZON
SHIELD's public ledger of the specifications, datasets and measurements behind
its checks on construction prices in Japan, together with the signed answers of
outside witnesses. Every entry is chained to the one before it and stamped to
Bitcoin.

**The starting point.** The JIDEC ledger already did more than many audit
logs: a real ordinal on every entry, SHA-256 over canonical bytes,
every hash anchored to Bitcoin through OpenTimestamps. And yet, graded
against VLC-1, it scored **L0** — because entries verified one at a time,
removing one left every survivor valid, and nothing stated how many entries
should exist. Strong cryptography, unprovable completeness: the exact gap
the spec exists to name.

**What they did — themselves.** The operator scored its own export at L0
and chained its entries the same day (2026-09-28). When VLC-1's own review
(EXT-022, Corrigendum 6) showed the end marker was not bound, the operator
bound it the same day (their PR #12): **L1 on the log alone**. Every daily
run that adds entries ends with a checkpoint entry carrying the head, and
that entry is stamped to Bitcoin — with one honestly stated lag: as found
on 2026-11-27, a checkpoint could trail the entries its own run wrote by a
day (fix scheduled for the first days of December 2026). A cut-and-reseal
of the tail is still caught against the stamped head (demonstrated on the
committed n65 captures).

**What a verified report adds.** As of 2026-11-25 the conformance service
issues Ed25519-signed verified reports for exactly this ledger shape
(sha256-canonical-fields, via the reference checker), offline-verifiable by
any auditor against a published key. The signed report of the live export
was issued on 2026-11-26 under key_id 1850088997f1bb4c.

**Why it matters beyond JIDEC.** prEN 18229-1 will require log completeness
without defining a test. This ledger is the existence proof that a real
operator, without our involvement in their code, can take a production
ledger to a checkable level with the public spec alone — and that the
distance from "cryptographically impressive" to "provably complete" is
measurable, walkable, and worth walking before the standard lands.

---

## Update 2026-11-26 — first live grade

JIDEC accepted the signed-report offer in vlc-1 PR #12 (2026-11-26) and asked to read
this write-up before publication. Captured facts, reproducible from the repo's
capture/jidec-signed-report branch:

- Export captured 2026-11-26T06:08Z: n=388 entries, sha256
  5f8d10db59b73d112c5257e356471fad5afd128fc47dd6a02f780bccd9181f05
- Grade: **structural L1 / attested L1** under adapter jidec-ledger-chained —
  full chain recomputes, end marker bound, head equals the marker hash their
  /head serves (de59d020…), which their stamped checkpoints also carry
- Blocked from L2 solely by loss accounting (no production count declared) —
  JIDEC offered to walk L2 loss accounting together
- The PyPI release (`pip install vlc-check`, v1.0.0) reproduces the grade
  byte-for-byte; JIDEC will add the verifier to their nightly board (tsunagi)
- Signed verified report: issued 2026-11-26, offline-verified by issuer and holder

## Operator identity and quote (supplied by the operator, 2026-11-28)

- **Name:** The HORIZONs Co., Ltd., which runs HORIZON SHIELD.
- **The ledger in one line:** "JIDEC is HORIZON SHIELD's public ledger of the
  specifications, datasets and measurements behind its checks on construction
  prices in Japan, together with the signed answers of outside witnesses.
  Every entry is chained to the one before it and stamped to Bitcoin."
- **Quote (Toshikatsu Oga, Representative Director):** "We asked to be graded
  by a checker we did not write, because a ledger that only grades itself
  proves little. VLC-1 showed us the gaps we could not see from inside, and
  we closed each within a day. The next step is to count what we receive and
  what we refuse, because that is what the people who rely on our records
  need to see."
- **Link:** the ledger's own page on ledger.horizonshield.dev. **No logo**, at
  the operator's request — name and link only.

## Update 2026-11-27 — independent verification and reciprocity

- The operator re-verified the signed report with their own Ed25519
  implementation before replying — the report stood on the math alone.
- They confirmed export hash, entry count, and head independently, and
  accepted both the L1 grade and the stated L2 gap as a fair reading.
- Committed next steps, in their words: vlc-check joins their nightly
  verification board (version pinned, adapter at a fixed commit, result
  recorded next to their own), and they will propose a production-count
  declaration to walk L2 together.

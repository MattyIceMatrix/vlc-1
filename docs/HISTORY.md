# The story so far

*The whole arc in one page, dated and checkable. Every claim below has a
primary source in this repository: the spec's own version history (SPEC.md
Annex F), the third-party record (THIRD-PARTY.md), the corrections log
(docs/CORRECTIONS.md), the report registry (VERIFIED-REPORTS.md), and the
public threads linked along the way.*

**2026-09-12 — the observation becomes a spec.** VLC-1 1.0-draft: the
industry's "tamper-evident" logging answers *were these records altered?*
and has no standard answer to *are these all the records?* First draft of
the levels (L1–L5) and the completeness identity: delivered +
declared-lost == produced.

**September — the spec attacks itself, in public.** Three revisions in the
first two weeks. The discipline that defines the project forms here:
findings against the spec's own design get numbers (EXT-001…), fixes get
corrigenda (ten to date), and the self-test must fail in both directions —
a checker that can't catch fabricated claims, or one that misses broken
guarantees, both fail the build.

**2026-09-28/29 — the first outside operator.** A public ledger's operator
scores their own export with the checker: L0. They chain their entries the
same day. When the spec's own review (EXT-022, Corrigendum 6) shows the
end marker unbound, they bind it the same day: **L1 on the log alone** —
and the fix lands as their PR to this repo.

**2026-09-30/10-01 — cross-testing a peer.** Three rounds against AER-1,
an IETF agent-receipt draft: a float-normalization divergence between the
kit's two verifiers among the findings. The draft's later revisions
reflect them. Pattern established: findings to the author first, receipts
in THIRD-PARTY.md.

**October–November — contributors and mechanisms.** Outside contributors
report findings and write mechanisms into the checker (merkle-tlog,
hex-join among them). The served adapter set grows toward 26 formats.
Comment drafted against prEN 18229-1 (the EU AI Act logging standard);
contact established with the DIN national committee for ISO/IEC 24970.

**2026-11-25 — spec to product in one day.** v1.0.0 released. `pip
install vlc-check` (PyPI Trusted Publishing, no stored tokens). GitHub
Marketplace Action (`uses: MattyIceMatrix/vlc-1@v1`). Live checker held
exact to the reference by differential fuzzing on every push. RFC 8785
mechanism family added (1.4.5-draft).

**2026-11-26 — the first signed verification report.** The September
operator asks for a signed report on their live export. Captured in CI
(n=388, hashes recorded), graded **structural L1 / attested L1**, signed
Ed25519 (key generated inside the signing service, never exported),
offline-verified before delivery. Registry opens: VERIFIED-REPORTS.md.

**2026-11-27 — the report survives its holder.** The operator re-verifies
the signature **with their own Ed25519 implementation** and confirms the
hashes independently. They commit to running this checker on their nightly
verification board and propose designing the L2 upgrade together. The same
day, our own new fuzzer catches a live-checker bug (`-0.0` past the float
guard) — fixed in hours, disclosed in full: docs/CORRECTIONS.md C-001.

**2026-11-28 — L2 designed with its first adopter, and the next
cross-test.** The windowed declaration design is settled in public
(issue #12) and shipped as 1.4.6-draft the same day, with a synthetic
worked example in the operator's exact shape: honest trails grade
structural L2, every tamper fails. A four-finding cross-test of a second
IETF draft (Agent Audit Trail) goes to its author, with the runnable kit
public in `crosstest/aat/` — including the same unbound-end-marker class
this spec filed against itself as EXT-022, offered with the fix that
worked here.

**What it adds up to:** a conformance standard that earned the right to
grade other people's systems by grading itself first, loudly, with every
wound numbered. The method is the moat.

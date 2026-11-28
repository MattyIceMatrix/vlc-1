# Get your logs graded — free

**Question:** if your AI agent, gateway or pipeline had an incident tomorrow, could a third
party prove from your log alone that it's *complete*? Could they show nothing was dropped,
nothing was rewritten, and every loss was declared?

Most production logs can't. In our twenty-year outage replay
([`examples/outage-simulations-2006-2026/`](examples/outage-simulations-2006-2026/)), all 25
plain logs graded **L0**, and a forged copy of each one graded exactly the same as the honest
original. A grade tells you where you stand before an incident, an auditor or a customer
asks.

## Three ways to get graded

### 1. Grade it yourself in two minutes (nothing leaves your machine)

```
git clone https://github.com/MattyIceMatrix/vlc-1 && cd vlc-1
pip install vlc-check
vlc-check --log your-export.jsonl --adapter adapters/generic-appjsonl.json
```

The checker is open source (CC0) and uses only the Python standard library. Nothing is uploaded
anywhere. Adapters are data files in [`adapters/`](adapters/), which is why the clone is needed.
If none of them fits your format, use option 2.

### 2. We grade it for you, free, no NDA

Open a **[grade request](https://github.com/MattyIceMatrix/vlc-1/issues/new?template=grade-request.yml)**
and tell us your log's **field names only**: timestamp, sequence, any hash or integrity
field, any dropped/lost counter. Field names are usually all we need to write the adapter and
tell you what level your format can reach.

Want a grade on real data? Email a **scrubbed or synthetic** export to
**hello@moore-labs.com**. Never paste log contents into a public issue.

**What you get back:**
- Your **structural and attested level** (L0–L5), from the same public checker anyone can rerun.
- **Every requirement** that passed or failed, with the checker's reason.
- **The gap list:** exactly what your producer would need to reach the next level, and L4.
- The **adapter** we wrote for your format, so you can regrade on your own from then on.

### 3. A signed report in the public registry

Want proof you can show a customer or auditor? A
[verified report](VERIFIED-REPORTS.md) is Ed25519-signed by the registry key and
re-verifiable offline by anyone. Ask in your grade request or by email.

## If the grade shows a gap

The gap list is yours to close however you like. The spec is public and free, and every
requirement says what it needs. If you'd rather have help reaching L3 or L4, that's a scoped,
paid pilot ([`ACCESS.md`](ACCESS.md), Level 3). For reference, the registry's first L4 is
report 002.

---

*Grading runs the same reference checker that's in this repository. We report what it says
and nothing more: no grade is rounded up, and a self-reported log tops out at L4 because the
spec says so. Your field names, data and results stay private unless you ask for a public
registry entry.*

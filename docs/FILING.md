# How to actually file this

**Status as at 2026-09-12.** Everything below was checked against primary
sources today; the uncertain parts are flagged as uncertain rather than smoothed
over. **Nothing here has been filed.** These are the steps a person has to take,
with the friction written down honestly.

---

## 0. Read the drafts first. This is not optional.

`COMMENT-prEN-18229.md` §7 says it and it is repeated here because it is the one
step that can turn an asset into an embarrassment:

> Every "no requirement addresses X" statement in the comment is based on
> **published drafts and specialist commentary, not committee documents.** Before
> filing, obtain prEN 18229-1, prEN 18229-3 and ISO/IEC FDIS 24970 in full
> through a national standards body and re-check each statement against the
> actual text. Withdraw any that is wrong.

A comment that mischaracterises a draft is worse than no comment, and a committee
remembers which one you filed. Budget a day and roughly £200–400 for draft copies.

---

## 1. CEN-CENELEC — prEN 18229-1 and -3

### The structural fact

**There is no public CEN comment portal.** Votes and comments are submitted by
**CEN members — the national standards bodies** — on the e-balloting platform,
using the CEN Commenting Form. Only ANEC, ECOS and ETUC have a direct non-NSB
channel. A US-based commenter therefore routes through a national mirror
committee, and only NSB-submitted comments enter the official disposition.

### The two realistic routes

| | route | what it costs | notes |
|---|---|---|---|
| **A** | **DIN Norm-Entwurfs-Portal** — https://www.din.de/de/mitwirken/entwuerfe | free | DIN states plainly: *"Jeder hat das Recht, zum Inhalt eines Norm-Entwurfs … Stellungnahmen abzugeben"* — **everyone** has the right to comment. No residency requirement is stated. German-language interface; comments go to the responsible working group. **This is the lowest-friction route and should be tried first.** |
| **B** | **BSI Standards Development Portal** — https://standardsdevelopment.bsigroup.com/ | free to register | Register, find the standard's profile page, comment while it is at "Public comment". BSI's About/User Guide pages state no geographic restriction. *Uncertain whether non-UK residents are accepted in practice — confirm before relying on it.* |

NEN (https://www.normontwerpen.nen.nl/Drafts) is a third option; Dutch-only, login
required, and 18229 was not listed at time of check.

**ANSI is not a route.** ANSI has cooperation agreements with CEN-CENELEC but no
mechanism for individual US comments on prENs.

### Dates

- **prEN 18229-1** — enquiry **closed** (BSI ran 28 May – 21 July 2026; DIN to
  5 August). **Comment disposition is in progress.** A comment cannot be filed
  through the enquiry, but a technical contribution reaching the working group
  during disposition still has weight, especially one with a working
  implementation behind it. Route: contact the JTC 21 mirror committee secretary
  at DIN or BSI directly.
- **prEN 18229-3** — reached enquiry around **30 July 2026**. CEN enquiry runs
  **12 weeks** by default with up to 4 weeks' extension, which implies a close
  around **late October 2026** — *inferred from the standard duration, not
  confirmed.* **The exact closing date was not findable in open sources and must
  be confirmed at DIN or BSI before planning around it.**

### Do this, in order

1. Search for "18229" on the DIN Norm-Entwurfs-Portal. If -3 is listed at
   enquiry, **file there first** — it is free, open to anyone, and immediate.
2. In parallel, register on the BSI portal and search 18229.
3. Email the JTC 21 mirror committee secretary at whichever body lists it, with
   the -1 disposition comment attached and one paragraph saying what the
   reference implementation is.
4. Keep the submission receipt. A filed comment is a citable fact; an intention
   to file is not.

---

## 2. ISO/IEC JTC 1/SC 42 — via INCITS/AI

ISO/IEC 24970 lives in SC 42. The US Technical Advisory Group to SC 42 **is**
the INCITS Artificial Intelligence technical committee, so INCITS/AI is the route
from the United States.

**24970 is at FDIS** — the last stage before publication — so the base document
is closed. The realistic target is an **amendment or a new work item** on
verifiable log completeness, which is exactly the kind of thing a committee
member proposes and a non-member cannot.

### What it costs

INCITS membership is **organisational**, on a 1 December – 30 November year:

| category | 2026 fee |
|---|---|
| TC/SG participation | **$2,703** |
| **small business (<$3M revenue)** | **$1,530** |
| academic | $510 |

There is no separate task-group fee — you join at TC/SG level. There is a
**standing open call for experts** with no deadline; participation ranges from
monitoring to full technical contribution, and meetings are monthly and virtual.

**Uncertain:** whether an unaffiliated *individual* can join at all, since
membership is organisation-based. Resolving the legal entity — already the
cheapest open item on the backlog and a gate on SOC 2 as well — also resolves
this.

### Contacts

- Lynn Barra, INCITS — **lbarra@itic.org** (the contact named on the open call)
- Deborah Spittle, secretariat — dspittle@itic.org
- Committee page: https://www.incits.org/committees/ai
- Membership: https://www.incits.org/participation/membership-info

### Draft enquiry — send this

> **Subject:** INCITS/AI participation — contribution on verifiable log completeness (SC 42 / ISO/IEC 24970)
>
> Dear Ms Barra,
>
> I am writing in response to the open call for experts for INCITS/Artificial
> Intelligence, with a specific technical contribution in mind for the SC 42
> logging work.
>
> I have published a vendor-neutral specification and conformance scheme for
> demonstrating the **completeness** of AI system logs — the property that
> distinguishes "nothing happened" from "nothing was recorded". It defines five
> cumulative conformance levels, ships an adapter-driven conformance checker that
> can be run against any JSON-lines audit log, and includes a machine-checked
> Coq development proving the levels are strictly ordered and that each admits an
> attack the next refuses. It is released CC0 precisely so that a committee can
> lift clauses from it without a licensing conversation.
>
> My reading of ISO/IEC CD 24970 is that it specifies event content and the
> documentation burden but contains no requirement addressing dropped events,
> guaranteed capture, gap accounting or completeness verification. If that
> reading is wrong I would very much like to be corrected, and if it is right
> I believe it is worth an amendment or a new work item.
>
> Two questions before I proceed:
>
> 1. Is participation open to a small business, and is the $1,530 small-business
>    category the applicable one for a company below $3M revenue?
> 2. Given 24970 is at FDIS, is the appropriate vehicle an amendment proposal, a
>    new work item, or a contribution through the US TAG's existing liaison?
>
> The specification, checker, worked examples and proof are public and I am happy
> to send the link or walk the committee through the conformance suite.
>
> With thanks,
> Matthew Moore
> moorematthew131@gmail.com

---

## 3. Publish somewhere citable — do this first, it is free and takes an hour

A standards comment that references a repository nobody can reach is an
assertion. Before either of the above:

1. **Push this repository publicly.** `docs/PUBLISH.md` has the commands.
2. **Mint a DOI.** Turn on the GitHub–Zenodo integration and cut a release;
   Zenodo assigns a DOI and archives the tarball. `CITATION.cff` is already in
   the repository so the citation metadata is picked up automatically. A DOI is
   what turns "a GitHub repo" into something a committee document can cite.
3. Optionally post the specification to arXiv (cs.CR or cs.SE) or to the CEN/ISO
   liaison mailing lists once a DOI exists.

The order matters: **DOI, then file.** It costs nothing and it changes how the
comment reads.

---

## 4. The one-line status board

| item | state | next action | blocker |
|---|---|---|---|
| Publish repository + DOI | ready to push | `docs/PUBLISH.md` | none |
| Read 18229-1 / -3 / 24970 in full | **not done** | order through DIN or BSI | ~£200–400 |
| prEN 18229-3 comment | drafted | confirm closing date, file via DIN | draft must be read first |
| prEN 18229-1 disposition contribution | drafted | email JTC 21 mirror secretary | same |
| INCITS/AI membership | drafted enquiry above | send it | legal entity |
| Legal entity | open | — | gates INCITS, SOC 2, and contracts |

# Agreement Record v0 (`a2a-agreement-v1`), DRAFT

**Status:** draft, 2026-09-10. NOT served at a URI, NOT anchored, NOT implemented. This document exists
so that the design is dated and quotable before anyone needs it. It will move to a URI and be anchored
only when a real two party agreement exists to record.
**Author:** The HORIZ音s Co., Ltd. / HORIZON SHIELD.
**License:** Apache-2.0, the same as `conduct-v1`.
**Language:** RFC 2119 keywords. Field names are exact.

## 1. What this is for

`conduct-v1` records a **one sided** observation: a measurer measured an endpoint, or a client walked an
agent and filed what it saw. Nothing in it records the other half of commerce: that **two** agents agreed
on terms, and that **both** said so.

This document defines that record. It is not an exchange. Nothing here matches orders, holds funds,
takes custody, or declares a contract formed. It records one fact: at time T, party A and party B both
signed the same bytes describing terms, and each of them was, at that moment, pointing at a conduct
record written by somebody other than themselves.

## 2. Why a third party, and why this one

Two agents can already sign a message to each other. What they cannot do is produce, on their own, an
artifact that a fourth party will believe later: the parties hold their own copies, and whoever holds
the record chooses what to keep. That is the same defect this project removed from measurement three
times over (the subject choosing the coordinate of content, of population, and of time).

A record layer is worth something only if it satisfies all of:

1. **Both signatures or nothing.** A one sided receipt is not an agreement; the intake MUST refuse it.
2. **An external clock nobody owns.** The record is bundled and anchored to Bitcoin, so its upper time
   bound does not depend on the operator of this layer.
3. **The counterparty's conduct at that instant, by sha.** Not a link that can change: the hash of the
   conduct record each side presented when they agreed.
4. **No custody, no matching, no fee tied to the deal.** The recorder MUST NOT hold funds, MUST NOT
   decide whether a deal happens, and MUST NOT charge a fee that varies with the amount or the outcome.
   The record MUST disclose who paid for it (`record_paid_by`).

## 3. The record

Schema `a2a-agreement-v1`. Canonical bytes as in `conduct-v1` section 4 (UTF-8, keys sorted at every
level, separators `,` and `:` with no spaces, non-ASCII unescaped).

- `schema`: `"a2a-agreement-v1"`.
- `agreed_at`: ISO-8601 UTC, as stated by the parties. It is a claim, not a measurement; the anchor is
  what bounds it from above.
- `parties`: exactly two objects, each `{ "domain", "key_url", "agent_card", "conduct_record_sha256",
  "conduct_record_url", "role" }`. `role` is `"payer"` or `"payee"` or `"peer"`. `key_url` MUST be an
  https URL under that party's own domain, as in `conduct-v1.1` section 11.4.
- `terms`: `{ "what", "who_pays_whom", "amount" or "fee_basis", "currency", "disclosure_url" }`. The
  content of `terms` is NOT judged by anyone in this layer. Only its presence and shape are checked.
- `upstream`: OPTIONAL `{ "protocol", "reference" }`, naming a payment the parties made elsewhere
  (for example an x402 transaction hash, or an AP2 mandate id). Recorded as declared, never verified here.
- `record_paid_by`: `"party_a"`, `"party_b"`, `"both"`, `"neither"`, or `"third_party"`. REQUIRED.
- `signatures`: exactly two, each `{ "domain", "alg", "signature", "key_url" }`, over the canonical bytes
  of the record with `signatures` removed. The intake MUST verify that both cover the same bytes.
- `establishes` / `does_not_establish`: as in `conduct-v1.1` section 11.1, REQUIRED, non empty.

## 4. What the intake MUST refuse

`one_sided` (fewer than two signatures), `signatures_disagree` (the two signatures do not cover the same
bytes), `self_agreement` (both parties resolve to the same domain), `bad_key_url` (not https, or not under
the signing party's domain), `key_url_unreachable` (503, so the record is retried rather than judged),
`missing_conduct_sha` (a party presented no conduct record), `disclaimer_missing`, and
`fee_tied_to_outcome` (the record declares a recorder fee that varies with `terms.amount`).

Refusal is mechanical. No editorial step exists, and none may be added.

## 5. What a filed agreement does not establish

That either party performed. That the terms are lawful, fair, or complete. That money moved. That either
party is solvent, competent, or honest. That the conduct records presented were accurate; only that they
were the records presented, by sha, at that moment. That this record is a contract: it is evidence that
two keys signed the same bytes at a time bounded from above by a Bitcoin block, and nothing more.

## 6. Prior art, named before anyone has to

- **AP2** (Agent Payments Protocol, Google and 60+ partners, 2025): cryptographically signed mandates
  (Intent, Cart, Payment) authorise a payment. Difference: AP2 authorises; this records, and it records
  the counterparty's measured conduct beside the terms. The two compose: an AP2 mandate id belongs in
  `upstream`.
- **x402** (Coinbase, with the x402 Foundation co-governed with Cloudflare) and the A2A extension
  `google-agentic-commerce/a2a-x402` (Apache-2.0, experimental): settlement over HTTP 402, three steps,
  `payment-required` / `payment-submitted` / `payment-completed`. Difference: settlement leaves a chain
  transaction, not a record of the agreed terms that a third party can verify. Its transaction hash
  belongs in `upstream`.
- **ACP** (OpenAI and Stripe) and **MPP** (Stripe and Tempo): checkout and multi rail sessions, token
  based authorisation rather than bilateral signing. Different layer.
- **Cedulon** (IETF individual draft, `draft-dogru-cedulon-08`): an audit layer above x402 and AP2. Spend
  Receipts with payer, payee, amount, policy hash, rail reference, `prevReceiptHash`, `outcome`; custody
  explicitly forbidden. Closest prior art. Differences: in Cedulon the parties hold their own records and
  the payee countersignature is OPTIONAL, so a one sided receipt is valid and the party being audited
  keeps the evidence. Here both signatures are mandatory, the bytes go to an intake that refuses
  editorially nothing, and the batch is anchored outside the operator.
- **1F916 Agent Record** (IETF individual draft, `draft-maintainer-1f916-agent-record-01`, 2026-08-12):
  per agent append only logs bound to Ed25519 keys, witness countersigned checkpoints, an instance of the
  SCITT architecture, explicitly with no blockchain. Differences: it tracks **one agent's own history**,
  and states that inter agent agreements are out of scope; and it takes trust from witness diversity
  where this design also takes an upper time bound from a chain nobody here operates. These are different
  trust assumptions, not a ranking, and the two are complementary: witnesses catch equivocation, an anchor
  bounds time.
- **NENRIN** and `conduct-v1` (this operator, 2026-08 and 2026-09): the measurement and witness layers this
  record depends on. An agreement record without a conduct record on each side is only half of the point.

No new primitive is claimed. What is claimed is the combination: two mandatory signatures, an intake that
judges nothing, an external anchor, and the counterparty's measured conduct pinned by sha at the moment of
agreement.

## 7. What is deliberately not here yet

A URI. An anchor. An implementation. A fee schedule. Those come when a real pair of parties has a real
agreement to record. A record layer built before it has two parties is an empty exchange, and an empty
exchange is worse than none.

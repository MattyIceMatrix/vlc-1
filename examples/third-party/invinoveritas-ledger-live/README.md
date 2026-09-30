# invinoveritas verdict ledger, from public data (positive control)

Fetched 2026-09-30 on a GitHub-hosted runner by `.github/workflows/ledger-capture.yml`
and `capture/scripts/ledger_capture.py` on branch `capture/invinoveritas-ledger`, three
runs (`run-20260930T135456Z`, `run-20260930T140743Z`, `run-20260930T142032Z`), which
produced byte-identical chain files. The operator offered the ledger for scoring on
vlc-1 PR #3 and supplied no number. Nothing here is confirmed by the operator.

## What was done

The runner sent only GET requests to `https://api.babyblueviper.com` and Nostr `REQ`
subscriptions to six public relays; it published nothing.

1. `GET /ledger`: 269 entries, 230 of them with a `chain` block (40 to 269);
   `verifier_pubkey` equals the key pinned in invinoveritas's own
   `invinoveritas_verify.py`.
2. `GET /ledger/{n}` for each chained entry: `content_hash` recomputed from the full
   `record` by the canonicalization `chain_spec` pins
   (`json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`),
   then `head_hash = sha256(content_hash + "|" + prev_head_hash)` from the genesis
   `sha256("invinoveritas-ledger-genesis:before-entry-40")`, each link checked against
   the recomputed predecessor rather than the served one. All 230 matched
   (`recompute.jsonl` in the run folder). The index and entry pages served the same
   chain block for every entry except that entry 40's page adds an explanatory
   `prev_head_hash_note` field.
3. Nostr: every event by the published key. Six carry
   `invinoveritas.ledger_chain_head.v1`, for entries 264 to 269, on `wss://nos.lol` and
   `wss://relay.primal.net`; `relay.damus.io`, `nostr.wine` and `relay.snort.social`
   returned none, and `relay.nostr.band` timed out. All six have a NIP-01 id that
   recomputes and a valid BIP-340 signature by the published key. The newest states
   entry 269 and head `04467b72…108d`, the head the recomputation reaches.

The full records were hashed on the runner and are **not** copied into this repository;
they are invinoveritas's data and anyone can fetch them. `invinoveritas-ledger-live-full.jsonl`
holds each entry's served chain block (`entry`, `content_hash`, `prev_head_hash`,
`head_hash`) and the newest head event verbatim, with only a `class` field added.
`invinoveritas-ledger-live-truncated.jsonl` is the same file with entry 269 removed.

invinoveritas's own `recompute_ledger.py` was also run as a cross-check. It did not
finish inside the 10-minute limit (it fetches each verdict event from the relays one by
one), so there is no cross-check result; that says nothing about the ledger.

## `verify_ledger.py`

Standard library only, written from the published `chain_spec`, not from invinoveritas
code: BIP-340 verification (self-tested on the BIP's own vectors before use), NIP-01 event
ids, chain links, entry order, and the head event against the recomputed head.

| file or mutation | chain alone | with the signed head |
|---|---|---|
| `-full.jsonl` | passes | passes |
| one middle entry removed | caught | caught |
| one `content_hash` edited | caught | caught |
| two entries swapped | caught | caught |
| newest entry dropped (`-truncated.jsonl`) | **passes** | caught |
| whole chain rewritten consistently from genesis | **passes** | caught |

The last two rows are why a head held outside the log matters, and why `--expect-head`
exists. Here the outside holders are Nostr relays run by third parties; each head event
has its own `d` tag, so a later head does not replace an earlier one, and two heads for
one entry number is a visible fork. The operator still signs every head.

## Score, and why it is not higher

Both files score **L0** in `conformance.py`, on the same 13 failed requirements
(VLC-L1-1/2/3, L2-1, L2-5, L3-1a, L3-6, L4-1, L5-1, L5-3/4/5/6), and the truncated file
scores exactly as the full one.

Integrity is a limit of the checker: none of its mechanisms computes
`sha256(content_hash + "|" + prev_head)` over a content hash of a separate record, so the
adapter declares `none` and states the real mechanism in `integrity.actual_mechanism`.
Reshaping the rows to fit one of the checker's mechanisms would manufacture a pass.

The rest are real, and the ledger says so itself. No record states how many verdicts
were issued against how many were written (loss); the index's `completeness` block gives
aggregate tape counts and calls them "still short of a hard completeness proof".
`population_spec` declares which entry types are mandatory at issuance and what stays
open, but that is a declared scope, not a per-record enumeration (coverage). No entry
binds the rules that admitted it (policy). The operator writes the entries and signs the
heads (independence).

Entries 264 to 269 were written outside the chain and chained late on 2026-09-30; each
carries `chain_note` and `chain_backfilled_at` saying so. The operator found and disclosed
this on PR #3 while preparing the ledger for scoring.

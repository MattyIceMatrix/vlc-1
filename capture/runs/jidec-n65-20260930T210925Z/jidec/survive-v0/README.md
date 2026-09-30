# nenrin-survive-v0: can the history be rebuilt without us?

The claim: if The HORIZONs Co., Ltd. and every host it runs disappeared tomorrow, a stranger could rebuild yesterday's JIDEC ledger from copies held elsewhere and check every entry against Bitcoin alone.

A claim like that is worth nothing until someone tries it on a schedule and publishes what happened. This directory does both. Every day a workflow in this repository runs the drill below from a GitHub runner with the operator's names sinkholed, and commits the report beside this file, whatever it says.

## The drill

    pip install -r requirements.txt
    python3 survive.py drill --source swh --fenced --out report.json

1. **A copy, not from us.** `--source swh` asks Software Heritage for the archived copy of `kept/` (a mirror-v0 copy of the ledger committed here daily) and has it cooked into a tarball. `--source github` takes a GitHub tarball instead; that account is ours, so the report marks it `operator_controlled: true` and it proves the copy's form, not its survival. `--source dir:/path` takes your own copy, for example one made with [mirror-v0](../mirror-v0/BECOME_A_MIRROR.md).
2. **No operator host.** Every URL is checked before any connection: operator names are refused by suffix (`horizonshield.dev`, `the-horizons-innovation.com`, `oga-surf-project.workers.dev`), and anything that is not Software Heritage, the GitHub tarball host or one of two block explorers is refused too. With `--fenced`, a canary connection to `ledger.horizonshield.dev` must fail before the drill starts; in CI those names resolve to 0.0.0.0.
3. **Digests.** sha256 of every `ledger/<n>.raw` must equal that entry's `claim_sha256`.
4. **Chain.** jidec-chain-v1 is recomputed over entries 1..N from the copy alone, with the recipe in [`chain_v1.mjs`](../../src/chain_v1.mjs). Every head that a checkpoint or batch carries inside its own anchored bytes (`ledger_head`: n, entry_sha256, marker_sha256) must match the recomputation. A missing entry breaks the walk and is reported where it breaks.
5. **Anchors.** Every `ledger/<n>.ots` is walked with the OpenTimestamps library. A Bitcoin attestation counts only if the merkle root it commits to equals the block header's merkle root as served by both blockstream.info and mempool.space. Proofs that are still pending are listed, never counted.

The report is `nenrin-survive-drill-v0` JSON with `outcome` one of `rebuilt`, `findings`, `custodian_unavailable`, `empty_copy` or `fence_failed`, the custodian and its snapshot identifiers, the counts, every failure by entry number, `establishes`, `does_not_establish` and its own `report_sha256`.

## What it does not establish

That any claim in the ledger is true. That the copy is complete past its highest entry: the newest entries reach the custodian a day or more later. That two explorers agreeing is Bitcoin consensus; check the headers against your own node for that. Anything about pending proofs.

## Where the reports are

`drills/latest-swh.json`, `drills/latest-github.json` and one line per run in `drills/history.jsonl`. A red run is kept, not rerun until it turns green.

## Tests

    python3 survive_test.py

Offline, no network. Synthetic ledgers that break one thing each (a changed byte, a removed entry, a checkpoint that disagrees, explorers that disagree, a proof for other bytes, operator hosts), one real proof (ledger entry 66, confirmed in blocks 969240 and 969244), and a check that the Python chain recipe gives the same bytes as the ledger's JavaScript.

#!/usr/bin/env python3
"""ledger_capture.py -- live capture of the invinoveritas verdict-ledger hash chain.

BLAST RADIUS: runs only on a GitHub-hosted runner (workflow ledger-capture.yml).
Reads public HTTPS endpoints and public Nostr relays; writes only under $OUT/ledger.
Sends nothing but GET requests and Nostr REQ subscriptions (no EVENT is ever published).

What it writes (committed to capture/runs/ on branch capture/invinoveritas-ledger):
  index-summary.json        top-level keys, chain_spec, verifier_pubkey, sha256 of the
                            /ledger response bytes (the response itself is not kept)
  recompute.jsonl           per chained entry: content_hash recomputed from the full
                            record at GET /ledger/{n}, compared with the served chain
                            block; record top-level keys; the record's byte length
  chain.jsonl               class "ledger-entry" rows: entry + the served chain block
  nostr-summary.json        per relay: events returned, kinds, head events found
  nostr-head-events.jsonl   every raw signed event whose content or tags name
                            ledger_chain_head (public broadcasts, kept verbatim)
  ledger-live-full.jsonl    chain.jsonl + the newest valid head event (class chain-head)
Full records are fetched and hashed on the runner but NOT committed: they are
invinoveritas's data, served publicly, and anyone can re-fetch them.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "examples", "third-party", "invinoveritas-ledger-live"))
import verify_ledger as V  # noqa: E402

API = "https://api.babyblueviper.com"
RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net",
          "wss://relay.nostr.band", "wss://nostr.wine", "wss://relay.snort.social"]
OUT = os.path.join(os.environ["OUT"], "ledger")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "vlc-1-conformance-capture (github.com/MattyIceMatrix/vlc-1)"}


def log(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    with open(os.path.join(OUT, "steps.txt"), "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def get(path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(API + path, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            log(f"GET {path} try {i + 1}: {e}")
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"GET {path} failed")


def dump(name, obj):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def dumpl(name, rows):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


async def relay_query(url, filters, timeout=20):
    import websockets
    got = []
    try:
        async with websockets.connect(url, open_timeout=10, max_size=2 ** 24) as ws:
            for i, flt in enumerate(filters):
                await ws.send(json.dumps(["REQ", f"q{i}", flt]))
            open_subs = {f"q{i}" for i in range(len(filters))}
            end = time.time() + timeout
            while open_subs and time.time() < end:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.time())))
                except asyncio.TimeoutError:
                    break
                if msg[0] == "EVENT" and len(msg) >= 3:
                    got.append(msg[2])
                elif msg[0] in ("EOSE", "CLOSED"):
                    open_subs.discard(msg[1])
            for s in list(open_subs):
                await ws.send(json.dumps(["CLOSE", s]))
        return got, None
    except Exception as e:  # noqa: BLE001
        return got, f"{type(e).__name__}: {e}"


def main():
    V._selftest_bip340()
    raw = get("/ledger")
    idx = json.loads(raw)
    entries = idx.get("entries") or []
    pk = str(idx.get("verifier_pubkey") or "").lower()
    dump("index-summary.json", {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256_of_response": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "top_level_keys": list(idx.keys()), "schema_version": idx.get("schema_version"),
        "chain_spec": idx.get("chain_spec"), "completeness": idx.get("completeness"),
        "count": idx.get("count"), "population_spec": idx.get("population_spec"),
        "recompute_whole_ledger": idx.get("recompute_whole_ledger"), "verifier_pubkey": idx.get("verifier_pubkey"),
        "verifier_pubkey_equals_pinned": pk == V.PUBKEY, "entries": len(entries),
        "entries_with_chain": sum(1 for e in entries if e.get("chain")),
        "entry_numbers": [e.get("entry") for e in entries],
    })
    log(f"/ledger: {len(entries)} entries, verifier_pubkey pinned-match={pk == V.PUBKEY}")

    chained = sorted([e for e in entries if e.get("chain")], key=lambda e: e.get("entry", 0))
    rec_rows, chain_rows, prev = [], [], V.GENESIS
    for e in chained:
        n = e["entry"]
        claimed = e["chain"]
        row = {"entry": n}
        try:
            doc = json.loads(get(f"/ledger/{n}"))
            record = doc.get("record")
            ch = V.content_hash(record)
            served = doc.get("chain") or claimed
            row.update(record_present=record is not None,
                       record_keys=sorted(record.keys()) if isinstance(record, dict) else type(record).__name__,
                       record_canon_bytes=len(V.canon_record(record)),
                       doc_keys=sorted(doc.keys()),
                       content_hash_recomputed=ch,
                       content_hash_matches_index=ch == claimed.get("content_hash"),
                       content_hash_matches_entry_doc=ch == served.get("content_hash"),
                       index_and_doc_chain_agree=served == claimed,
                       chain_block_differences=None if served == claimed else {
                           k: {"index": claimed.get(k), "entry_doc": served.get(k)}
                           for k in sorted(set(claimed) | set(served)) if claimed.get(k) != served.get(k)},
                       chain_backfilled_at=doc.get("chain_backfilled_at"),
                       chain_note=doc.get("chain_note"),
                       prev_head_matches_recomputed_predecessor=claimed.get("prev_head_hash") == prev,
                       head_recomputes=V.link(ch, prev) == claimed.get("head_hash"),
                       )
            prev = V.link(ch, prev)
        except Exception as ex:  # noqa: BLE001
            row.update(error=str(ex))
            prev = claimed.get("head_hash", prev)
        rec_rows.append(row)
        cr = {"class": "ledger-entry", "entry": n}
        cr.update({k: claimed.get(k) for k in ("content_hash", "prev_head_hash", "head_hash")})
        chain_rows.append(cr)
        time.sleep(0.15)
    dumpl("recompute.jsonl", rec_rows)
    dumpl("chain.jsonl", chain_rows)
    bad = [r["entry"] for r in rec_rows if r.get("error") or not all(
        r.get(k) for k in ("content_hash_matches_index", "prev_head_matches_recomputed_predecessor", "head_recomputes"))]
    log(f"chained entries: {len(chain_rows)} ({chain_rows[0]['entry'] if chain_rows else '-'}"
        f"..{chain_rows[-1]['entry'] if chain_rows else '-'}); recompute failures: {bad}")

    # ---- Nostr: every event by the published key, then keep the chain-head broadcasts
    filters = [{"authors": [V.PUBKEY], "kinds": [30078], "limit": 2000},
               {"authors": [V.PUBKEY], "limit": 500}]
    summary, allev = {}, {}

    async def all_relays():
        return await asyncio.gather(*(relay_query(u, filters) for u in RELAYS))

    for url, (evs, err) in zip(RELAYS, asyncio.run(all_relays())):
        heads = [ev for ev in evs if "ledger_chain_head" in json.dumps([ev.get("content"), ev.get("tags")])]
        summary[url] = {"events": len(evs), "error": err,
                        "kinds": sorted({ev.get("kind") for ev in evs}),
                        "head_events": len(heads)}
        for ev in heads:
            allev.setdefault(ev["id"], dict(ev, _relays=[]))["_relays"].append(url)
    heads = sorted(allev.values(), key=lambda ev: ev.get("created_at", 0))
    checked = []
    for ev in heads:
        pure = {k: v for k, v in ev.items() if not k.startswith("_")}
        try:
            idok = V.nostr_event_id(pure) == pure["id"]
            sigok = V.schnorr_verify(bytes.fromhex(pure["id"]), bytes.fromhex(pure["pubkey"]),
                                     bytes.fromhex(pure["sig"]))
        except Exception:  # noqa: BLE001
            idok = sigok = False
        hn, hh = V.head_claim(pure)
        checked.append((pure, idok and sigok and pure.get("pubkey") == V.PUBKEY, hn, hh, ev["_relays"]))
    dumpl("nostr-head-events.jsonl", [dict(p, _relays=r, _valid=ok, _claim_entry=hn, _claim_head=hh)
                                      for p, ok, hn, hh, r in checked])
    summary["_distinct_head_events"] = len(heads)
    summary["_valid_head_events"] = sum(1 for c in checked if c[1])
    summary["_d_tags"] = sorted({t[1] for p, *_ in checked for t in p.get("tags", []) if t and t[0] == "d" and len(t) > 1})
    dump("nostr-summary.json", summary)
    log(f"nostr: {len(heads)} distinct head events, {summary['_valid_head_events']} valid")

    valid = [c for c in checked if c[1] and c[3]]
    full = list(chain_rows)
    if valid:
        # the head event for the newest entry the log reaches, else the newest valid event
        last_n = chain_rows[-1]["entry"] if chain_rows else None
        pick = [c for c in valid if c[2] == last_n] or valid
        full.append(dict(pick[-1][0], **{"class": "chain-head"}))
    dumpl("ledger-live-full.jsonl", full)
    ok, findings, facts = V.verify(full)
    dump("verify.json", {"ok": ok, "findings": findings, "facts": facts,
                         "mutations": V.run_mutations(full, V.PUBKEY)})
    log(f"verify: ok={ok} findings={findings[:5]}")


if __name__ == "__main__":
    main()

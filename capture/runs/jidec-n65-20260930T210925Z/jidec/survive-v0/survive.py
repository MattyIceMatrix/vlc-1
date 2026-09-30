#!/usr/bin/env python3
"""nenrin-survive-v0: rebuild yesterday's ledger history without the operator.

The claim this tests: if The HORIZONs Co., Ltd. and every host it runs disappeared tomorrow, a stranger could
still rebuild the JIDEC ledger from copies held elsewhere and check it against Bitcoin alone.

A claim like that is worth nothing until someone tries it on a schedule and publishes the result. This file is
that attempt. It never talks to an operator host: every URL is checked against a list of operator names and a
short allowlist of custodians and block explorers before any connection is made, and in CI the operator names
are also sinkholed in /etc/hosts and a canary connection must fail.

    python3 survive.py drill --source swh    --out report.json   # copy from Software Heritage (preferred)
    python3 survive.py drill --source github --out report.json   # copy from a GitHub tarball (operator controlled)
    python3 survive.py drill --source dir:/path/to/mirror --out report.json   # your own copy (mirror-v0 layout)

What is checked, all from the copy plus two public block explorers:
  1. digests: sha256 of every ledger/<n>.raw equals the claim_sha256 of ledger/<n>.json
  2. chain: jidec-chain-v1 is recomputed over entries 1..N from the copy alone, and every stamped head a
     checkpoint or batch carries (ledger_head: n, entry_sha256, marker_sha256) must match the recomputation
  3. anchors: every ledger/<n>.ots is walked with the OpenTimestamps library; each Bitcoin attestation's
     merkle root must equal the block header's, as served by two explorers that must agree with each other

Dependencies: Python 3.8+, opentimestamps (pinned in requirements.txt). Nothing else.
"""
import argparse, hashlib, io, json, os, socket, sys, tarfile, time, urllib.parse, urllib.request

SCHEMA = "nenrin-survive-drill-v0"
VERSION = "0.1.0"
REPO_ORIGIN = "https://github.com/ogasurfproject-jpg/horizon-shield"
KEPT_PATH = "workers/hs-ledger/nenrin/survive-v0/kept"
OPERATOR_SUFFIXES = ("horizonshield.dev", "the-horizons-innovation.com", "oga-surf-project.workers.dev")
ALLOWED_HOSTS = ("archive.softwareheritage.org", "codeload.github.com", "blockstream.info", "mempool.space")
EXPLORERS = ("https://blockstream.info/api", "https://mempool.space/api")
CANARY_HOST = "ledger.horizonshield.dev"
CHAIN_ROOT = "0" * 64
UA = "nenrin-survive-v0/" + VERSION + " (+" + REPO_ORIGIN + ")"


class Refused(Exception):
    pass


def host_of(url):
    return (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")


def guard(url):
    """Refuse operator hosts by name, and anything that is not an allowed custodian or explorer."""
    h = host_of(url)
    if not url.startswith("https://"):
        raise Refused("not https: " + url)
    for s in OPERATOR_SUFFIXES:
        if h == s or h.endswith("." + s):
            raise Refused("operator host refused: " + h)
    if h not in ALLOWED_HOSTS:
        raise Refused("host not on the custodian/explorer allowlist: " + h)
    return url


def http_get(url, timeout=60, data=None, method=None):
    guard(url)
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def sha256hex(b):
    return hashlib.sha256(b).hexdigest()


# ---- canonical form and chain, identical to workers/hs-ledger/src/chain_v1.mjs --------------------------------
def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def chain_body(entry, prev):
    b = {"n": entry["n"], "claim_sha256": entry["claim_sha256"], "prev_entry_sha256": prev}
    if isinstance(entry.get("schema"), str):
        b["schema"] = entry["schema"]
    if isinstance(entry.get("created_at"), str):
        b["created_at"] = entry["created_at"]
    return b


def entry_sha(entry, prev):
    return sha256hex(canon(chain_body(entry, prev)).encode("ascii"))


def marker_sha(n, head):
    return sha256hex(canon({"n": n, "schema": "jidec-head-v1", "prev_entry_sha256": head, "head": head}).encode("ascii"))


# ---- obtaining a copy without the operator --------------------------------------------------------------------
def copy_from_dir(path):
    return os.path.abspath(path), {"custodian": "local", "path": os.path.abspath(path), "operator_controlled": None}


def _extract_subdir(tgz_bytes, want_suffix, dest):
    os.makedirs(dest, exist_ok=True)
    root = None
    with tarfile.open(fileobj=io.BytesIO(tgz_bytes), mode="r:*") as tf:
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            i = name.find(want_suffix)
            if i < 0 or not (m.isfile() or m.isdir()):
                continue
            rel = name[i + len(want_suffix):].lstrip("/")
            if ".." in rel.split("/"):
                continue
            out = os.path.join(dest, rel)
            if m.isdir():
                os.makedirs(out, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(tf.extractfile(m).read())
            root = dest
    if root is None:
        raise RuntimeError("the archive does not contain " + want_suffix)
    return dest


def copy_from_github(work):
    url = "https://codeload.github.com/ogasurfproject-jpg/horizon-shield/tar.gz/refs/heads/main"
    st, body = http_get(url, timeout=180)
    d = _extract_subdir(body, KEPT_PATH, os.path.join(work, "kept"))
    return d, {"custodian": "github", "url": url, "archive_sha256": sha256hex(body),
               "operator_controlled": True,
               "note": "the operator can delete this account; this source proves the copy's form, not its survival"}


def copy_from_swh(work, wait_s=900):
    api = "https://archive.softwareheritage.org/api/1"
    o = urllib.parse.quote(REPO_ORIGIN, safe="")
    st, b = http_get("%s/origin/%s/visit/latest/?require_snapshot=true" % (api, o))
    visit = json.loads(b)
    snap_id = visit["snapshot"]
    st, b = http_get("%s/snapshot/%s/" % (api, snap_id))
    snap = json.loads(b)
    br = snap["branches"].get("HEAD") or snap["branches"].get("refs/heads/main")
    if br and br.get("target_type") == "alias":
        br = snap["branches"][br["target"]]
    rev = br["target"]
    st, b = http_get("%s/revision/%s/" % (api, rev))
    root_dir = json.loads(b)["directory"]
    st, b = http_get("%s/directory/%s/%s/" % (api, root_dir, KEPT_PATH))
    ent = json.loads(b)
    if ent.get("type") != "dir":
        raise RuntimeError("%s is not a directory in the archived revision" % KEPT_PATH)
    dir_id = ent["target"]
    swhid = "swh:1:dir:" + dir_id
    cook = "%s/vault/flat/%s/" % (api, swhid)
    st, b = http_get(cook, data=b"", method="POST")
    t0 = time.time()
    while True:
        info = json.loads(b)
        if info.get("status") == "done":
            break
        if info.get("status") == "failed" or time.time() - t0 > wait_s:
            raise RuntimeError("Software Heritage vault did not finish: " + str(info.get("status")))
        time.sleep(15)
        st, b = http_get(cook)
    fu = info.get("fetch_url") or (cook + "raw/")
    if not fu.startswith("https://"):
        fu = "https://archive.softwareheritage.org" + fu
    st, tgz = http_get(fu, timeout=300)
    d = os.path.join(work, "kept")
    os.makedirs(d, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:*") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2 or not m.isfile() or ".." in parts[1].split("/"):
                continue
            out = os.path.join(d, parts[1])
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as f:
                f.write(tf.extractfile(m).read())
    return d, {"custodian": "software-heritage", "visit_date": visit.get("date"), "snapshot": snap_id,
               "revision": rev, "directory": swhid, "archive_sha256": sha256hex(tgz), "operator_controlled": False}


# ---- checks -----------------------------------------------------------------------------------------------------
def load_entries(d):
    ld = os.path.join(d, "ledger")
    out = {}
    for name in os.listdir(ld) if os.path.isdir(ld) else []:
        if name.endswith(".json") and name[:-5].isdigit():
            with open(os.path.join(ld, name), "rb") as f:
                out[int(name[:-5])] = json.loads(f.read())
    return out


def check_digests(d, entries):
    ok, bad = 0, []
    for n in sorted(entries):
        p = os.path.join(d, "ledger", "%d.raw" % n)
        if not os.path.exists(p):
            bad.append({"n": n, "why": "raw_missing"}); continue
        with open(p, "rb") as f:
            h = sha256hex(f.read())
        if h != entries[n].get("claim_sha256"):
            bad.append({"n": n, "why": "digest_mismatch", "got": h}); continue
        ok += 1
    return {"ok": ok, "failed": bad}


def find_heads(v, found):
    if isinstance(v, dict):
        lh = v.get("ledger_head")
        if isinstance(lh, dict) and isinstance(lh.get("n"), int) and isinstance(lh.get("entry_sha256"), str):
            found.append(lh)
        for x in v.values():
            find_heads(x, found)
    elif isinstance(v, list):
        for x in v:
            find_heads(x, found)


def check_chain(d, entries):
    heads, top = {}, max(entries) if entries else 0
    prev, broken = CHAIN_ROOT, None
    for n in range(1, top + 1):
        e = entries.get(n)
        if not e or e.get("n") != n or not isinstance(e.get("claim_sha256"), str):
            broken = n; break
        prev = entry_sha(e, prev)
        heads[n] = prev
    stamped, results = [], []
    for n in sorted(entries):
        p = os.path.join(d, "ledger", "%d.raw" % n)
        try:
            with open(p, "rb") as f:
                rec = json.loads(f.read())
        except Exception:
            continue
        found = []
        find_heads(rec, found)
        for lh in found:
            stamped.append((n, lh))
    for carrier, lh in stamped:
        k = lh["n"]
        r = {"carried_by": carrier, "head_n": k}
        if k not in heads:
            r["result"] = "beyond_rebuilt_range"
        elif heads[k] != lh["entry_sha256"]:
            r["result"] = "entry_sha256_mismatch"
        elif isinstance(lh.get("marker_sha256"), str) and lh["marker_sha256"] != marker_sha(k, heads[k]):
            r["result"] = "marker_mismatch"
        else:
            r["result"] = "match"
        results.append(r)
    return {"rebuilt_through": (broken - 1) if broken else top, "broken_at": broken,
            "head": heads.get((broken - 1) if broken else top),
            "stamped_heads": results,
            "stamped_heads_matched": sum(1 for r in results if r["result"] == "match")}


def header_merkle_root(height, get=http_get, cache=None):
    cache = {} if cache is None else cache
    if height in cache:
        return cache[height]
    roots = {}
    for base in EXPLORERS:
        try:
            st, h = get("%s/block-height/%d" % (base, height))
            st, b = get("%s/block/%s" % (base, h.decode().strip()))
            roots[host_of(base)] = json.loads(b)["merkle_root"]
        except Refused:
            raise
        except Exception as ex:
            roots[host_of(base)] = "error: " + type(ex).__name__
        time.sleep(0.2)
    cache[height] = roots
    return roots


def check_anchors(d, entries, get=http_get):
    from opentimestamps.core.timestamp import DetachedTimestampFile
    from opentimestamps.core.serialize import StreamDeserializationContext
    from opentimestamps.core.notary import BitcoinBlockHeaderAttestation
    confirmed, pending, failed = [], [], []
    cache = {}
    for n in sorted(entries):
        p = os.path.join(d, "ledger", "%d.ots" % n)
        if not os.path.exists(p):
            failed.append({"n": n, "why": "ots_missing"}); continue
        try:
            with open(p, "rb") as f:
                dtf = DetachedTimestampFile.deserialize(StreamDeserializationContext(f))
        except Exception as ex:
            failed.append({"n": n, "why": "ots_unparsable", "detail": type(ex).__name__}); continue
        if dtf.file_digest.hex() != entries[n].get("claim_sha256"):
            failed.append({"n": n, "why": "ots_digest_is_not_the_claim"}); continue
        btc = [(msg, a) for msg, a in dtf.timestamp.all_attestations() if isinstance(a, BitcoinBlockHeaderAttestation)]
        if not btc:
            pending.append(n); continue
        good = None
        for msg, a in sorted(btc, key=lambda x: x[1].height):
            want = msg[::-1].hex()
            roots = header_merkle_root(a.height, get, cache)
            vals = list(roots.values())
            if len(vals) == len(EXPLORERS) and all(v == want for v in vals):
                good = a.height; break
        if good is not None:
            confirmed.append({"n": n, "block": good})
        else:
            failed.append({"n": n, "why": "merkle_root_not_confirmed_by_both_explorers",
                           "heights": sorted(a.height for _, a in btc)})
    return {"confirmed": len(confirmed), "pending": pending, "failed": failed,
            "first_block": min((c["block"] for c in confirmed), default=None),
            "last_block": max((c["block"] for c in confirmed), default=None),
            "explorers": [host_of(e) for e in EXPLORERS]}


def canary():
    """In a fenced run the operator must be unreachable. Resolution to a sinkhole or a refused connect passes."""
    try:
        infos = socket.getaddrinfo(CANARY_HOST, 443, proto=socket.IPPROTO_TCP)
    except Exception:
        return {"host": CANARY_HOST, "reachable": False, "why": "does_not_resolve"}
    for fam, _, _, _, addr in infos:
        if addr[0] in ("0.0.0.0", "::", "127.0.0.1", "::1"):
            return {"host": CANARY_HOST, "reachable": False, "why": "sinkholed:" + addr[0]}
        try:
            s = socket.create_connection((addr[0], 443), timeout=5); s.close()
            return {"host": CANARY_HOST, "reachable": True, "why": "connected:" + addr[0]}
        except Exception:
            continue
    return {"host": CANARY_HOST, "reachable": False, "why": "connect_failed"}


def drill(source, work, fenced, get=http_get):
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fence = canary() if fenced else {"checked": False}
    if fenced and fence.get("reachable"):
        return {"schema": SCHEMA, "version": VERSION, "drill_at": started, "outcome": "fence_failed", "fence": fence}
    try:
        if source == "swh":
            d, prov = copy_from_swh(work)
        elif source == "github":
            d, prov = copy_from_github(work)
        elif source.startswith("dir:"):
            d, prov = copy_from_dir(source[4:])
        else:
            raise SystemExit("unknown --source " + source)
    except Refused:
        raise
    except SystemExit:
        raise
    except Exception as ex:
        # The custodian could not hand over a copy. That is a finding about availability, not about the ledger,
        # and it is reported as such rather than as a crash or as a pass.
        rep = {"schema": SCHEMA, "version": VERSION, "drill_at": started, "outcome": "custodian_unavailable",
               "source": {"requested": source}, "fence": fence, "why": "%s: %s" % (type(ex).__name__, str(ex)[:300])}
        rep["report_sha256"] = sha256hex(canon(rep).encode("ascii"))
        return rep
    entries = load_entries(d)
    dig = check_digests(d, entries)
    ch = check_chain(d, entries)
    an = check_anchors(d, entries, get)
    clean = (not dig["failed"] and ch["broken_at"] is None and not an["failed"]
             and all(r["result"] in ("match", "beyond_rebuilt_range") for r in ch["stamped_heads"]))
    rep = {
        "schema": SCHEMA, "version": VERSION, "drill_at": started,
        "outcome": "rebuilt" if clean and entries else ("empty_copy" if not entries else "findings"),
        "source": prov, "fence": fence,
        "entries": len(entries), "range": [min(entries), max(entries)] if entries else None,
        "digests": dig, "chain": ch, "anchors": an,
        "establishes": [
            "these ledger bytes were rebuilt from the named custodian without connecting to any operator host",
            "every digest, the jidec-chain-v1 head, the stamped heads and the Bitcoin anchors were recomputed from the copy and two public explorers",
        ],
        "does_not_establish": [
            "that any claim in the ledger is true",
            "that the copy is complete past its highest entry; the newest entries may not have reached the custodian yet",
            "that two explorers agreeing is Bitcoin consensus; check headers against your own node for that",
            "anything about entries whose proofs are still pending; they are listed, not counted",
        ],
    }
    rep["report_sha256"] = sha256hex(canon(rep).encode("ascii"))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(prog="survive.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("drill")
    p.add_argument("--source", default="swh", help="swh | github | dir:/path")
    p.add_argument("--out", default="-")
    p.add_argument("--work", default=".survive-work")
    p.add_argument("--fenced", action="store_true", help="require the operator canary to be unreachable")
    a = ap.parse_args(argv)
    rep = drill(a.source, a.work, a.fenced)
    txt = json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True)
    if a.out == "-":
        print(txt)
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt + "\n")
    print("outcome=%s entries=%s confirmed=%s pending=%s" % (rep.get("outcome"), rep.get("entries"),
          (rep.get("anchors") or {}).get("confirmed"), len((rep.get("anchors") or {}).get("pending") or [])), file=sys.stderr)
    return 0 if rep.get("outcome") == "rebuilt" else 1


if __name__ == "__main__":
    sys.exit(main())

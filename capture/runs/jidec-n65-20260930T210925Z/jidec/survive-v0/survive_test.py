#!/usr/bin/env python3
"""Offline tests for survive.py. No network: explorers are mocked, the copy is built on disk.

One case uses a real proof: fixtures/ledger66.ots is the OpenTimestamps proof of JIDEC ledger entry 66
(claim 0c3bebf7...), and the two merkle roots below are the ones blockstream.info and mempool.space both
served for blocks 969240 and 969244 on 2026-09-30. The rest are synthetic ledgers that break one thing each.
"""
import io, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import survive as S
from opentimestamps.core.timestamp import Timestamp, DetachedTimestampFile
from opentimestamps.core.op import OpAppend, OpSHA256
from opentimestamps.core.notary import BitcoinBlockHeaderAttestation, PendingAttestation
from opentimestamps.core.serialize import BytesSerializationContext

fails = ran = 0
def ok(name, cond, detail=""):
    global fails, ran
    ran += 1
    if not cond:
        fails += 1
        print("  NG  " + name + ("  <- " + str(detail)[:300] if detail != "" else ""))

REAL_CLAIM_66 = "0c3bebf744e5896b6457902dfd355e47ead6fa327f96b226e964acdbe300223e"
REAL_ROOTS = {969240: "33456e83db466c1f7b15f7b54314142dc3b431cf9e0310786b5def5267408b20",
              969244: "54052b87c416d8067de2f09eb509cf47404b07726675014e5714ed4f537a7ceb"}


def make_ots(digest_hex, height=None, pending=False):
    t = Timestamp(bytes.fromhex(digest_hex))
    t2 = t.ops.add(OpAppend(b"\x07\x07")).ops.add(OpSHA256())
    if pending:
        t2.attestations.add(PendingAttestation("https://alice.btc.calendar.opentimestamps.org"))
    else:
        t2.attestations.add(BitcoinBlockHeaderAttestation(height))
    ctx = BytesSerializationContext()
    DetachedTimestampFile(OpSHA256(), t).serialize(ctx)
    return ctx.getbytes(), t2.msg[::-1].hex()


class Explorer:
    def __init__(self, roots, disagree=None):
        self.roots, self.disagree, self.calls = dict(roots), dict(disagree or {}), []
    def __call__(self, url, timeout=60, data=None, method=None):
        S.guard(url)
        self.calls.append(url)
        host = S.host_of(url)
        if "/block-height/" in url:
            h = int(url.rsplit("/", 1)[1])
            return 200, ("hash%d" % h).encode()
        h = int(url.rsplit("hash", 1)[1])
        root = self.disagree.get((host, h), self.roots.get(h, "00" * 32))
        return 200, json.dumps({"merkle_root": root}).encode()


def build_ledger(d, n_entries=5, pending_n=(3,), mutate=None):
    """Entries 1..n-1 are plain claims; the last entry is a checkpoint carrying ledger_head of n-1."""
    os.makedirs(os.path.join(d, "ledger"), exist_ok=True)
    entries, roots, prev = {}, {}, S.CHAIN_ROOT
    heads = {}
    for n in range(1, n_entries + 1):
        if n < n_entries:
            raw = ("claim %d, bytes a stranger can hash é" % n).encode("utf-8")
        else:
            k = n_entries - 1
            lh = {"chain": "jidec-chain-v1", "n": k, "entry_sha256": heads[k], "marker_sha256": S.marker_sha(k, heads[k])}
            if mutate == "bad_checkpoint":
                lh["entry_sha256"] = "f" * 64
            raw = S.canon({"schema": "nenrin-head-checkpoint-v1", "ledger_head": lh}).encode("ascii")
        e = {"n": n, "schema": "v0-plain", "claim_sha256": S.sha256hex(raw), "created_at": "2026-09-%02dT00:00:00Z" % n}
        prev = S.entry_sha(e, prev); heads[n] = prev
        entries[n] = e
        ots, root = make_ots(e["claim_sha256"], height=800000 + n, pending=(n in pending_n))
        if n not in pending_n:
            roots[800000 + n] = root
        with open(os.path.join(d, "ledger", "%d.json" % n), "w") as f: json.dump(e, f)
        with open(os.path.join(d, "ledger", "%d.raw" % n), "wb") as f: f.write(raw)
        with open(os.path.join(d, "ledger", "%d.ots" % n), "wb") as f: f.write(ots)
    return entries, roots, heads


def run(d, explorer):
    return S.drill("dir:" + d, os.path.join(d, ".work"), fenced=False, get=explorer)


tmp = tempfile.mkdtemp(prefix="survive-")
try:
    print("1. honest copy")
    d = os.path.join(tmp, "honest"); _, roots, heads = build_ledger(d)
    r = run(d, Explorer(roots))
    ok("outcome rebuilt", r["outcome"] == "rebuilt", r.get("outcome"))
    ok("5 entries, range 1..5", r["entries"] == 5 and r["range"] == [1, 5])
    ok("all digests ok", r["digests"]["ok"] == 5 and not r["digests"]["failed"])
    ok("chain rebuilt through 5, head equals recomputation", r["chain"]["rebuilt_through"] == 5 and r["chain"]["head"] == heads[5])
    ok("stamped head in the checkpoint matched", r["chain"]["stamped_heads_matched"] == 1)
    ok("4 anchors confirmed by both explorers, entry 3 pending and listed", r["anchors"]["confirmed"] == 4 and r["anchors"]["pending"] == [3], r["anchors"])
    ok("report carries its own sha256", len(r["report_sha256"]) == 64)
    ok("says what it does not establish", any("true" in x for x in r["does_not_establish"]))

    print("2. one byte changed in a claim")
    d = os.path.join(tmp, "tamper"); build_ledger(d)
    with open(os.path.join(d, "ledger", "2.raw"), "ab") as f: f.write(b"!")
    r = run(d, Explorer(build_ledger(os.path.join(tmp, "t2ref"))[1]))
    ok("findings, digest mismatch at 2", r["outcome"] == "findings" and r["digests"]["failed"][0]["n"] == 2, r["digests"])

    print("3. an entry removed from the middle")
    d = os.path.join(tmp, "hole"); _, roots, _ = build_ledger(d)
    os.remove(os.path.join(d, "ledger", "2.json"))
    r = run(d, Explorer(roots))
    ok("chain broken at 2, reported not skipped", r["chain"]["broken_at"] == 2 and r["outcome"] == "findings", r["chain"])

    print("4. a checkpoint whose stamped head disagrees with the rebuilt chain")
    d = os.path.join(tmp, "badcp"); _, roots, _ = build_ledger(d, mutate="bad_checkpoint")
    r = run(d, Explorer(roots))
    ok("stamped head mismatch is a finding", r["outcome"] == "findings" and r["chain"]["stamped_heads"][0]["result"] == "entry_sha256_mismatch", r["chain"])

    print("5. the two explorers disagree about one block")
    d = os.path.join(tmp, "disagree"); _, roots, _ = build_ledger(d)
    r = run(d, Explorer(roots, disagree={("mempool.space", 800001): "ab" * 32}))
    ok("entry 1 not confirmed, named", r["outcome"] == "findings" and r["anchors"]["failed"][0]["n"] == 1, r["anchors"])

    print("6. the proof is for other bytes")
    d = os.path.join(tmp, "wrongots"); _, roots, _ = build_ledger(d)
    shutil.copy(os.path.join(d, "ledger", "1.ots"), os.path.join(d, "ledger", "2.ots"))
    r = run(d, Explorer(roots))
    ok("ots digest is not the claim", any(f["n"] == 2 and f["why"] == "ots_digest_is_not_the_claim" for f in r["anchors"]["failed"]), r["anchors"])

    print("7. the guard")
    for u in ["https://ledger.horizonshield.dev/ledger", "https://gate.horizonshield.dev/x", "https://shield.the-horizons-innovation.com/",
              "https://hs-partner-001-mcp.oga-surf-project.workers.dev/", "https://horizonshield.dev/"]:
        try:
            S.guard(u); ok("refused " + u, False)
        except S.Refused as ex:
            ok("operator host refused: " + S.host_of(u), "operator host" in str(ex))
    for u in ["https://example.com/", "http://mempool.space/api/x", "https://mempool.space.evil.example/api"]:
        try:
            S.guard(u); ok("refused " + u, False)
        except S.Refused:
            ok("not allowlisted or not https: " + u, True)
    try:
        S.http_get("https://ledger.horizonshield.dev/ledger?format=json"); ok("http_get refuses before connecting", False)
    except S.Refused:
        ok("http_get refuses before connecting", True)

    print("8. a real proof: JIDEC entry 66, blocks 969240 and 969244")
    d = os.path.join(tmp, "real"); os.makedirs(os.path.join(d, "ledger"))
    shutil.copy(os.path.join(HERE, "fixtures", "ledger66.ots"), os.path.join(d, "ledger", "66.ots"))
    ent = {66: {"n": 66, "claim_sha256": REAL_CLAIM_66}}
    ex = Explorer(REAL_ROOTS)
    a = S.check_anchors(d, ent, ex)
    ok("real proof confirmed at the lowest block both explorers agree on (969240)", a["confirmed"] == 1 and a["first_block"] == 969240, a)
    ex2 = Explorer(REAL_ROOTS, disagree={("blockstream.info", 969240): "cd" * 32})
    a = S.check_anchors(d, ent, ex2)
    ok("if 969240 is disputed, 969244 still confirms it", a["confirmed"] == 1 and a["first_block"] == 969244, a)
    a = S.check_anchors(d, {66: {"n": 66, "claim_sha256": "0" * 64}}, ex)
    ok("the real proof does not confirm a different claim", a["confirmed"] == 0 and a["failed"][0]["why"] == "ots_digest_is_not_the_claim", a)

    print("9. the chain recipe is byte identical to the ledger's JavaScript (chain_v1.mjs)")
    js = os.environ.get("CHAIN_V1_MJS") or os.path.join(HERE, "..", "..", "src", "chain_v1.mjs")
    if os.path.exists(js):
        es = [{"n": 1, "schema": "v0-plain", "claim_sha256": "a" * 64, "created_at": "2026-09-01T00:00:00Z"},
              {"n": 2, "claim_sha256": "b" * 64},
              {"n": 3, "schema": "café", "claim_sha256": "c" * 64, "created_at": "2026-09-03T00:00:00Z"}]
        prog = ("import {entrySha, markerSha} from %s; const es=%s; let p='0'.repeat(64); const out=[];"
                "for (const e of es){ p = await entrySha(e,p); out.push(p);} out.push(await markerSha(3,p)); console.log(JSON.stringify(out));"
                % (json.dumps("file://" + os.path.abspath(js)), json.dumps(es)))
        res = subprocess.run(["node", "--input-type=module", "-e", prog], capture_output=True, text=True)
        want, p = [], S.CHAIN_ROOT
        for e in es:
            p = S.entry_sha(e, p); want.append(p)
        want.append(S.marker_sha(3, p))
        ok("python and javascript give the same entry and marker hashes", res.returncode == 0 and json.loads(res.stdout) == want, res.stderr or res.stdout)
    else:
        print("  (chain_v1.mjs not found beside this directory; parity check skipped)")

    print("10. a custodian that cannot hand over a copy is reported, not passed and not crashed")
    r = S.drill("dir:" + os.path.join(tmp, "does-not-exist"), os.path.join(tmp, ".w"), fenced=False, get=Explorer({}))
    ok("an empty copy is not a pass", r["outcome"] == "empty_copy", r.get("outcome"))
    orig = S.copy_from_swh
    S.copy_from_swh = lambda work, wait_s=900: (_ for _ in ()).throw(RuntimeError("vault did not finish"))
    r = S.drill("swh", os.path.join(tmp, ".w2"), fenced=False, get=Explorer({}))
    S.copy_from_swh = orig
    ok("custodian_unavailable with the reason", r["outcome"] == "custodian_unavailable" and "vault" in r["why"], r)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(("=== NG %d / %d ===" % (fails, ran)) if fails else ("survive-v0 全%d件 通過" % ran))
sys.exit(1 if fails else 0)

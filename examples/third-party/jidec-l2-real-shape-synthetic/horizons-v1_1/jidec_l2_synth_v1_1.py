#!/usr/bin/env python3
"""jidec_l2_synth_v1_1.py (v1.1 of jidec_l2_synth.py acf174c6, 2026-11-28): every checkpoint carries
refused_complete_since (vlc-1 PR #12, the field for the first window), a Markdown record is written in one entry of
the plain_note variants (the live ledger holds both kinds), and five variants are added. The fourteen of v1 keep their
names and expectations; their bytes change only by the new field.
jidec_l2_synth.py: SYNTHETIC JIDEC trails in the ledger's real export shape, carrying the L2
checkpoint design settled in vlc-1 PR #12 (2026-11-28). Standard library only. Test keys come from
fixed seeds and sign nothing real.

  python3 -I jidec_l2_synth.py --out <new empty folder>
  python3 -I jidec_l2_synth.py --selftest

The entry shape is the live export's, unchanged: every line carries n, schema, claim_sha256, created_at,
prev_entry_sha256 and entry_sha256 = sha256(canon({n, schema, claim_sha256, created_at,
prev_entry_sha256})), canon = keys sorted, "," and ":" without spaces, non-ASCII escaped. Entry 1 links
to 64 zeros. The export ends in the jidec-head-v1 end marker, whose n is the n of the head it binds and
whose entry_sha256 = sha256(canon({n, schema, prev_entry_sha256, head})), as /ledger/head serves it.

Two fields are added to each export line for L2. Neither is hashed into entry_sha256, so no entry hash
changes:
  record_canonical  the record bytes exactly as the producer wrote them (not re-canonicalized);
                    sha256 of their UTF-8 is claim_sha256, which the entry hash covers
  record_sig        {alg, key_id, sig} for a record that names its signer: Ed25519 over the record bytes

Record schemas: jidec-claim-synthetic-v1 (a submission), nenrin-witness-batch-v1 (one entry per batch),
nenrin-key-statement-v1 (the operator key names the ledger key, written before the first signed
checkpoint) and nenrin-head-checkpoint-v2 (the window declaration and the head it seals, signed by the
ledger key).

Counting rules (issue #12, 2026-11-28): the unit is the entry; `to` is the last entry written before the
checkpoint and `from` is the one after the previous checkpoint's `to`, so a checkpoint entry falls in
the following window; received = written in [from, to] + refused + lost; refused is counted by class and
the window's refusal list is its own file, whose sha256 rides in the checkpoint; lost is an ordinal
given and never written. ledger_head.n equals `to`: a checkpoint declares exactly the span its head
seals.

The tamper variants are built by the same builder with one input changed, so everything downstream of
the change stays consistent, as an operator holding the ledger key would make it.
番人(個人) 2026-11-28. SYNTHETIC: no output of the JIDEC ledger.
"""
import hashlib
import json
import os
import sys

ZERO = "0" * 64

# --------------------------------------------------------------------------- Ed25519 (RFC 8032)
P = 2 ** 255 - 19
Lq = 2 ** 252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)


def _inv(x):
    return pow(x, P - 2, P)


def _add(p1, p2):
    a = (p1[1] - p1[0]) * (p2[1] - p2[0]) % P
    b = (p1[1] + p1[0]) * (p2[1] + p2[0]) % P
    c = 2 * p1[3] * p2[3] * D % P
    d = 2 * p1[2] * p2[2] % P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _mul(s, pt):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, pt)
        pt = _add(pt, pt)
        s >>= 1
    return q


def _recover_x(y, sign):
    if y >= P:
        return None
    x2 = (y * y - 1) * _inv(D * y * y + 1) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


_GY = 4 * _inv(5) % P
_GX = _recover_x(_GY, 0)
G = (_GX, _GY, 1, _GX * _GY % P)


def _enc(pt):
    zi = _inv(pt[2])
    x, y = pt[0] * zi % P, pt[1] * zi % P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _dec(b):
    if len(b) != 32:
        return None
    y = int.from_bytes(b, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % P)


def _h(*parts):
    return int.from_bytes(hashlib.sha512(b"".join(parts)).digest(), "little")


def ed_keypair(seed):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return {"a": a, "prefix": h[32:], "pub": _enc(_mul(a, G))}


def ed_sign(key, msg):
    r = _h(key["prefix"], msg) % Lq
    rb = _enc(_mul(r, G))
    k = _h(rb, key["pub"], msg) % Lq
    return rb + ((r + k * key["a"]) % Lq).to_bytes(32, "little")


def ed_verify(pub, msg, sig):
    if len(sig) != 64:
        return False
    a, r = _dec(pub), _dec(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if a is None or r is None or s >= Lq:
        return False
    k = _h(sig[:32], pub, msg) % Lq
    left, right = _mul(s, G), _add(r, _mul(k, a))
    return (left[0] * right[2] - right[0] * left[2]) % P == 0 and (left[1] * right[2] - right[1] * left[2]) % P == 0


# --------------------------------------------------------------------------- ledger shape
def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def entry_hash(e):
    return sha(canon({k: e[k] for k in ("n", "schema", "claim_sha256", "created_at", "prev_entry_sha256") if k in e}).encode())


def marker_hash(n, head):
    return sha(canon({"n": n, "schema": "jidec-head-v1", "prev_entry_sha256": head, "head": head}).encode())


def key_id(pub):
    return sha(pub)


def record_bytes(rec):
    # the producer's bytes: insertion order, as a JavaScript JSON.stringify writes them
    return json.dumps(rec, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


KEYS = {name: ed_keypair(hashlib.sha256(("jidec-l2-synthetic test key " + name).encode()).digest())
        for name in ("operator", "ledger", "stranger")}


class Builder:
    """Writes entries in order. One ordinal per append that gets a slot; an ordinal in `lost` is
    given and never written (a gap in the chain the checkpoint must declare)."""

    def __init__(self):
        self.lines, self.prev, self.n, self.day = [], ZERO, 0, ""
        self.written = {}            # n -> entry_sha256
        self.last_written = 0
        self.refusals = {}           # window index -> list of refusal lines
        self.files = {}              # file name -> bytes

    def ts(self, hh, mm=0):
        return "%sT%02d:%02d:00.000Z" % (self.day, hh, mm)

    def append(self, rec, hh, mm=0, signer=None, lose=False, raw=None):
        self.n += 1
        if lose:
            return self.n
        rb = raw if raw is not None else record_bytes(rec)
        e = {"n": self.n, "claim_sha256": sha(rb), "prev_entry_sha256": self.prev, "schema": "v0",
             "created_at": self.ts(hh, mm)}
        e["entry_sha256"] = entry_hash(e)
        e["record_canonical"] = rb.decode("utf-8")
        if signer is not None:
            key = KEYS[signer]
            e["record_sig"] = {"alg": "Ed25519", "key_id": key_id(key["pub"]), "sig": ed_sign(key, rb).hex()}
        self.lines.append(e)
        self.prev = e["entry_sha256"]
        self.written[self.n] = e["entry_sha256"]
        self.last_written = self.n
        return self.n

    def head(self):
        n = self.last_written
        h = self.written[n]
        return {"chain": "jidec-chain-v1", "n": n, "entry_sha256": h, "marker_sha256": marker_hash(n, h)}

    def claim(self, i, hh, lose=False):
        return self.append({"schema": "jidec-claim-synthetic-v1", "work": "synthetic claim %d" % i,
                            "body_sha256": sha(b"synthetic claim body %d" % i), "note": "SYNTHETIC"}, hh, lose=lose)

    def witness(self, hh, count):
        return self.append({"schema": "nenrin-witness-batch-v1", "anchored_at": self.ts(hh), "count": count,
                            "ledger_head": self.head(), "note": "SYNTHETIC"}, hh)

    def key_statement(self, hh, signer="operator", ledger="ledger"):
        lk = KEYS[ledger]
        return self.append({"schema": "nenrin-key-statement-v1",
                            "operator_key_id": key_id(KEYS["operator"]["pub"]),
                            "ledger_key": {"alg": "Ed25519", "key_id": key_id(lk["pub"]), "public_key": lk["pub"].hex()},
                            "use": "signs nenrin-head-checkpoint-v2 records written after this entry",
                            "note": "SYNTHETIC"}, hh, signer=signer)

    def refuse(self, w, hh, cls, what):
        self.refusals.setdefault(w, []).append({"at": self.ts(hh), "class": cls, "claim_sha256": sha(what)})

    def note(self, i, hh):
        """a plain-text record, as the live ledger writes v0-plain notes: Markdown, not JSON"""
        return self.append(None, hh, raw=("# synthetic note %d\n\nSYNTHETIC: a plain-text record, bound by its sha256 "
                                          "like any other.\n" % i).encode())

    def checkpoint(self, w, frm, hh, lost=0, signer="ledger", tweak=None, complete_since=None):
        head = self.head()
        to = head["n"]
        written = sum(1 for n in self.written if frm <= n <= to)
        refs = self.refusals.get(w, [])
        body = "".join(json.dumps(x, separators=(",", ":")) + "\n" for x in refs).encode()
        name = "refusals-w%d.jsonl" % w
        self.files[name] = body
        by_class = {}
        for x in refs:
            by_class[x["class"]] = by_class.get(x["class"], 0) + 1
        rec = {"schema": "nenrin-head-checkpoint-v2", "anchored_at": self.ts(hh), "ledger_head": head,
               "production_count": {"from": frm, "to": to, "received": written + len(refs) + lost,
                                    "refused": len(refs), "lost": lost},
               "refused_by_class": dict(sorted(by_class.items())), "refusals_sha256": sha(body),
               "refused_complete_since": frm if complete_since is None else complete_since,
               "signer_key_id": key_id(KEYS[signer]["pub"]),
               "note": "SYNTHETIC: the declaration of [from, to] and the head it seals"}
        if tweak:
            tweak(rec)
        self.append(rec, hh, signer=signer)
        return to

    def marker(self):
        n, h = self.last_written, self.written[self.last_written]
        return {"schema": "jidec-head-v1", "n": n, "head": h, "root": ZERO, "chain": "jidec-chain-v1",
                "prev_entry_sha256": h, "entry_sha256": marker_hash(n, h)}


def build(v="honest"):
    """Three days, three windows, then a tail. v names the one input a variant changes."""
    b = Builder()
    sig_ks = "stranger" if v == "statement_not_operator" else "operator"
    cp2_signer = "stranger" if v == "wrong_key" else "ledger"

    b.day = "2026-12-02"                                    # window 1
    b.key_statement(0, signer=sig_ks)                       # n1
    for i in range(2, 6):                                   # n2..n5
        if i == 4 and v.startswith("plain_note"):
            b.note(i, i)                                    # n4 a Markdown record
        else:
            b.claim(i, i)
    b.witness(6, 4)                                         # n6
    b.refuse(1, 7, "duplicate", b"synthetic claim body 3")
    b.refuse(1, 8, "rejected", b"a malformed claim that was well-formed JSON")
    cs1 = {"partial_first": 3, "complete_since_out_of_range": 8, "complete_since_below_from": 0}.get(v)
    to1 = b.checkpoint(1, 1, 15, complete_since=cs1)        # n7 declares [1, 6]

    b.day = "2026-12-03"                                    # window 2
    b.claim(8, 1, lose=(v in ("hidden_drop", "declared_loss")))   # n8
    b.claim(9, 2)                                           # n9
    b.claim(10, 3, lose=True)                               # n10: given an ordinal, never written
    b.claim(11, 4)                                          # n11
    b.witness(5, 3)                                         # n12
    b.refuse(2, 6, "duplicate", b"synthetic claim body 9")
    lost2 = 2 if v == "declared_loss" else 1

    def tw2(rec):
        pc = rec["production_count"]
        if v == "undercount":
            pc["received"] -= 1
        if v == "hidden_drop":      # the declaration stands as made while n8 existed; n8 is gone
            pc["received"] += 1
        if v == "head_mismatch":
            rec["ledger_head"] = dict(rec["ledger_head"], n=pc["to"] - 1)
        if v == "complete_since_later_window":
            rec["refused_complete_since"] = pc["from"] + 1
        if v == "head_hash_mismatch":
            rec["ledger_head"] = dict(rec["ledger_head"], entry_sha256=b.written[9],
                                      marker_sha256=marker_hash(pc["to"], b.written[9]))
    to2 = b.checkpoint(2, to1 + 1, 15, lost=lost2, signer=cp2_signer, tweak=tw2)   # n13 declares [7, 12]

    b.day = "2026-12-04"                                    # window 3
    for i in range(14, 17):                                 # n14..n16
        b.claim(i, i - 13)
    b.witness(5, 3)                                         # n17

    def tw3(rec):
        pc = rec["production_count"]
        if v == "window_overlap":
            pc["from"] -= 1
            pc["received"] += 1
        if v == "window_gap":
            pc["from"] += 1
            pc["received"] -= 1
        rec["refused_complete_since"] = pc["from"]          # v1.1: the field follows from, so tiling is what fails
    b.checkpoint(3, to2 + 1, 15, tweak=tw3)                 # n18 declares [13, 17]

    b.day = "2026-12-05"                                    # the tail, not yet declared
    b.claim(19, 1, lose=(v == "tail_gap"))                  # n19
    b.claim(20, 2)                                          # n20
    lines = b.lines + [b.marker()]

    if v == "unbound_edit":                                 # bytes changed, claim hash left alone
        e = next(x for x in lines if x.get("n") == 13 and "record_canonical" in x)
        r = json.loads(e["record_canonical"])
        r["production_count"]["lost"] += 1
        r["production_count"]["received"] += 1
        e["record_canonical"] = record_bytes(r).decode("utf-8")
    if v == "plain_note_edited":                            # the note's bytes changed, claim hash left alone
        e = next(x for x in lines if x.get("n") == 4)
        e["record_canonical"] = e["record_canonical"].replace("synthetic note 4", "synthetic note 44")
    if v == "sig_stripped":
        next(x for x in lines if x.get("n") == 13 and "record_sig" in x).pop("record_sig")
    files = dict(b.files)
    if v == "refusal_list_short":                           # the list behind refusals_sha256 lost a line
        files["refusals-w1.jsonl"] = b"".join(files["refusals-w1.jsonl"].splitlines(True)[:-1])
    return lines, files


VARIANTS = [
    ("honest", "L2", "three windows, a declared lost ordinal, refusals by class, a contiguous tail"),
    ("declared_loss", "L2", "an entry lost after its ordinal and declared: a declared loss is not a hidden one"),
    ("undercount", "L1", "window 2 declares one fewer received; re-signed by the ledger key"),
    ("hidden_drop", "L1", "an entry of window 2 removed after the window was declared; the chain and later checkpoints rewritten and re-signed"),
    ("tail_gap", "L1", "an ordinal gap after the last checkpoint"),
    ("unbound_edit", "L0", "checkpoint bytes edited, claim_sha256 left as it was"),
    ("sig_stripped", "L1", "the checkpoint's signature removed"),
    ("wrong_key", "L1", "a checkpoint signed by a key the key history does not name"),
    ("statement_not_operator", "L1", "the key statement signed by a key that is not the operator's"),
    ("head_mismatch", "L1", "ledger_head.n is not the window's `to`"),
    ("head_hash_mismatch", "L1", "ledger_head.entry_sha256 is not the hash of entry `to`"),
    ("window_overlap", "L1", "window 3 starts inside window 2, counts adjusted to close"),
    ("window_gap", "L1", "window 3 starts one past where window 2 ended, counts adjusted to close"),
    ("refusal_list_short", "L1", "the refusal list behind refusals_sha256 lost a line"),
    ("partial_first", "L2", "v1.1: the first window counts refusals only from entry 3 (refused_complete_since 3); L2, read from 3"),
    ("complete_since_later_window", "L1", "v1.1: window 2 says refused_complete_since from + 1; only the first window may"),
    ("complete_since_out_of_range", "L1", "v1.1: window 1 says refused_complete_since 8, past to + 1 (7)"),
    ("complete_since_below_from", "L1", "v1.1: window 1 says refused_complete_since 0, below from"),
    ("plain_note", "L2", "v1.1: entry 4 is a Markdown note, bound by its sha256 and not read as a record"),
    ("plain_note_edited", "L0", "v1.1: the Markdown note's bytes changed, claim_sha256 left as it was"),
]


def write(out):
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit("--out must be a new or empty folder")
    os.makedirs(out, exist_ok=True)
    pins = {"operator_public_key": KEYS["operator"]["pub"].hex(), "operator_key_id": key_id(KEYS["operator"]["pub"]),
            "note": "SYNTHETIC test key from a fixed seed; the real operator key is published out of band"}
    with open(os.path.join(out, "operator_key.json"), "w") as f:
        f.write(json.dumps(pins, indent=1) + "\n")
    index = []
    for v, want, what in VARIANTS:
        lines, files = build(v)
        d = os.path.join(out, v)
        os.makedirs(d)
        p = os.path.join(d, "export.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            for e in lines:
                f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
        for name, body in files.items():
            with open(os.path.join(d, name), "wb") as f:
                f.write(body)
        index.append({"variant": v, "expect": want, "what": what,
                      "export_sha256": sha(open(p, "rb").read()), "marker_sha256": lines[-1]["entry_sha256"]})
    with open(os.path.join(out, "index.json"), "w") as f:
        f.write(json.dumps(index, indent=1) + "\n")
    print("JIDEC_L2_SYNTH_OK %d variants in %s" % (len(index), out))


def selftest():
    ok = []

    def t(name, cond):
        ok.append(bool(cond))
        print(("ok    " if cond else "NG    ") + name)

    sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    k = ed_keypair(sk)
    t("RFC 8032 test 1: public key", k["pub"].hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    sig = ed_sign(k, b"")
    t("RFC 8032 test 1: signature", sig.hex() == "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    t("RFC 8032 test 1: verifies", ed_verify(k["pub"], b"", sig))
    t("a changed message does not verify", not ed_verify(k["pub"], b"x", sig))
    t("S >= L is refused", not ed_verify(k["pub"], b"", sig[:32] + (int.from_bytes(sig[32:], "little") + Lq).to_bytes(32, "little")))
    lines, files = build("honest")
    t("the export ends in the end marker", lines[-1]["schema"] == "jidec-head-v1")
    t("the marker's n is the n of the head it binds (as the live export)", lines[-1]["n"] == lines[-2]["n"] == 20)
    t("ordinal 10 is given and never written", [e["n"] for e in lines[:-1]] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    t("each entry hash is the live recipe", all(entry_hash(e) == e["entry_sha256"] for e in lines[:-1]))
    t("each claim_sha256 is sha256 of the record bytes", all(sha(e["record_canonical"].encode()) == e["claim_sha256"] for e in lines[:-1]))
    cps = [json.loads(e["record_canonical"]) for e in lines[:-1] if '"nenrin-head-checkpoint-v2"' in e["record_canonical"]]
    t("three checkpoints", len(cps) == 3)
    t("windows [1,6] [7,12] [13,17]", [(c["production_count"]["from"], c["production_count"]["to"]) for c in cps] == [(1, 6), (7, 12), (13, 17)])
    t("received per window 8, 7, 5", [c["production_count"]["received"] for c in cps] == [8, 7, 5])
    t("ledger_head.n is `to` in each", all(c["ledger_head"]["n"] == c["production_count"]["to"] for c in cps))
    t("refusals_sha256 is the hash of the window's file", all(c["refusals_sha256"] == sha(files["refusals-w%d.jsonl" % (i + 1)]) for i, c in enumerate(cps)))
    t("the empty refusal list hashes to sha256 of nothing", cps[2]["refusals_sha256"] == sha(b""))
    sigd = [e for e in lines[:-1] if "record_sig" in e]
    t("the key statement and the three checkpoints are signed", [e["n"] for e in sigd] == [1, 7, 13, 18])
    t("the signatures verify", all(ed_verify(KEYS["operator" if e["n"] == 1 else "ledger"]["pub"], e["record_canonical"].encode(), bytes.fromhex(e["record_sig"]["sig"])) for e in sigd))
    t("the build is deterministic", build("honest")[0] == lines)
    t("v1.1: every checkpoint carries refused_complete_since = from in the honest build",
      [c["refused_complete_since"] for c in cps] == [1, 7, 13])
    pl, _ = build("plain_note")
    e4 = next(e for e in pl if e.get("n") == 4)
    t("v1.1: plain_note: entry 4 is Markdown bytes, and its claim is their sha256",
      e4["record_canonical"].startswith("# synthetic note 4") and sha(e4["record_canonical"].encode()) == e4["claim_sha256"])
    n = sum(ok)
    print("jidec_l2_synth_v1_1 selftest %d / %d %s" % (n, len(ok), "all green" if n == len(ok) else "NG"))
    return 0 if n == len(ok) else 1


def main():
    a = sys.argv[1:]
    if a == ["--selftest"]:
        return selftest()
    if len(a) == 2 and a[0] == "--out":
        write(a[1])
        return 0
    print(__doc__.split("\n\n")[1])
    return 2


if __name__ == "__main__":
    sys.exit(main())

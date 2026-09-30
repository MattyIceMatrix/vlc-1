#!/usr/bin/env python3
"""Verify the Tessera tile log captured by capture/scripts/tessera.sh, with the
standard library only -- the integrity check the VLC-1 checker cannot do, because
conformance.py has no Merkle-tree mechanism (its MECHANISMS list is hash chains).

  python3 verify_tlog.py log   DIR VKEY [OLD_CHECKPOINT] [--proofs VERIFY_JSONL]
  python3 verify_tlog.py jsonl FILE VKEY

`log` reads the log as Tessera wrote it (C2SP tlog-tiles layout): the checkpoint,
the entry bundles and the level-0 hash tile. It checks
  1. the checkpoint is a C2SP signed note with a valid Ed25519 signature by VKEY
     (a C2SP signed-note verifier key: name+keyhash+base64(0x01||pubkey));
  2. the RFC 6962 leaf hash of every entry equals the hash Tessera stored in the
     level-0 tile, and the RFC 6962 root over all entries equals the checkpoint's
     root; the checkpoint's size equals the number of entries;
  3. with OLD_CHECKPOINT: it is signed by VKEY, and the root over its first `size`
     entries equals its root (the log was extended, not rewritten, since);
  4. with --proofs: every inclusion proof and the consistency proof that
     tlogcap.go wrote (built by Tessera's client from the tiles) verifies by the
     RFC 9162 algorithms against the checkpoint roots.
`jsonl` reads a file produced by convert.py: checks 1 and 2 on the delivered
records (entries in order, then the checkpoint record carrying the raw note).

Prints one line per check; exits 0 if every check passed, 1 otherwise.
Deterministic; writes nothing.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------- Ed25519 (RFC 8032 s.5.1.7)
P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)


def _add(a, b):
    A, B = (a[1] - a[0]) * (b[1] - b[0]) % P, (a[1] + a[0]) * (b[1] + b[0]) % P
    C, Dd = 2 * a[3] * b[3] * D % P, 2 * a[2] * b[2] % P
    E, F, G, H = B - A, Dd - C, Dd + C, B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def _mul(s, pt):
    r = (0, 1, 1, 0)
    while s:
        if s & 1:
            r = _add(r, pt)
        pt = _add(pt, pt)
        s >>= 1
    return r


def _eq(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % P == 0 and (a[1] * b[2] - b[1] * a[2]) % P == 0


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        if sign:
            return None
        x = 0
    else:
        x = pow(x2, (P + 3) // 8, P)
        if (x * x - x2) % P:
            x = x * SQRT_M1 % P
        if (x * x - x2) % P:
            return None
        if (x & 1) != sign:
            x = P - x
    return (x, y, 1, x * y % P)


_GY = 4 * pow(5, P - 2, P) % P
G = _decompress(_GY.to_bytes(32, "little"))


def ed25519_verify(pub, msg, sig):
    if len(sig) != 64:
        return False
    A, R = _decompress(pub), _decompress(sig[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= Q:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + pub + msg).digest(), "little") % Q
    return _eq(_mul(s, G), _add(R, _mul(h, A)))


# ---------------------------------------------------------------- C2SP signed note / checkpoint
def parse_vkey(vkey):
    name, keyhash, key = vkey.strip().split("+", 2)
    raw = base64.b64decode(key)
    if raw[0] != 1 or len(raw) != 33:
        raise ValueError("not an Ed25519 note verifier key")
    kh = hashlib.sha256(name.encode() + b"\n" + raw).digest()[:4]
    if kh.hex() != keyhash:
        raise ValueError("verifier key hash does not match its key")
    return name, kh, raw[1:]


def open_note(text, vkey):
    """Returns (body, error). The body is the signed text, up to the blank line."""
    name, kh, pub = parse_vkey(vkey)
    i = text.rfind("\n\n")
    if i < 0:
        return None, "no signature block"
    body, sigs = text[: i + 1], text[i + 2:]
    for line in sigs.splitlines():
        if not line.startswith("— "):
            return None, f"malformed signature line {line!r}"
        n, b = line[2:].rsplit(" ", 1)
        raw = base64.b64decode(b)
        if n == name and raw[:4] == kh:
            if ed25519_verify(pub, body.encode(), raw[4:]):
                return body, None
            return None, f"signature by {name} does not verify"
    return None, f"no signature by {name}"


def parse_checkpoint(body):
    lines = body.split("\n")
    return lines[0], int(lines[1]), base64.b64decode(lines[2])


# ---------------------------------------------------------------- RFC 6962 / RFC 9162
def leaf_hash(b):
    return hashlib.sha256(b"\x00" + b).digest()


def node(l, r):
    return hashlib.sha256(b"\x01" + l + r).digest()


def mth(leaves):
    """RFC 6962 s.2.1 Merkle Tree Hash over leaf hashes."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaves[0]
    k = 1
    while k * 2 < n:
        k *= 2
    return node(mth(leaves[:k]), mth(leaves[k:]))


def verify_inclusion(idx, size, leaf, proof, root):
    """RFC 9162 s.2.1.3.2."""
    if idx >= size:
        return False
    fn, sn, r = idx, size - 1, leaf
    for p in proof:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = node(p, r)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            r = node(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r == root


def verify_consistency(n1, n2, proof, r1, r2):
    """RFC 9162 s.2.1.4.2."""
    if n1 == n2:
        return not proof and r1 == r2
    if n1 == 0 or n1 > n2 or not proof:
        return False
    path = list(proof)
    if n1 & (n1 - 1) == 0:
        path.insert(0, r1)
    fn, sn = n1 - 1, n2 - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1
    fr = sr = path[0]
    for c in path[1:]:
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            fr, sr = node(c, fr), node(c, sr)
            if not fn & 1:
                while not fn & 1 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            sr = node(sr, c)
        fn >>= 1
        sn >>= 1
    return sn == 0 and fr == r1 and sr == r2


# ---------------------------------------------------------------- C2SP tlog-tiles layout
def fmt_n(n):
    s = f"{n:03d}"
    groups = []
    while n >= 1000:
        groups.insert(0, f"{n % 1000:03d}")
        n //= 1000
    groups.insert(0, f"{n:03d}")
    return "/".join(["x" + g for g in groups[:-1]] + [groups[-1]]) if len(groups) > 1 else s


def tile_path(kind, idx, size):
    w = size - idx * 256
    return f"tile/{kind}/{fmt_n(idx)}" + (f".p/{w}" if w < 256 else "")


def read_bundle(b):
    out, i = [], 0
    while i < len(b):
        n = int.from_bytes(b[i:i + 2], "big")
        out.append(b[i + 2:i + 2 + n])
        i += 2 + n
    return out


class Report:
    def __init__(self):
        self.bad = 0

    def __call__(self, ok, what):
        print(("ok    " if ok else "FAIL  ") + what)
        self.bad |= not ok


def check_log(d, vkey, old=None, proofs=None):
    rep, d = Report(), Path(d)
    body, err = open_note(d.joinpath("checkpoint").read_text(), vkey)
    rep(err is None, "checkpoint signature" + (f": {err}" if err else ""))
    if err:
        return 1
    origin, size, root = parse_checkpoint(body)
    entries = []
    for bi in range((size + 255) // 256):
        entries += read_bundle(d.joinpath(tile_path("entries", bi, size)).read_bytes())
    rep(len(entries) == size, f"checkpoint size {size} == {len(entries)} entries in the bundles")
    lh = [leaf_hash(e) for e in entries]
    stored = b"".join(d.joinpath(tile_path("0", ti, size)).read_bytes() for ti in range((size + 255) // 256))
    rep(stored == b"".join(lh), "level-0 tile holds the RFC 6962 leaf hash of every entry")
    rep(mth(lh) == root, f"RFC 6962 root over the entries == checkpoint root {base64.b64encode(root).decode()}")
    if old:
        ob, err = open_note(Path(old).read_text(), vkey)
        rep(err is None, "old checkpoint signature" + (f": {err}" if err else ""))
        if ob:
            _, osize, oroot = parse_checkpoint(ob)
            rep(osize <= size and mth(lh[:osize]) == oroot,
                f"old checkpoint (size {osize}) is the root of the first {osize} entries")
    if proofs:
        for l in Path(proofs).read_text().splitlines():
            o = json.loads(l)
            pf = [base64.b64decode(x) for x in o.get("proof") or []]
            if o.get("check") == "inclusion":
                i = o["index"]
                rep(o["tree_size"] == size and base64.b64decode(o["leaf_hash"]) == lh[i]
                    and verify_inclusion(i, size, lh[i], pf, root),
                    f"inclusion proof for entry {i} ({len(pf)} hashes)")
            elif o.get("check") == "consistency":
                rep(o["to_size"] == size and verify_consistency(
                    o["from_size"], size, pf, base64.b64decode(o["from_root"]), root),
                    f"consistency proof {o['from_size']} -> {size} ({len(pf)} hashes)")
    return rep.bad


def check_jsonl(f, vkey):
    rep = Report()
    recs = [json.loads(l) for l in Path(f).read_text().splitlines() if l.strip()]
    ents = [r for r in recs if r.get("class") == "entry"]
    cps = [r for r in recs if r.get("class") == "checkpoint"]
    rep(len(cps) == 1 and recs[-1] is cps[0], "one checkpoint record, last")
    if not cps:
        return 1
    body, err = open_note(cps[0]["note"], vkey)
    rep(err is None, "checkpoint signature" + (f": {err}" if err else ""))
    if err:
        return 1
    origin, size, root = parse_checkpoint(body)
    rep(len(ents) == size, f"checkpoint size {size} == {len(ents)} entry records")
    rep([r.get("index") for r in ents] == list(range(len(ents))), "entry indices run 0..n-1 without a gap")
    lh = [leaf_hash(r["data"].encode()) for r in ents]
    rep(mth(lh) == root, "RFC 6962 root over the delivered entries == signed checkpoint root")
    return rep.bad


if __name__ == "__main__":
    a = sys.argv[1:]
    pr = None
    if "--proofs" in a:
        i = a.index("--proofs")
        pr = a[i + 1]
        del a[i:i + 2]
    if len(a) >= 3 and a[0] == "log":
        sys.exit(check_log(a[1], Path(a[2]).read_text() if Path(a[2]).is_file() else a[2],
                           a[3] if len(a) > 3 else None, pr))
    if len(a) == 3 and a[0] == "jsonl":
        sys.exit(check_jsonl(a[1], Path(a[2]).read_text() if Path(a[2]).is_file() else a[2]))
    raise SystemExit(__doc__)

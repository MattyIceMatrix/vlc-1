#!/usr/bin/env python3
import hashlib, json, pathlib, sys, urllib.request
from verifier import verify, check_profile, check_anchor, verify_workflow, verify_chain, merkle_root
ROOT = pathlib.Path(__file__).resolve().parent
VECTOR_ROOT = next((p for p in (ROOT/"vectors", ROOT.parent/"vectors", ROOT.parent.parent/"vectors") if (p/"index.json").exists()), None)
if VECTOR_ROOT is None: raise FileNotFoundError("AER-1 vectors/index.json not found from " + str(ROOT))
AER1_ROOT = next((p for p in (ROOT/"aer-1", ROOT.parent/"aer-1", ROOT.parent.parent/"aer-1") if p.is_dir()), None)
INDEX_URL = "https://zambo.dev/aer1/test-vectors/index.json"
def load_index(live=False):
    if live:
        with urllib.request.urlopen(INDEX_URL, timeout=20) as r: return json.load(r)
    return json.loads((VECTOR_ROOT/"index.json").read_text())
def load_vector(v, live=False):
    if live:
        for url in (f"https://zambo.dev/aer1/test-vectors/{v['fixture']}", f"https://zambo.dev/aer1/test-vectors/v1.3/{v['fixture'].split('/',1)[-1]}"):
            try:
                with urllib.request.urlopen(url, timeout=20) as r: return json.load(r)
            except Exception: pass
    return json.loads((VECTOR_ROOT/v["fixture"]).read_text())
def legacy_merkle_root(preimages):
    level=[hashlib.sha256(p.encode()).digest() for p in preimages]
    while len(level)>1:
        if len(level)%2: level.append(level[-1])
        level=[hashlib.sha256(level[i]+level[i+1]).digest() for i in range(0,len(level),2)]
    return level[0].hex() if level else hashlib.sha256(b"").hexdigest()
def main():
    live = "--live" in sys.argv; idx=load_index(live); passed=0
    for v in idx["vectors"]:
        r=load_vector(v,live); result=not verify(r)
        if v["id"]=="missing-inputs": result=result and not check_profile(r)
        if v.get("vector_group")=="anchored": result=result and not check_anchor(r)
        ok=result==v["expected_verdict"]; passed+=ok; print(f"{'PASS' if ok else 'FAIL'} {v['id']}")
    print(f"CONFORMANCE: {passed}/{len(idx['vectors'])}"); corpus_ok=passed==len(idx["vectors"])
    chain_total=0; chain_passed=0; chain_aborted=False
    try:
        if AER1_ROOT is None: raise FileNotFoundError("aer-1/chain-vectors.json not found from " + str(ROOT))
        cvs=json.loads((AER1_ROOT/"chain-vectors.json").read_text()).get("vectors")
        if not isinstance(cvs, list) or not cvs: raise ValueError("chain vectors list is missing or empty")
        for v in cvs:
            if v.get("expected_verdict") not in ("valid","invalid"): raise ValueError(f"bad verdict in chain vector {v.get('name')}")
            entries = v.get("entries") if v.get("entries") is not None else v.get("timeline")
            try: got = entries is not None and (not verify_chain(entries))==(v["expected_verdict"]=="valid")
            except (KeyError, TypeError): got=False
            chain_total+=1; chain_passed+=got; print(f"[chain] {'PASS' if got else 'FAIL'} {v.get('name')}")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc: print(f"[chain] FAIL closed: {exc}"); chain_aborted=True
    print(f"CHAIN: {chain_passed}/{chain_total}"); chain_ok=not chain_aborted and chain_total>0 and chain_passed==chain_total
    merkle_total=0; merkle_passed=0; merkle_aborted=False
    try:
        if AER1_ROOT is None: raise FileNotFoundError("aer-1/merkle-vectors.json not found from " + str(ROOT))
        mvs=json.loads((AER1_ROOT/"merkle-vectors.json").read_text()).get("vectors")
        if not isinstance(mvs, list) or not mvs: raise ValueError("merkle vectors list is missing or empty")
        for v in mvs:
            name=v.get("name"); ok=False; detail=""
            if isinstance(v.get("receipt_ids"), list) and isinstance(v.get("expected_root"), str):
                rids,root=v["receipt_ids"],v["expected_root"]
                if any(not isinstance(r, str) for r in rids): raise ValueError(f"malformed merkle vector {name}")
                if merkle_root(rids)!=root: detail="recomputed root mismatch"
                else:
                    verdict=v.get("expected_workflow_verdict")
                    if verdict is None: ok=True
                    elif verdict in ("valid","invalid"):
                        wf={"steps":[{"seq":i+1,"receipt_id":r} for i,r in enumerate(rids)],"merkle_root":root}
                        fails=verify_workflow(wf); want_valid=verdict=="valid"; rb=v.get("rejected_by")
                        ok=(not fails)==want_valid and (want_valid or not isinstance(rb, str) or any(rb in x for x in fails))
                        detail=f"verdict={verdict}, failures={fails}"
                    else: raise ValueError(f"bad verdict in merkle vector {name}")
            elif isinstance(v.get("leaves"), list) and isinstance(v.get("expected_root"), str):
                leg=legacy_merkle_root([l["preimage"] for l in v["leaves"]])
                ok=leg==v["expected_root"] and leg!=v.get("must_not_equal"); detail=f"legacy_root={leg}"
            else: raise ValueError(f"malformed merkle vector {name}")
            merkle_total+=1; merkle_passed+=ok
            print(f"[merkle] {'PASS' if ok else 'FAIL'} {name} ({detail})")
    except (FileNotFoundError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc: print(f"[merkle] FAIL closed: {exc}"); merkle_aborted=True
    merkle_ok=not merkle_aborted and merkle_total>0 and merkle_passed==merkle_total
    print(f"MERKLE: {merkle_passed}/{merkle_total}")
    return 0 if corpus_ok and chain_ok and merkle_ok else 1
if __name__=="__main__": sys.exit(main())

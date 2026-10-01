#!/usr/bin/env bash
set -euo pipefail
REPO_URL="${1:-https://gitlab.com/rambozambodotdev/zambo.git}"
WORKDIR="${AER1_QUICKSTART_DIR:-$(mktemp -d)}"
START=$(date +%s%N)
cleanup(){ if [[ -z "${AER1_KEEP:-}" && -z "${AER1_QUICKSTART_DIR:-}" ]]; then rm -rf "$WORKDIR"; fi; }
trap cleanup EXIT
printf 'AER-1 clean-room quickstart\nRepository: %s\n' "$REPO_URL"
git clone --depth 1 --quiet "$REPO_URL" "$WORKDIR/zambo"
command -v python3 >/dev/null
command -v node >/dev/null
python3 - "$WORKDIR/zambo" <<'PY'
import base64, calendar, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path
root=Path(sys.argv[1]); idx=json.loads((root/'aer1-implementations/vectors/index.json').read_text()); vectors=idx['vectors']
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'); RFC=re.compile(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$'); HASH=re.compile(r'^sha256:[0-9a-f]{64}$')
def valid_ts(x):
 m=RFC.fullmatch(x) if isinstance(x,str) else None
 if not m:return False
 y,mo,d,h,mi,s=map(int,m.groups()[:6]);z=m.group(7)
 if not 1<=mo<=12 or not 1<=d<=calendar.monthrange(y,mo)[1] or h>23 or mi>59 or s>59:return False
 return z=='Z' or (int(z[1:3])<=23 and int(z[4:])<=59)
def core(r):
 if not isinstance(r,dict):return False
 fields=('id','receipt_schema_version','created_at','tool','provenance_class','canonical_bytes','output_hash','verification_status')
 if any(k not in r for k in fields):return False
 if not UUID.fullmatch(r['id']) or r['receipt_schema_version']!='0.3' or not valid_ts(r['created_at']):return False
 t=r['tool'];p=r['provenance_class']
 if not isinstance(t,dict) or any(not isinstance(t.get(k),str) or not t[k] for k in ('name','version','scope')):return False
 if not (p in ('OBSERVED VIA GATEWAY','LOGGED BY AGENT') or isinstance(p,str) and re.fullmatch(r'EXECUTED BY [A-Z0-9][A-Z0-9 ._-]*',p)):return False
 try:
  b=r['canonical_bytes'];raw=base64.b64decode(b,validate=True)
  if not isinstance(b,str) or len(b)%4 or base64.b64encode(raw).decode()!=b: return False
  raw.decode('utf-8')
 except Exception:return False
 return bool(HASH.fullmatch(r['output_hash']) and r['output_hash']=='sha256:'+hashlib.sha256(raw).hexdigest() and r['verification_status']=='verified')
def anchor(r):
 a=r.get('anchor');
 if not isinstance(a,dict) or set(a)!={'log','leaf_hash','anchored_at','proof'}:return False
 try:raw=base64.b64decode(r['canonical_bytes'],validate=True)
 except Exception:return False
 return a.get('leaf_hash')=='sha256:'+hashlib.sha256(raw).hexdigest() and valid_ts(a.get('anchored_at')) and isinstance(a.get('proof'),dict)
def profile(r):
 try:return 'inputs' in json.loads(base64.b64decode(r['canonical_bytes']).decode())
 except Exception:return False
passed=0
for v in vectors:
 r=json.loads((root/'aer1-implementations/vectors'/v['fixture']).read_text()); actual=core(r)
 if v.get('vector_group')=='anchored': actual=actual and anchor(r)
 if v.get('vector_group')=='invalid-profile': actual=actual and profile(r)
 if actual==v['expected_verdict']:passed+=1
 else:print('FAIL',v['id'])
print(f'CONFORMANCE: {passed}/{len(vectors)}')
if passed!=len(vectors):raise SystemExit(1)
PY
NODE_VERSION=$(node --version)
ELAPSED=$(( ($(date +%s%N)-START)/1000000 ))
VECTOR_COUNT=$(python3 -c "import json; print(len(json.load(open('$WORKDIR/zambo/aer1-implementations/vectors/index.json'))['vectors']))")
printf 'PASS: %s/%s vectors; Node %s available; wall-clock %sms\n' "$VECTOR_COUNT" "$VECTOR_COUNT" "$NODE_VERSION" "$ELAPSED"

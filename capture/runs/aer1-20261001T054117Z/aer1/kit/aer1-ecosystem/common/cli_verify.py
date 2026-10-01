#!/usr/bin/env python3
import base64,json,sys
from aer1_core import verify,check_anchor,check_profile
try:
    r=json.load(open(sys.argv[1])); failures=verify(r)
    try:
        payload=json.loads(base64.b64decode(r.get('canonical_bytes','')).decode('utf-8'))
        if isinstance(payload,dict) and isinstance(payload.get('tool'),str) and 'inputs' not in payload: failures += check_profile(r)
    except Exception: pass
    if isinstance(r.get('anchor'),dict) and any(k in r['anchor'] for k in ('log','leaf_hash','anchored_at','proof')): failures += check_anchor(r)
except Exception as e: failures=[str(e)]
if failures:
    print('FAIL: '+'; '.join(dict.fromkeys(failures))); sys.exit(1)
print('PASS'); sys.exit(0)

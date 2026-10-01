#!/usr/bin/env python3
import base64,binascii,json,pathlib,re,sys
from datetime import datetime
ROOT=pathlib.Path(__file__).parent; sys.path.insert(0,str(ROOT.parent/'common')); from aer1_core import verify
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'); RFC=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$'); HASH=re.compile(r'^sha256:[0-9a-f]{64}$')
def schema_errors(r):
    f=[]
    if not isinstance(r,dict): return ['root must be an object']
    required=['id','receipt_schema_version','created_at','tool','provenance_class','canonical_bytes','output_hash','verification_status']
    f += [f'missing required property: {k}' for k in required if k not in r]
    if f:return f
    if not isinstance(r['id'],str) or not UUID.fullmatch(r['id']):f.append('id does not match UUID v4 pattern')
    if r['receipt_schema_version']!='0.3':f.append('receipt_schema_version must be 0.3')
    if not isinstance(r['created_at'],str) or not RFC.fullmatch(r['created_at']):f.append('created_at does not match RFC 3339 pattern')
    else:
        try: datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))
        except ValueError: f.append('created_at is not a valid calendar timestamp')
    t=r['tool']
    if not isinstance(t,dict) or any(not isinstance(t.get(k),str) or not t[k] for k in ('name','version','scope')):f.append('tool does not satisfy object schema')
    if not isinstance(r['provenance_class'],str) or not r['provenance_class']:f.append('provenance_class must be a non-empty string')
    b=r['canonical_bytes']
    if not isinstance(b,str) or not re.fullmatch(r'[A-Za-z0-9+/]*={0,2}',b) or len(b)%4: f.append('canonical_bytes is not strict base64')
    if not isinstance(r['output_hash'],str) or not HASH.fullmatch(r['output_hash']):f.append('output_hash does not match sha256 pattern')
    if r['verification_status']!='verified':f.append('verification_status must equal verified')
    if 'anchor' in r:
        a=r['anchor']
        if not isinstance(a,dict): f.append('anchor must be an object')
        else:
            if 'log' in a and not isinstance(a['log'],str): f.append('anchor.log must be a string')
            if 'leaf_hash' in a and (not isinstance(a['leaf_hash'],str) or not HASH.fullmatch(a['leaf_hash']) or a['leaf_hash'] != r.get('output_hash')): f.append('anchor.leaf_hash is invalid or does not match output_hash')
            if 'anchored_at' in a:
                try: datetime.fromisoformat(a['anchored_at'].replace('Z','+00:00'))
                except (ValueError,TypeError): f.append('anchor.anchored_at is invalid')
            if any(k in a for k in ('log','leaf_hash','anchored_at')) and not isinstance(a.get('proof'),dict): f.append('anchor.proof is required for a structured anchor')
    return f
def validate(r):
    f=schema_errors(r)+verify(r)
    try:
        raw=base64.b64decode(r['canonical_bytes'],validate=True); payload=json.loads(raw.decode('utf-8'))
        if isinstance(payload,dict) and isinstance(payload.get('tool'),str) and 'inputs' not in payload: f.append('canonical payload is missing inputs')
    except Exception: pass
    return f
if __name__=='__main__':
    try:r=json.load(open(sys.argv[1])); f=validate(r)
    except Exception as e:f=[f'JSON parse error: {e}']
    if f: print('FAIL\n- '+'\n- '.join(dict.fromkeys(f)));sys.exit(1)
    print('PASS');sys.exit(0)

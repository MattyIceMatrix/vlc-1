#!/usr/bin/env python3
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]/'common'));from aer1_core import verify,check_anchor,check_profile
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'receipts'); files=sorted(root.rglob('*.json')); bad=[]
for p in files:
 try:
  r=json.loads(p.read_text()); f=verify(r)
  if isinstance(r.get('anchor'),dict) and any(k in r['anchor'] for k in ('log','leaf_hash','anchored_at','proof')): f+=check_anchor(r)
  if f: bad.append((p,f))
 except Exception as e: bad.append((p,[str(e)]))
for p,f in bad: print('FAIL',p,'; '.join(dict.fromkeys(f)))
print(f'AER-1 receipts: {len(files)-len(bad)}/{len(files)} valid')
sys.exit(1 if bad else 0)

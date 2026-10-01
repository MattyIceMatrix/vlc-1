import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).parent; sys.path.insert(0,str(ROOT.parent/'common')); from aer1_core import verify
from ce_wrap import wrap,unwrap
idx=json.loads((ROOT.parent/'certifier/vectors/index.json').read_text()); receipts=[]
for v in idx['vectors']:
    if v['expected_verdict']:
        receipts.append(json.loads((ROOT.parent/'certifier/vectors'/v['fixture']).read_text()))
        if len(receipts)==5: break
count=0
for r in receipts:
    ce=wrap(r); assert unwrap(ce)==r and not verify(unwrap(ce)); count+=1
    event={'version':'0','id':ce['id'],'source':'aer1.bridge','detail-type':ce['type'],'time':ce['time'],'detail':ce}; assert unwrap(event)==r; count+=1
    p=subprocess.run(['node',str(ROOT/'ce_wrap.js'),'unwrap'],input=json.dumps(ce),text=True,capture_output=True,check=True); assert json.loads(p.stdout)==r
print(f'CLOUDEVENTS BINDING: {count}/10 round trips')

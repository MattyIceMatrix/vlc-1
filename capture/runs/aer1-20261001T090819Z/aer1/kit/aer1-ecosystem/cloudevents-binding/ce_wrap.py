#!/usr/bin/env python3
import json,sys

def _receipt(value): return json.loads(value) if isinstance(value,str) else dict(value)
def wrap(receipt_json):
    r=_receipt(receipt_json); tool=r.get('tool',{}); name=tool.get('name','unknown'); return {'specversion':'1.0','id':r['id'],'source':'/tools/'+name,'type':'dev.zambo.aer1.receipt.v1','time':r['created_at'],'datacontenttype':'application/json','data':r,'aer1provenance':r.get('provenance_class'),'aer1schemaversion':r.get('receipt_schema_version','0.3')}
def unwrap(ce_json):
    ce=_receipt(ce_json)
    if 'detail' in ce and isinstance(ce['detail'],dict): ce=ce['detail']
    if ce.get('specversion')!='1.0': raise ValueError('not a CloudEvents 1.0 event')
    r=ce.get('data')
    if not isinstance(r,dict): raise ValueError('CloudEvent data is not an AER-1 receipt')
    if ce.get('id') and ce.get('id')!=r.get('id'): raise ValueError('CloudEvent id does not match receipt id')
    return r
if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1] not in ('wrap','unwrap'): raise SystemExit('usage: ce_wrap.py wrap|unwrap file.json')
    fn=wrap if sys.argv[1]=='wrap' else unwrap; print(json.dumps(fn(json.loads(open(sys.argv[2]).read())),separators=(',',':')))

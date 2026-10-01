#!/usr/bin/env python3
import base64, hashlib, json, pathlib, sys, uuid
from datetime import datetime, timezone

def _attrs(span):
    out={}
    attrs=span.get('attributes',{})
    if isinstance(attrs,list):
        for item in attrs:
            if not isinstance(item,dict) or 'key' not in item: continue
            v=item.get('value',{}); out[item['key']]=next((v[k] for k in ('stringValue','intValue','doubleValue','boolValue','arrayValue','kvlistValue') if k in v), None)
    elif isinstance(attrs,dict): out=attrs
    return out

def _uuid(span):
    raw=bytearray(hashlib.sha256((str(span.get('traceId',''))+str(span.get('spanId',''))).encode()).digest()[:16]); raw[6]=(raw[6]&0x0f)|0x40; raw[8]=(raw[8]&0x3f)|0x80; return str(uuid.UUID(bytes=bytes(raw)))

def _time(span):
    ns=int(span.get('startTimeUnixNano',0)); return datetime.fromtimestamp(ns/1_000_000_000,tz=timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

def convert(span):
    a=_attrs(span); name=a.get('gen_ai.tool.name') or a.get('gen_ai.agent.name') or a.get('gen_ai.operation.name') or 'otel-span'
    inputs={}; outputs={}
    for k,v in a.items():
        if k.startswith('gen_ai.input') or k in ('gen_ai.request.model','gen_ai.request.temperature','gen_ai.request.max_tokens'): inputs[k]=v
        elif k.startswith('gen_ai.output') or k in ('gen_ai.response.id','gen_ai.response.model','gen_ai.response.finish_reasons'): outputs[k]=v
    if not inputs: inputs={'span_name':span.get('name','')}
    if not outputs: outputs={'status':span.get('status',{}).get('code','OK') if isinstance(span.get('status'),dict) else 'OK'}
    payload={'inputs':inputs,'outputs':outputs}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return {'id':_uuid(span),'receipt_schema_version':'0.3','created_at':_time(span),'tool':{'name':str(name),'version':'otel-export','scope':'public'},'provenance_class':'EXECUTED BY OTEL','canonical_bytes':base64.b64encode(raw).decode(),'output_hash':'sha256:'+hashlib.sha256(raw).hexdigest(),'verification_status':'verified','otel_trace_id':span.get('traceId'),'otel_span_id':span.get('spanId'),'otel_status':span.get('status')}

def spans_from_export(data):
    if isinstance(data,list): return data
    out=[]
    for rs in data.get('resourceSpans',[]):
        for ss in rs.get('scopeSpans',rs.get('instrumentationLibrarySpans',[])):
            out.extend(ss.get('spans',[]))
    return out

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python3 otel2aer1.py spans.json')
    data=json.loads(pathlib.Path(sys.argv[1]).read_text())
    for span in spans_from_export(data): print(json.dumps(convert(span),ensure_ascii=False))
if __name__=='__main__': main()

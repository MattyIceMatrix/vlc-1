#!/usr/bin/env python3
"""A dependency-light MCP stdio server; install mcp for host integration if desired."""
import base64,datetime,hashlib,json,sys,uuid,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]/'common'));from aer1_core import verify

def emit(args):
    payload={'inputs':args.get('inputs',{}),'outputs':args.get('outputs',{})};raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return {'id':str(uuid.uuid4()),'receipt_schema_version':'0.3','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z'),'tool':{'name':args.get('tool_name','mcp-tool'),'version':args.get('tool_version','1.0.0'),'scope':args.get('scope','public')},'provenance_class':'EXECUTED BY MCP','canonical_bytes':base64.b64encode(raw).decode(),'output_hash':'sha256:'+hashlib.sha256(raw).hexdigest(),'verification_status':'verified'}
def call(name,args):
    if name=='verify_receipt':
        try:r=json.loads(args.get('receipt','')) if isinstance(args.get('receipt'),str) else args.get('receipt'); f=verify(r)
        except Exception as e:f=[str(e)]
        return ('PASS: receipt satisfies AER-1 verification rules' if not f else 'FAIL: '+'; '.join(f),not not f)
    if name=='emit_receipt': return (json.dumps(emit(args),ensure_ascii=False),False)
    if name=='explain_receipt':
        try:r=json.loads(args.get('receipt','')) if isinstance(args.get('receipt'),str) else args.get('receipt'); f=verify(r); status='passes' if not f else 'fails'; return (f'This receipt {status} core AER-1 validation. It records tool {r.get("tool",{}).get("name","<unknown>")}, timestamp {r.get("created_at","<missing>")}, and commits to exact canonical UTF-8 bytes with {r.get("output_hash","<missing>")}. It proves the recorded execution payload and commitment; it does not independently prove the external truth of the output.' if isinstance(r,dict) else 'This input is not a receipt object.',False)
        except Exception as e:return ('Could not parse receipt: '+str(e),True)
    return ('Unknown tool: '+name,True)
def response(req):
    rid=req.get('id');method=req.get('method')
    if method=='initialize': result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'aer1-receipts','version':'1.0.0'}}
    elif method=='notifications/initialized': return None
    elif method=='tools/list': result={'tools':[{'name':'verify_receipt','description':'Validate an AER-1 receipt and return reasons.','inputSchema':{'type':'object','properties':{'receipt':{'type':'string'}},'required':['receipt']}},{'name':'emit_receipt','description':'Emit a valid AER-1 receipt from tool inputs and outputs.','inputSchema':{'type':'object','properties':{'tool_name':{'type':'string'},'inputs':{},'outputs':{}},'required':['tool_name','inputs','outputs']}},{'name':'explain_receipt','description':'Explain what an AER-1 receipt proves.','inputSchema':{'type':'object','properties':{'receipt':{'type':'string'}},'required':['receipt']}}]}
    elif method=='tools/call':
        text,iserr=call(req.get('params',{}).get('name',''),req.get('params',{}).get('arguments',{}));result={'content':[{'type':'text','text':text}],'isError':iserr}
    else: return {'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'method not found'}}
    return {'jsonrpc':'2.0','id':rid,'result':result}
for line in sys.stdin:
    try:
        req=json.loads(line); out=response(req)
        if out is not None: print(json.dumps(out,ensure_ascii=False),flush=True)
    except Exception as e: print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':str(e)}}),flush=True)

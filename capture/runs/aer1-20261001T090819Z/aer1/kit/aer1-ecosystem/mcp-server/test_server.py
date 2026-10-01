import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).parent
reqs=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'emit_receipt','arguments':{'tool_name':'smoke','inputs':{'x':1},'outputs':{'ok':True}}}}]
p=subprocess.Popen([sys.executable,str(ROOT/'server.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
out=[]
for r in reqs: p.stdin.write(json.dumps(r)+'\n');p.stdin.flush();out.append(json.loads(p.stdout.readline()))
emitted=json.loads(out[2]['result']['content'][0]['text']); receipt_text=json.dumps(emitted)
for i,name in ((4,'verify_receipt'),(5,'explain_receipt')):
 p.stdin.write(json.dumps({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':name,'arguments':{'receipt':receipt_text}}})+'\n');p.stdin.flush();out.append(json.loads(p.stdout.readline()))
p.terminate();assert out[0]['result']['serverInfo']['name']=='aer1-receipts';assert len(out[1]['result']['tools'])==3;assert out[3]['result']['isError'] is False and out[3]['result']['content'][0]['text'].startswith('PASS');assert out[4]['result']['isError'] is False
print('MCP SERVER: initialize, list, verify, emit, explain smoke tests passed')

import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).parent; idx=json.loads((ROOT.parent/'certifier/vectors/index.json').read_text()); ok=0
for v in idx['vectors']:
    p=ROOT.parent/'certifier/vectors'/v['fixture']; r=subprocess.run([sys.executable,str(ROOT/'validate.py'),str(p)],capture_output=True,text=True); passed=r.returncode==0
    if passed==v['expected_verdict']: ok+=1
    else: print('FAIL',v['id'],v['expected_verdict'],r.stdout,r.stderr)
print(f'SCHEMA CONFORMANCE: {ok}/{len(idx["vectors"])}');sys.exit(0 if ok==len(idx['vectors']) else 1)

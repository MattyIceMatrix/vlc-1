import json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).parent; sys.path.insert(0,str(ROOT.parent/'common')); from aer1_core import verify
p=subprocess.run([sys.executable,str(ROOT/'otel2aer1.py'),str(ROOT/'test_spans.json')],capture_output=True,text=True,check=True)
receipts=[json.loads(line) for line in p.stdout.splitlines() if line.strip()]
assert len(receipts)==5
for receipt in receipts:
    failures=verify(receipt)
    assert not failures, failures
print('OTEL BRIDGE: 5/5 receipts verified')

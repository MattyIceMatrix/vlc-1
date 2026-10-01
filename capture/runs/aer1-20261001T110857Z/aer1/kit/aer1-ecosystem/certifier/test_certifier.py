import json,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).parent
cmd=[sys.executable,str(ROOT/'certify.py'),'--command','python3 ../common/cli_verify.py','--name','python-reference','--out','/tmp/aer1-cert-pass']
r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr;report=json.loads(pathlib.Path('/tmp/aer1-cert-pass/conformance-report.json').read_text());assert report['vectors']['passed']==45 and report['fuzz']['passed']==1000 and report['overall']=='PASS' and report['signature'].startswith('sha256:')
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'broken.py';p.write_text('import sys; print("PASS"); sys.exit(0)')
 r=subprocess.run([sys.executable,str(ROOT/'certify.py'),'--command',f'{sys.executable} {p}','--name','broken','--out',d+'/out'],cwd=ROOT,capture_output=True,text=True);assert r.returncode!=0; bad=json.loads((pathlib.Path(d)/'out/conformance-report.json').read_text());assert bad['overall']=='FAIL' and bad['vectors']['passed']<45
print('CERTIFIER: passing implementation and broken implementation detected')

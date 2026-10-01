import pathlib,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).parents[2]; verifier=ROOT/'ci-templates/verify_receipts.py'
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);shutil.copy(ROOT/'ci-templates/test/valid-receipt.json',p/'valid.json');r=subprocess.run([sys.executable,str(verifier),str(p)],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
 shutil.copy(ROOT/'ci-templates/test/tampered-receipt.json',p/'tampered.json');r=subprocess.run([sys.executable,str(verifier),str(p)],capture_output=True,text=True);assert r.returncode!=0
print('CI TEMPLATES: valid green, tampered red')

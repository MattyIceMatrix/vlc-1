import hashlib,json,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).parent; repo=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent.parent.parent; samples=ROOT/'samples'; out=ROOT/'test-bundle';out.exists() and __import__('shutil').rmtree(out)
r=subprocess.run([sys.executable,str(ROOT/'export_audit_bundle.py'),str(samples),'--repo',str(repo),'--out',str(out)],capture_output=True,text=True,check=True);print(r.stdout.strip());m=json.loads((out/'manifest.json').read_text())
for e in m['files']:
 p=out/e['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'][7:];assert p.stat().st_size==e['bytes']
assert m['receipt_count']==3 and (out/'article-12-mapping.json').exists() and (out/'article-12-mapping.md').exists() and '12(3)(d)' in (out/'article-12-mapping.md').read_text();print('AUDIT BUNDLE: manifest hashes and Article 12 mapping verified')

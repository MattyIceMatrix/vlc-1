#!/usr/bin/env python3
import argparse,datetime,hmac,json,hashlib,os,pathlib,shlex,subprocess,sys
ROOT=pathlib.Path(__file__).parent

def digest(p): return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def run_one(cmd,p,expect,cwd):
    r=subprocess.run(cmd+[str(p)],cwd=cwd,capture_output=True,text=True)
    return {'file':str(p.relative_to(ROOT)),'expected_pass':expect,'actual_pass':r.returncode==0,'ok':(r.returncode==0)==expect,'output':(r.stdout+r.stderr).strip()[-500:]}
def badge(path,passed):
    label='AER-1 Conformant · 45/45' if passed else 'AER-1 Non-Conformant'; color='#16834b' if passed else '#b42318'; w=max(260,len(label)*7+40)
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="30" role="img"><rect width="{w}" height="30" rx="5" fill="{color}"/><text x="{w/2}" y="20" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="white">{label}</text></svg>')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--command');ap.add_argument('--module');ap.add_argument('--name',default='unnamed-implementation');ap.add_argument('--out',default='.');a=ap.parse_args()
    if bool(a.command)==bool(a.module): ap.error('provide exactly one of --command or --module')
    cmd=shlex.split(a.command) if a.command else [sys.executable,'-m',a.module];out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    idx=json.loads((ROOT/'vectors/index.json').read_text()); vectors=[]
    for v in idx['vectors']: vectors.append(run_one(cmd,ROOT/'vectors'/v['fixture'],bool(v['expected_verdict']),ROOT))
    fuzz=[];sys.path.insert(0,str(ROOT.parent/'common'));from aer1_core import verify
    for p in sorted((ROOT/'fuzz-corpus').glob('case_*.json')):
        try: expect=not bool(verify(json.loads(p.read_text())))
        except Exception: expect=False
        fuzz.append(run_one(cmd,p,expect,ROOT))
    report={'implementation':a.name,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verifier_command':a.command or ('python -m '+a.module),'vectors':{'total':len(vectors),'passed':sum(x['ok'] for x in vectors),'results':vectors,'input_hashes':{x['file']:digest(ROOT/x['file']) for x in vectors}},'fuzz':{'total':len(fuzz),'passed':sum(x['ok'] for x in fuzz),'results':fuzz,'input_hashes':{x['file']:digest(ROOT/x['file']) for x in fuzz}},'overall':'PASS' if all(x['ok'] for x in vectors+fuzz) else 'FAIL'}
    key=os.environ.get('AER1_CERTIFIER_KEY','development-only-certifier-key').encode();unsigned=json.dumps(report,sort_keys=True,separators=(',',':')).encode();report['signature_algorithm']='HMAC-SHA256';report['signature']='sha256:'+hmac.new(key,unsigned,hashlib.sha256).hexdigest()
    (out/'conformance-report.json').write_text(json.dumps(report,indent=2));badge(out/'aer1-conformant.svg',report['overall']=='PASS');print(f"{report['overall']}: vectors {report['vectors']['passed']}/{report['vectors']['total']}, fuzz {report['fuzz']['passed']}/{report['fuzz']['total']}");return 0 if report['overall']=='PASS' else 1
if __name__=='__main__':sys.exit(main())

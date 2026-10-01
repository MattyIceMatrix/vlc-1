#!/usr/bin/env python3
import argparse,base64,copy,hashlib,json,os,pathlib,random,re,shutil,subprocess,tempfile,time,uuid,html
EXPECTED=['python','java','csharp','swift','rust','go','typescript']

def discover(root):
    p=root/'aer1-implementations'; found={}
    markers={'rust':'rust/Cargo.toml','go':'go/go.mod','typescript':'typescript/package.json','python':'python/verifier.py','java':'java/pom.xml','csharp':'csharp/Aer1.csproj','swift':'swift/Package.swift'}
    for lang,mark in markers.items():
        if (p/mark).exists(): found[lang]=(p/mark).parent
    return found

def native_setup(found,root,tmp):
    cmds={}; cleanup=[]
    if 'rust' in found:
        d=found['rust']; src=d/'src/bin/interop_gap_verify.rs'; src.write_text('use std::env; use std::fs; fn main(){let p=env::args().nth(1).unwrap();let r=aer1::load(std::path::Path::new(&p)); match aer1::verify(&r){Ok(())=>println!("PASS"),Err(f)=>{println!("FAIL {}",f.join("; "));std::process::exit(1)}}}')
        cmds['rust']=['cargo','run','--quiet','--bin','interop_gap_verify','--']; cleanup.append(src)
    if 'go' in found:
        d=found['go']; g=d/'cmd/interop_gap_verify';g.mkdir(exist_ok=True);(g/'main.go').write_text('package main\nimport("fmt";"os";"aer1")\nfunc main(){r:=aer1.Load(os.Args[1]);if f:=aer1.Verify(r);len(f)>0{fmt.Println("FAIL");os.Exit(1)};fmt.Println("PASS")}')
        cmds['go']=['go','run','./cmd/interop_gap_verify']; cleanup.append(g)
    if 'typescript' in found:
        d=found['typescript'];
        if not (d/'dist/aer1.js').exists(): subprocess.run(['npm','install','--silent'],cwd=d,check=True);subprocess.run(['npm','run','build','--silent'],cwd=d,check=True)
        cmds['typescript']=['node','-e','import("./dist/aer1.js").then(m=>{let r=m.load(process.argv[1]);let f=m.verify(r);if(f.length){console.log("FAIL",f.join("; "));process.exit(1)}console.log("PASS")})']
    if 'python' in found:
        d=found['python']; w=d/'interop_verify.py'; w.write_text('import sys,json;sys.path.insert(0,".");import verifier; r=json.load(open(sys.argv[1])); f=verifier.verify(r); print("PASS" if not f else "FAIL "+"; ".join(f)); sys.exit(1 if f else 0)')
        cmds['python']=['python3','interop_verify.py']; cleanup.append(w)
    if 'java' in found:
        d=found['java']; subprocess.run(['mvn','-q','compile','-DskipTests'],cwd=d,capture_output=True,timeout=120)
        cmds['java']=['java','-cp','target/classes','dev.aer1.AER1','verify']
    if 'csharp' in found:
        d=found['csharp']; subprocess.run(['dotnet','build','--nologo','-v','quiet'],cwd=d,capture_output=True,timeout=180,check=True)
        cmds['csharp']=['dotnet',str(d/'bin/Debug/net8.0/Aer1.dll'),'verify']
    if 'swift' in found:
        d=found['swift']; subprocess.run(['swift','build','-c','debug'],cwd=d,capture_output=True,timeout=180,check=True)
        cmds['swift']=[str(d/'.build/debug/aer1'),'verify']
    return cmds,cleanup

def emit(found):
    out={}
    for lang,d in found.items():
        if lang=='rust': cmd=['cargo','run','--quiet','--bin','emit']
        elif lang=='go': cmd=['go','run','./cmd/emit']
        elif lang=='typescript': cmd=['node','dist/emit.js']
        elif lang=='python': cmd=['python3','emitter.py']
        elif lang=='java': cmd=['java','-cp','target/classes','dev.aer1.AER1','emit']
        elif lang=='csharp': cmd=['dotnet',str(d/'bin/Debug/net8.0/Aer1.dll'),'emit']
        elif lang=='swift': cmd=[str(d/'.build/debug/aer1'),'emit']
        else: continue
        try:
            r=subprocess.run(cmd,cwd=d,capture_output=True,text=True,timeout=90,check=True);out[lang]=json.loads(r.stdout)
        except Exception as e: out[lang]={'_error':str(e)}
    return out

def fuzz_base():
    raw=b'{"inputs":{"x":1},"outputs":{"ok":true}}'; return {'id':'b6c63ac5-f324-4fa7-ad58-c4bf83faa86a','receipt_schema_version':'0.3','created_at':'2026-09-27T09:00:00.000Z','tool':{'name':'interop','version':'1.0.0','scope':'public'},'provenance_class':'EXECUTED BY INTEROP','canonical_bytes':base64.b64encode(raw).decode(),'output_hash':'sha256:'+hashlib.sha256(raw).hexdigest(),'verification_status':'verified'}
def fuzz_cases(n=200):
    rng=random.Random(41); cases=[]
    for i in range(n):
        r=fuzz_base(); typ=i%10
        if typ==0:r['output_hash']='sha256:'+'0'*64
        elif typ==1:r['id']='not-uuid'
        elif typ==2:r['created_at']='2026-02-30T00:00:00Z'
        elif typ==3:r['canonical_bytes']='!!!!'
        elif typ==4:r['canonical_bytes']=base64.b64encode(b'\xff').decode();r['output_hash']='sha256:'+hashlib.sha256(b'\xff').hexdigest()
        elif typ==5:r.pop('tool')
        elif typ==6:r['verification_status']='pending'
        elif typ==7:r['provenance_class']='unknown'
        elif typ==8:r['receipt_schema_version']='0.4'
        else:r['extra']=i
        cases.append(r)
    return cases

def verify_one(lang,cmd,cwd,path):
    argv=cmd+[str(path)] if lang!='typescript' else cmd+[str(path)]
    try:r=subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=90);return r.returncode==0
    except Exception:return False

def report_html(data,out):
    rows=[]
    for a in EXPECTED:
        cells=[]
        for b in EXPECTED:
            v=data['matrix'].get(a,{}).get(b)
            if v is None: cells.append('<td class="missing">MISSING</td>')
            else: cells.append(f'<td class="{"ok" if v else "bad"}">{"PASS" if v else "FAIL"}</td>')
        rows.append('<tr><th>'+a+'</th>'+''.join(cells)+'</tr>')
    notes=''.join(f'<li><b>{x}</b>: {html.escape(v)}</li>' for x,v in data['notes'].items())
    cmds='<pre>'+html.escape('\n'.join(data['commands']))+'</pre>'
    return '''<!doctype html><meta charset="utf-8"><title>AER-1 Interop Matrix</title><style>body{font:15px system-ui;margin:30px;background:#f5f7fb;color:#192337}main{max-width:1200px;margin:auto;background:white;padding:28px;border-radius:14px}table{border-collapse:collapse}td,th{border:1px solid #d9e0eb;padding:9px;text-align:center}th{background:#eef2f7}.ok{background:#dff6e8;color:#146c3a}.bad{background:#ffe4e1;color:#9b2118}.missing{background:#fff2cc;color:#795b00}.stat{display:inline-block;padding:12px 18px;margin:5px;border-radius:8px;background:#eef2f7}.stat strong{font-size:22px;display:block}</style><main><h1>AER-1 Cross-Language Interop</h1><p>Generated from the canonical repository checkout. Green cells are executed emitter/verifier pairs; yellow cells are languages not present in the checkout.</p><div class="stat"><strong>''' + str(data['available']) + '''/7</strong>discovered</div><div class="stat"><strong>''' + str(data['matrix_pass']) + '''/''' + str(data['matrix_total']) + '''</strong>available pairs PASS</div><div class="stat"><strong>''' + str(data['divergences']) + '''</strong>fuzz divergences</div><h2>7×7 matrix</h2><table><tr><th>Emit ↓ / Verify →</th>''' + ''.join('<th>'+x+'</th>' for x in EXPECTED) + '</tr>' + ''.join(rows) + '''</table><h2>Per-language notes</h2><ul>''' + notes + '''</ul><h2>Reproduction commands</h2>''' + cmds + '''<p><b>Important:</b> this report does not treat absent implementations as passing. The canonical checkout contains seven implementations (Rust, Go, TypeScript, Python, Java, C#, Swift); absent languages are marked missing, not passing.</p></main>'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default=str(pathlib.Path(__file__).resolve().parent.parent));ap.add_argument('--out',default='interop-report.html');a=ap.parse_args();root=pathlib.Path(a.repo).resolve();found=discover(root);tmp=pathlib.Path(tempfile.mkdtemp(prefix='aer1-interop-'));cmds,cleanup=native_setup(found,root,tmp);receipts=emit(found);matrix={}
    for emitter,r in receipts.items():
        matrix[emitter]={}
        if '_error' in r: continue
        p=tmp/(emitter+'.json');p.write_text(json.dumps(r))
        for verifier,cmd in cmds.items(): matrix[emitter][verifier]=verify_one(verifier,cmd,found[verifier],p)
    cases=fuzz_cases();div=[]
    for i,r in enumerate(cases):
        p=tmp/f'fuzz{i}.json';p.write_text(json.dumps(r));vals={v:verify_one(v,cmds[v],found[v],p) for v in cmds}
        if len(set(vals.values()))>1:div.append({'case':i,'outcomes':vals})
    data={'available':len(found),'missing':[x for x in EXPECTED if x not in found],'matrix':matrix,'matrix_pass':sum(v for row in matrix.values() for v in row.values()),'matrix_total':sum(len(row) for row in matrix.values()),'divergences':len(div),'divergence_cases':div,'notes':{x:('discovered at '+str(found[x]) if x in found else 'MISSING from canonical checkout') for x in EXPECTED},'commands':['python3 run_matrix.py --repo /path/to/zambo --out interop-report.html','git clone https://gitlab.com/rambozambodotdev/zambo.git zambo']}
    pathlib.Path(a.out).write_text(report_html(data,a.out));(pathlib.Path(a.out).with_suffix('.json')).write_text(json.dumps(data,indent=2));print(f"AVAILABLE MATRIX: {data['matrix_pass']}/{data['matrix_total']} PASS; FUZZ DIVERGENCES: {data['divergences']}; MISSING: {','.join(data['missing']) or 'none'}")
    for x in cleanup:
        if x.is_dir():shutil.rmtree(x,ignore_errors=True)
        elif x.exists():x.unlink()
    return 0
if __name__=='__main__':raise SystemExit(main())

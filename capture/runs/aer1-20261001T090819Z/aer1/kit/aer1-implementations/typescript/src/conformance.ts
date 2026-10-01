import {readdirSync,readFileSync,existsSync} from "node:fs";import {join} from "node:path";import {createHash} from "node:crypto";import {load,verify,profile,anchor,verifyWorkflow,verifyChain,verifyChainV07,merkleRoot} from "./aer1.js";const root=join(process.cwd(),"..","vectors");const idx=JSON.parse(readFileSync(join(root,"index.json"),"utf8"));let pass=0;for(const v of idx.vectors){const r=load(join(root,v.fixture));let got=verify(r).length===0;if(v.id==="missing-inputs")got=got&&profile(r);if(v.vector_group==="anchored"){const t=anchor(r);got=got&&t}if(got===v.expected_verdict){pass++;console.log("PASS",v.id)}else console.log("FAIL",v.id)}console.log(`CONFORMANCE: ${pass}/${idx.vectors.length}`);const corpusOk=pass===idx.vectors.length;
const aer1dir=[join(process.cwd(),"aer-1"),join(process.cwd(),"..","aer-1"),join(process.cwd(),"..","..","aer-1")].find(d=>existsSync(d));let chainPass=0,chainTotal=0,chainAborted=false;
try{
if(!aer1dir)throw new Error("aer-1/ vector dir not found from "+process.cwd());
const data=JSON.parse(readFileSync(join(aer1dir,"chain-vectors.json"),"utf8"));const cvs=data.vectors;
if(!Array.isArray(cvs)||cvs.length===0)throw new Error("chain vectors list is missing or empty");
for(const v of cvs){
if(v.expected_verdict!=="valid"&&v.expected_verdict!=="invalid")throw new Error("bad verdict in chain vector "+v.name);
const entries=v.entries!==undefined&&v.entries!==null?v.entries:v.timeline;
let got=false;
try{got=entries!==undefined&&entries!==null&&(verifyChain(entries).length===0)===(v.expected_verdict==="valid")}catch{got=false}
chainTotal++;if(got)chainPass++;console.log("[chain] "+(got?"PASS":"FAIL")+" "+v.name);
}
}catch(e){console.log("[chain] FAIL closed: "+(e as Error).message);chainAborted=true}
console.log("CHAIN: "+chainPass+"/"+chainTotal);const chainOk=!chainAborted&&chainTotal>0&&chainPass===chainTotal;
let v07Pass=0,v07Total=0,v07Aborted=false;
try{
if(!aer1dir)throw new Error("aer-1/ vector dir not found from "+process.cwd());
const data7=JSON.parse(readFileSync(join(aer1dir,"chain-vectors-v07.json"),"utf8"));const cvs7=data7.vectors;
if(!Array.isArray(cvs7)||cvs7.length===0)throw new Error("chain-v07 vectors list is missing or empty");
for(const v of cvs7){
if(v.expected_verdict!=="valid"&&v.expected_verdict!=="invalid")throw new Error("bad verdict in chain-v07 vector "+v.name);
const entries=v.entries!==undefined&&v.entries!==null?v.entries:v.timeline;
let got=false;
try{got=entries!==undefined&&entries!==null&&(verifyChainV07(entries).length===0)===(v.expected_verdict==="valid")}catch{got=false}
v07Total++;if(got)v07Pass++;console.log("[chain-v07] "+(got?"PASS":"FAIL")+" "+v.name);
}
}catch(e){console.log("[chain-v07] FAIL closed: "+(e as Error).message);v07Aborted=true}
console.log("CHAIN-V07: "+v07Pass+"/"+v07Total);const v07Ok=!v07Aborted&&v07Total>0&&v07Pass===v07Total;
let merklePass=0,merkleTotal=0,merkleAborted=false;
function legacyRoot(preimages:string[]):string{let level:Buffer[]=preimages.map(p=>createHash("sha256").update(p,"utf8").digest());while(level.length>1){if(level.length%2)level.push(Buffer.from(level[level.length-1]));const next:Buffer[]=[];for(let i=0;i<level.length;i+=2)next.push(createHash("sha256").update(Buffer.concat([level[i],level[i+1]])).digest());level=next}return level.length?level[0].toString("hex"):createHash("sha256").update(Buffer.alloc(0)).digest("hex")}
try{
if(!aer1dir)throw new Error("aer-1/ vector dir not found from "+process.cwd());
const mdata=JSON.parse(readFileSync(join(aer1dir,"merkle-vectors.json"),"utf8"));const mvs=mdata.vectors;
if(!Array.isArray(mvs)||mvs.length===0)throw new Error("merkle vectors list is missing or empty");
for(const v of mvs){
const name=v.name;let ok=false,detail="";
if(Array.isArray(v.receipt_ids)&&typeof v.expected_root==="string"){
const rids=v.receipt_ids as string[],root=v.expected_root as string;
if(rids.some(r=>typeof r!=="string"))throw new Error("malformed merkle vector "+name);
if(merkleRoot(rids)!==root)detail="recomputed root mismatch";
else{
const verdict=v.expected_workflow_verdict;
if(verdict===undefined||verdict===null)ok=true;
else if(verdict==="valid"||verdict==="invalid"){
const wf={steps:rids.map((r,i)=>({seq:i+1,receipt_id:r})),merkle_root:root};
const fails=verifyWorkflow(wf);const wantValid=verdict==="valid";
ok=(fails.length===0)===wantValid&&(wantValid||typeof v.rejected_by!=="string"||fails.some((x:string)=>x.includes(v.rejected_by)));
detail="verdict="+verdict+", failures="+JSON.stringify(fails);
}else throw new Error("bad verdict in merkle vector "+name);
}
}else if(Array.isArray(v.leaves)&&typeof v.expected_root==="string"){
const leg=legacyRoot(v.leaves.map((l:any)=>l.preimage));
ok=leg===v.expected_root&&leg!==v.must_not_equal;detail="legacy_root="+leg;
}else throw new Error("malformed merkle vector "+name);
merkleTotal++;if(ok)merklePass++;console.log("[merkle] "+(ok?"PASS":"FAIL")+" "+name+" ("+detail+")");
}
}catch(e){console.log("[merkle] FAIL closed: "+(e as Error).message);merkleAborted=true}
console.log("MERKLE: "+merklePass+"/"+merkleTotal);const merkleOk=!merkleAborted&&merkleTotal>0&&merklePass===merkleTotal;
if(!corpusOk||!chainOk||!v07Ok||!merkleOk)process.exit(1)

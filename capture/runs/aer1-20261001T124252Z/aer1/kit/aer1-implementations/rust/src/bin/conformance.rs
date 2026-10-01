use aer1::{load,verify,profile,anchor,verify_chain,verify_chain_v07,verify_workflow,merkle_root}; use serde_json::Value; use std::{fs,path::Path};
fn main(){
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().join("vectors");
 let idx:Value=serde_json::from_str(&fs::read_to_string(root.join("index.json")).unwrap()).unwrap();
 let mut pass=0;
 for v in idx["vectors"].as_array().unwrap(){
  let p=root.join(v["fixture"].as_str().unwrap());
  let r=load(&p);
  let expected=v["expected_verdict"].as_bool().unwrap();
  let mut got=verify(&r).is_ok();
  if v["id"].as_str().unwrap()=="missing-inputs"{got=verify(&r).is_ok()&&profile(&r).is_ok()}
  if v["vector_group"].as_str()==Some("anchored"){got=verify(&r).is_ok()&&anchor(&r).is_ok()}
  if got==expected{pass+=1;println!("PASS {}",v["id"])}else{println!("FAIL {} expected={} got={}",v["id"],expected,got)}
 }
 println!("CONFORMANCE: {pass}/{}",idx["vectors"].as_array().unwrap().len());
 let aer=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().join("aer-1");
 let (cp,ct)=gate_chain(&aer);
 let (vp,vt)=gate_chain_v07(&aer);
 let (mp,mt)=gate_merkle(&aer);
 println!("CHAIN: {cp}/{ct}");
 println!("CHAIN-V07: {vp}/{vt}");
 println!("MERKLE-VERDICT: {mp}/{mt}");
 if pass!=idx["vectors"].as_array().unwrap().len()||cp!=ct||vp!=vt||mp!=mt{std::process::exit(1)}
}
fn gate_chain(aer:&Path)->(usize,usize){
 let b=match fs::read_to_string(aer.join("chain-vectors.json")){Ok(x)=>x,Err(_)=>{println!("FAIL chain-vectors.json missing");return (0,1)}};
 let cf:Value=match serde_json::from_str(&b){Ok(x)=>x,Err(_)=>{println!("FAIL chain-vectors.json unreadable");return (0,1)}};
 let vecs=match cf["vectors"].as_array(){Some(v)if!v.is_empty()=>v,_=>{println!("FAIL chain-vectors.json empty");return (0,1)}};
 let mut pass=0;
 for v in vecs{
  let name=v["name"].as_str().unwrap_or("?");
  let verdict=v["expected_verdict"].as_str().unwrap_or("");
  if verdict!="valid"&&verdict!="invalid"{println!("FAIL chain {name} bad expected_verdict");continue}
  let tl:Vec<Value>=v["timeline"].as_array().cloned().unwrap_or_default();
  let fails=verify_chain(&tl);
  if fails.is_empty()==(verdict=="valid"){pass+=1;println!("PASS chain {name}")}else{println!("FAIL chain {name} {fails:?}")}
 }
 (pass,vecs.len())
}
fn gate_chain_v07(aer:&Path)->(usize,usize){
 let b=match fs::read_to_string(aer.join("chain-vectors-v07.json")){Ok(x)=>x,Err(_)=>{println!("FAIL chain-vectors-v07.json missing");return (0,1)}};
 let cf:Value=match serde_json::from_str(&b){Ok(x)=>x,Err(_)=>{println!("FAIL chain-vectors-v07.json unreadable");return (0,1)}};
 let vecs=match cf["vectors"].as_array(){Some(v)if!v.is_empty()=>v,_=>{println!("FAIL chain-vectors-v07.json empty");return (0,1)}};
 let mut pass=0;
 for v in vecs{
  let name=v["name"].as_str().unwrap_or("?");
  let verdict=v["expected_verdict"].as_str().unwrap_or("");
  if verdict!="valid"&&verdict!="invalid"{println!("FAIL chain-v07 {name} bad expected_verdict");continue}
  let tl:Vec<Value>=v["timeline"].as_array().cloned().unwrap_or_default();
  let fails=verify_chain_v07(&tl);
  if fails.is_empty()==(verdict=="valid"){pass+=1;println!("PASS chain-v07 {name}")}else{println!("FAIL chain-v07 {name} {fails:?}")}
 }
 (pass,vecs.len())
}
fn gate_merkle(aer:&Path)->(usize,usize){
 let b=match fs::read_to_string(aer.join("merkle-vectors.json")){Ok(x)=>x,Err(_)=>{println!("FAIL merkle-vectors.json missing");return (0,1)}};
 let mf:Value=match serde_json::from_str(&b){Ok(x)=>x,Err(_)=>{println!("FAIL merkle-vectors.json unreadable");return (0,1)}};
 let vecs=match mf["vectors"].as_array(){Some(v)if!v.is_empty()=>v,_=>{println!("FAIL merkle-vectors.json empty");return (0,1)}};
 let mut pass=0;let mut checked=0;
 for v in vecs.iter().filter(|v|v.get("expected_workflow_verdict").and_then(|x|x.as_str()).is_some()){
  let name=v["name"].as_str().unwrap_or("?");
  checked+=1;
  let verdict=v["expected_workflow_verdict"].as_str().unwrap_or("");
  if verdict!="valid"&&verdict!="invalid"{println!("FAIL merkle {name} bad expected_workflow_verdict");continue}
  let ids:Vec<&str>=v["receipt_ids"].as_array().map(|a|a.iter().filter_map(|x|x.as_str()).collect()).unwrap_or_default();
  let steps:Vec<Value>=ids.iter().enumerate().map(|(i,r)|serde_json::json!({"seq":(i+1) as u64,"receipt_id":r})).collect();
  let w=serde_json::json!({"steps":steps,"merkle_root":v["expected_root"].as_str().unwrap_or("")});
  let fails=verify_workflow(&w);
  let want=verdict=="valid";
  let mut ok=fails.is_empty()==want;
  if !want{
   let rej=v["rejected_by"].as_str().unwrap_or("");
   if !rej.is_empty()&&!fails.iter().any(|s|s.contains(rej)){ok=false}
  }
  if ok{println!("PASS merkle {name}");pass+=1}else{println!("FAIL merkle {name} {fails:?}")}
 }
 if checked==0{println!("FAIL merkle-vectors.json has no workflow-verdict vectors");return (0,1)}
 (pass,checked)
}

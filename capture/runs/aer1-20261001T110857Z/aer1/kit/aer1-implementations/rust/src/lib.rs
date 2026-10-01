use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{collections::HashSet, fs, path::Path};

const CORE: [&str;8] = ["id","receipt_schema_version","created_at","tool","provenance_class","canonical_bytes","output_hash","verification_status"];
fn s(v:&Value)->Option<&str>{v.as_str()}
fn is_uuid(x:&str)->bool { let p:[usize;5]=[8,4,4,4,12]; let a:Vec<&str>=x.split('-').collect(); a.len()==5 && a.iter().zip(p).all(|(s,n)|s.len()==n&&s.chars().all(|c|c.is_ascii_hexdigit()&&!c.is_ascii_uppercase())) }
fn is_rfc3339(x:&str)->bool {
 let b=x.as_bytes(); if b.len()<20{return false} if b[4]!=b'-'||b[7]!=b'-'||b[10]!=b'T'||b[13]!=b':'||b[16]!=b':' {return false}
 let date_ok=|i:usize,n:usize| b[i..i+n].iter().all(|c|c.is_ascii_digit()); if !date_ok(0,4)||!date_ok(5,2)||!date_ok(8,2)||!date_ok(11,2)||!date_ok(14,2)||!date_ok(17,2){return false}
 let mo:u32=x[5..7].parse().unwrap(); let day:u32=x[8..10].parse().unwrap(); let h:u32=x[11..13].parse().unwrap(); let mi:u32=x[14..16].parse().unwrap(); let sec:u32=x[17..19].parse().unwrap();
 if mo<1||mo>12||h>23||mi>59||sec>59{return false} let leap=|y:u32|y%4==0&&(y%100!=0||y%400==0); let y:u32=x[0..4].parse().unwrap(); let dm=[31,if leap(y){29}else{28},31,30,31,30,31,31,30,31,30,31]; if day<1||day>dm[(mo-1) as usize]{return false}
 let mut i=19; if i<b.len()&&b[i]==b'.'{i+=1; let st=i; while i<b.len()&&b[i].is_ascii_digit(){i+=1} if i==st{return false}}
 if i>=b.len(){return false} if b[i]==b'Z'{return i+1==b.len()} if b[i]!=b'+'&&b[i]!=b'-'{return false} i+=1; i+5==b.len()&&date_ok(i,2)&&b[i+2]==b':'&&date_ok(i+3,2)&&x[i..i+2].parse::<u32>().unwrap()<=23&&x[i+3..i+5].parse::<u32>().unwrap()<=59
}
fn b64(s:&str)->Option<Vec<u8>> { if s.len()%4!=0 || !s.chars().all(|c|c.is_ascii_alphanumeric()||c=='+'||c=='/'||c=='=') || s.matches('=').count()>2 || s.find('=').map(|i|i<s.len()-2).unwrap_or(false){return None}; let mut out=Vec::new(); let alpha=b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"; let bs=s.as_bytes(); let mut i=0; while i<bs.len(){let mut n=0u32; let mut pad=0; for j in 0..4{let c=bs[i+j] as char; if c=='='{pad+=1;n<<=6}else{n=(n<<6)|alpha.iter().position(|&x|x==bs[i+j]).unwrap_or(255) as u32}}; out.push((n>>16) as u8); if pad<2{out.push((n>>8) as u8)} if pad<1{out.push(n as u8)} i+=4} Some(out) }
fn sha(b:&[u8])->String { format!("sha256:{}",hex::encode(Sha256::digest(b))) }
fn core(r:&Value)->Vec<String>{let mut f=Vec::new(); if !r.is_object(){return vec!["receipt is not a JSON object".into()]}; for k in CORE {if r.get(k).is_none(){f.push(format!("missing required member: {k}"))}} if !f.is_empty(){return f}; if s(&r["id"]).map(|x| is_uuid(x) && x.as_bytes()[14]==b'4' && matches!(x.as_bytes()[19],b'8'|b'9'|b'a'|b'b')).unwrap_or(false)!=true{f.push("id is not a lowercase UUID".into())}; if s(&r["receipt_schema_version"]).map(|x|x=="0.3")!=Some(true){f.push("receipt_schema_version is not a non-empty string".into())}; if s(&r["created_at"]).map(is_rfc3339)!=Some(true){f.push("created_at is not RFC 3339 or valid calendar date/time".into())}; let t=&r["tool"]; if !t.is_object()||!["name","version","scope"].iter().all(|k|t.get(k).and_then(s).map(|x|!x.is_empty()).unwrap_or(false)){f.push("tool is not an object with name/version/scope strings".into())}; if s(&r["provenance_class"]).map(|x|x=="OBSERVED VIA GATEWAY"||x=="LOGGED BY AGENT"||x.strip_prefix("EXECUTED BY ").map(|y|!y.is_empty()&&y.chars().next().unwrap().is_ascii_uppercase()&&y.chars().all(|c|c.is_ascii_uppercase()||c.is_ascii_digit()||" ._-".contains(c))).unwrap_or(false))!=Some(true){f.push("provenance_class is not a known class".into())}; let raw=match s(&r["canonical_bytes"]).and_then(b64){Some(x)=>{if std::str::from_utf8(&x).is_err(){f.push("canonical_bytes is not valid UTF-8".into());None}else{Some(x)}},None=>{f.push("canonical_bytes is not valid base64".into());None}}; let oh=s(&r["output_hash"]); if oh.map(|x|x.len()==71&&x.starts_with("sha256:")&&x[7..].chars().all(|c|c.is_ascii_hexdigit()&&(!c.is_ascii_uppercase()))).unwrap_or(false)==false{f.push("output_hash is not sha256: + lowercase hex digest".into())}else if let Some(raw)=raw{if oh.unwrap()!=sha(&raw){f.push("output_hash does not match sha256(canonical_bytes)".into())}} if s(&r["verification_status"]).map(|x|x=="verified")!=Some(true){f.push("verification_status is not a non-empty string".into())} f }
pub fn verify(r:&Value)->Result<(),Vec<String>>{let f=core(r);if f.is_empty(){Ok(())}else{Err(f)}}
pub fn profile(r:&Value)->Result<(),String>{let raw=s(r.get("canonical_bytes").unwrap_or(&Value::Null)).and_then(b64).ok_or("canonical_bytes is not valid base64")?; let txt=std::str::from_utf8(&raw).map_err(|_|"canonical_bytes is not valid UTF-8")?; let p:Value=serde_json::from_str(txt).map_err(|_|"canonical payload is not JSON")?; if !p.is_object(){return Err("canonical payload is not a JSON object".into())}; if p.get("inputs").is_none(){Err("reference-producer payload omits the 'inputs' member".into())}else{Ok(())}}
pub fn anchor(r:&Value)->Result<(),String>{let a=r.get("anchor").and_then(|x|x.as_object()).ok_or("anchor is not an object")?; let keys:HashSet<_>=a.keys().map(String::as_str).collect(); if keys!=["log","leaf_hash","anchored_at","proof"].into_iter().collect(){return Err("anchor members are invalid".into())}; let raw=s(r.get("canonical_bytes").unwrap_or(&Value::Null)).and_then(b64).ok_or("canonical_bytes is not valid base64")?; if s(a.get("leaf_hash").unwrap_or(&Value::Null))!=Some(sha(&raw).as_str()){return Err("anchor.leaf_hash does not match canonical_bytes".into())}; if s(a.get("anchored_at").unwrap_or(&Value::Null)).map(is_rfc3339)!=Some(true){return Err("anchor.anchored_at is not valid RFC3339".into())}; if !a["proof"].is_object(){return Err("anchor.proof is not an object".into())}; Ok(())}
pub fn emit(id:&str,created:&str,tool:&str,version:&str,scope:&str,prov:&str,payload:&str)->Value{let raw=payload.as_bytes();serde_json::json!({"id":id,"receipt_schema_version":"0.3","created_at":created,"tool":{"name":tool,"version":version,"scope":scope},"provenance_class":prov,"canonical_bytes":base64_encode(raw),"output_hash":sha(raw),"verification_status":"verified"})}
fn base64_encode(b:&[u8])->String{let a=b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";let mut o=String::new();for c in b.chunks(3){let n=((c[0]as u32)<<16)|((*c.get(1).unwrap_or(&0)as u32)<<8)|(*c.get(2).unwrap_or(&0)as u32);o.push(a[(n>>18&63)as usize]as char);o.push(a[(n>>12&63)as usize]as char);o.push(if c.len()>1{a[(n>>6&63)as usize]as char}else{'='});o.push(if c.len()>2{a[(n&63)as usize]as char}else{'='})}o}
pub fn load(path:&Path)->Value{serde_json::from_str(&fs::read_to_string(path).unwrap()).unwrap()}
/// Section 8.1 recommended Merkle construction over ordered receipt IDs.
pub fn merkle_root(ids: &[&str]) -> String { if ids.is_empty(){return hex::encode(Sha256::digest([]));} let mut level:Vec<Vec<u8>>=ids.iter().map(|id|Sha256::digest(id.as_bytes()).to_vec()).collect(); while level.len()>1{if level.len()%2==1{level.push(level.last().unwrap().clone());} level=level.chunks(2).map(|p|{let mut b=Vec::with_capacity(64);b.extend(&p[0]);b.extend(&p[1]);Sha256::digest(&b).to_vec()}).collect();} hex::encode(&level[0]) }
/// verify_workflow validates the Section 8.1 workflow: input is an object,
/// steps is a non-empty list, each step has integer seq and string receipt_id,
/// seq runs exactly 1..n in order (no gaps, no duplicate seq), no two steps
/// share a receipt_id, and merkle_root equals the recomputed Section 8.1 root
/// over the ordered receipt_id strings. Section 8.2 steps 1-2 need network and
/// stay the caller's job; this checks structure and math only.
pub fn verify_workflow(w:&Value)->Vec<String>{let mut f=Vec::new();if !w.is_object(){return vec!["workflow is not a JSON object".into()]}let steps=match w.get("steps").and_then(|x|x.as_array()){Some(s)if!s.is_empty()=>s,_=>return vec!["steps is not a non-empty list".into()]};let mut ids:Vec<&str>=Vec::with_capacity(steps.len());let mut seen=HashSet::new();for(i,st)in steps.iter().enumerate(){let step=match st.as_object(){Some(x)=>x,None=>{f.push(format!("step {i} is not an object"));continue}};if step.get("seq").and_then(|v|v.as_u64())!=Some(i as u64+1){f.push(format!("step {i} seq is not {}",i+1))}match step.get("receipt_id").and_then(|v|v.as_str()){Some(r)if!r.is_empty()=>{if!seen.insert(r){f.push(format!("duplicate receipt_id: {r}"))}ids.push(r)},_=>f.push(format!("step {i} receipt_id is not a non-empty string"))}};match w.get("merkle_root").and_then(|v|v.as_str()){Some(root)=>{let got=merkle_root(&ids);if got!=root{f.push(format!("merkle_root does not match recomputed Section 8.1 root {got}"))}},None=>f.push("merkle_root is missing or not a string".into())}f}
/// verify_chain validates the pinned Section 7 hash chain and nothing else.
/// Entry digest = SHA-256 over the raw bytes of base64-decoded canonical_bytes
/// (strict decode, fail closed). Entry 0 prev_digest must be exactly 64 zeros.
/// Every later entry's prev_digest must equal the lowercase hex digest of the
/// previous entry. The last entry must carry close: true (boolean). An empty
/// timeline fails. Fetching or verifying the referenced receipts stays the
/// caller's job; this covers chain mechanics only.
pub fn verify_chain(tl:&[Value])->Vec<String>{let mut f=Vec::new();if tl.is_empty(){return vec!["timeline is empty".into()]}let mut digests:Vec<String>=Vec::with_capacity(tl.len());for(i,e)in tl.iter().enumerate(){let entry=match e.as_object(){Some(x)=>x,None=>{f.push(format!("entry {i} is not an object"));return f}};let raw=match entry.get("canonical_bytes").and_then(|v|v.as_str()).and_then(b64){Some(x)=>x,None=>{f.push(format!("entry {i} canonical_bytes is not valid base64"));return f}};digests.push(hex::encode(Sha256::digest(&raw)));match entry.get("prev_digest").and_then(|v|v.as_str()){None=>{f.push(format!("entry {i} prev_digest is missing or not a string"));return f},Some(pd)=>{if i==0{if pd!="0".repeat(64){f.push("entry 0 prev_digest is not 64 zeros".into())}}else if pd!=digests[i-1]{f.push(format!("entry {i} prev_digest does not match digest of entry {}",i-1))}}}}let last=tl.last().unwrap().as_object().unwrap();if last.get("close")!=Some(&Value::Bool(true)){f.push("last entry close is not true".into())}f}
/// ascii_json_v07 re-escapes any non-ASCII characters in serializer output
/// as \uXXXX (surrogate pairs for astral characters), matching the Python
/// reference's ensure_ascii canonical form so digests agree byte for byte.
fn ascii_json_v07(s:&str)->String{let mut o=String::with_capacity(s.len());for c in s.chars(){let n=c as u32;if n<0x80{o.push(c)}else if n<0x10000{o.push_str(&format!("\\u{:04x}",n))}else{let v=n-0x10000;o.push_str(&format!("\\u{:04x}\\u{:04x}",0xd800+(v>>10),0xdc00+(v&0x3ff)))}}o}
/// chain_entry_digest_v07 computes the -07 hardened entry digest: SHA-256
/// over the UTF-8 bytes of the canonical JSON object {prev_digest, seq,
/// job_id, close, id, tool, provenance_class, output_hash} with keys sorted
/// (serde_json::Map is a BTreeMap) and no whitespace, where output_hash =
/// lowercase hex SHA-256 of the base64-decoded canonical_bytes. A missing
/// close member digests as false. Returns None on bad base64 (fail closed).
/// seq_int extracts an integer-valued seq as u64. Accepts JSON integers and
/// integer-valued floats (1 and 1.0 are equivalent); rejects booleans,
/// strings, null, and non-integer floats. None = not an integer.
fn seq_int(v:&Value)->Option<u64>{match v{Value::Number(n)if n.is_u64()=>n.as_u64(),Value::Number(n)if n.is_i64()&&n.as_i64().unwrap()>=0=>Some(n.as_i64().unwrap()as u64),Value::Number(n)=>{let f=n.as_f64()?;if f.fract()!=0.0||f<0.0||f>9007199254740991.0{None}else{Some(f as u64)}},_=>None}}
pub fn chain_entry_digest_v07(e:&serde_json::Map<String,Value>)->Option<String>{
 let raw=b64(e.get("canonical_bytes")?.as_str()?)?;
 let oh=hex::encode(Sha256::digest(&raw));
 let mut m=serde_json::Map::new();
 m.insert("prev_digest".into(),Value::String(e.get("prev_digest")?.as_str()?.into()));
 m.insert("seq".into(),match seq_int(e.get("seq")?){Some(v)=>Value::Number(v.into()),None=>e.get("seq")?.clone()});
 m.insert("job_id".into(),Value::String(e.get("job_id")?.as_str()?.into()));
 m.insert("close".into(),e.get("close").cloned().unwrap_or(Value::Bool(false)));
 m.insert("id".into(),Value::String(e.get("id")?.as_str()?.into()));
 m.insert("tool".into(),Value::String(e.get("tool")?.as_str()?.into()));
 m.insert("provenance_class".into(),Value::String(e.get("provenance_class")?.as_str()?.into()));
 m.insert("output_hash".into(),Value::String(oh));
 let blob=ascii_json_v07(&serde_json::to_string(&Value::Object(m)).ok()?);
 Some(hex::encode(Sha256::digest(blob.as_bytes())))}
/// verify_chain_v07 validates the -07 hardened Section 7 hash-chain
/// construction and nothing else. The entry digest binds prev_digest, seq,
/// job_id, close, id, tool, provenance_class, and output_hash. Entry 0's
/// prev_digest must be exactly 64 zeros and seq must be 1; seq must be
/// contiguous from 1; every entry must carry the same job_id; close must be
/// a boolean and true only on the last entry; each entry's prev_digest must
/// equal the recomputed digest of the previous entry; canonical_bytes must
/// be strict-valid base64 (fail closed). Honest limit: truncation with
/// re-linking is not detectable by chain mechanics alone; it needs an
/// anchored endpoint.
pub fn verify_chain_v07(tl:&[Value])->Vec<String>{let mut f=Vec::new();if tl.is_empty(){return vec!["timeline is empty".into()]}let mut job:Option<&str>=None;let mut prev=String::new();for(i,e)in tl.iter().enumerate(){let entry=match e.as_object(){Some(x)=>x,None=>return vec![format!("entry {i} is not an object")]};if entry.get("canonical_bytes").and_then(|v|v.as_str()).and_then(b64).is_none(){return vec![format!("entry {i} canonical_bytes is not valid base64")]}for m in ["id","tool","provenance_class","job_id","prev_digest"]{if entry.get(m).and_then(|v|v.as_str()).map(|s|!s.is_empty())!=Some(true){return vec![format!("entry {i} missing {m}")]}}let seq=match entry.get("seq").and_then(seq_int){Some(v)=>v,_=>return vec![format!("entry {i} seq is not an integer")]};if seq!=i as u64+1{f.push(format!("entry {i} seq {seq} breaks contiguity (expected {})",i+1))}let j=entry["job_id"].as_str().unwrap();if job.is_none(){job=Some(j)}else if job!=Some(j){f.push(format!("entry {i} job_id mixes jobs"))}let pd=entry["prev_digest"].as_str().unwrap();if i==0{if pd!="0".repeat(64){f.push("entry 0 prev_digest is not 64 zeros".into())}}else if pd!=prev{f.push(format!("entry {i} prev_digest does not match digest of entry {}",i-1))}match entry.get("close"){Some(Value::Bool(c))=>{if *c&&i<tl.len()-1{f.push(format!("entry {i} carries close:true before the last entry"))}},Some(_)=>f.push(format!("entry {i} close is not a boolean")),None=>{}}let d=match chain_entry_digest_v07(entry){Some(x)=>x,None=>return vec![format!("entry {i} canonical_bytes is not valid base64")]};prev=d}let last=tl.last().unwrap().as_object().unwrap();if last.get("close")!=Some(&Value::Bool(true)){f.push("last entry does not carry close: true".into())}f}
#[cfg(test)]mod tests{use super::*;use serde_json::json;
fn wf(ids:&[&str],root:&str)->Value{let steps:Vec<Value>=ids.iter().enumerate().map(|(i,r)|json!({"seq":(i+1)as u64,"receipt_id":r})).collect();json!({"steps":steps,"merkle_root":root})}
#[test]fn workflow_valid(){let ids=["r1","r2","r3"];assert!(verify_workflow(&wf(&ids,&merkle_root(&ids))).is_empty())}
#[test]fn workflow_duplicate(){let ids=["r1","r1"];let f=verify_workflow(&wf(&ids,&merkle_root(&ids)));assert!(!f.is_empty()&&f.iter().any(|s|s.contains("duplicate receipt_id")))}
#[test]fn workflow_seq_gap(){let w=json!({"steps":[{"seq":1,"receipt_id":"r1"},{"seq":3,"receipt_id":"r2"}],"merkle_root":merkle_root(&["r1","r2"])});assert!(!verify_workflow(&w).is_empty())}
#[test]fn workflow_root_mismatch(){let w=wf(&["r1","r2"],"0000000000000000000000000000000000000000000000000000000000000000");assert!(verify_workflow(&w).iter().any(|s|s.contains("merkle_root")))}
#[test]fn workflow_empty_steps(){assert!(!verify_workflow(&json!({"steps":[],"merkle_root":"x"})).is_empty())}
fn chain_entry(prev:&str,close:Option<bool>)->Value{let mut e=json!({"canonical_bytes":super::base64_encode(b"payload"),"prev_digest":prev});if let Some(c)=close{e["close"]=json!(c)}e}
#[test]fn chain_valid(){let d0=hex::encode(Sha256::digest(b"payload"));let z="0".repeat(64);let tl=vec![chain_entry(&z,None),chain_entry(&d0,Some(true))];assert!(verify_chain(&tl).is_empty())}
#[test]fn chain_bad_genesis(){let tl=vec![chain_entry("0000000000000000000000000000000000000000000000000000000000000001",Some(true))];assert!(verify_chain(&tl).iter().any(|s|s.contains("64 zeros")))}
#[test]fn chain_broken_link(){let z="0".repeat(64);let tl=vec![chain_entry(&z,None),chain_entry(&z,Some(true))];assert!(verify_chain(&tl).iter().any(|s|s.contains("prev_digest does not match")))}
#[test]fn chain_missing_close(){let z="0".repeat(64);let tl=vec![chain_entry(&z,None),chain_entry(&hex::encode(Sha256::digest(b"payload")),None)];assert!(verify_chain(&tl).iter().any(|s|s.contains("close is not true")))}
#[test]fn chain_empty(){assert!(verify_chain(&[]).iter().any(|s|s.contains("empty")))}
}

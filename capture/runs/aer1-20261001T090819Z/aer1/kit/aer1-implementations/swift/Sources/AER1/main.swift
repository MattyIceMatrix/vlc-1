#if os(Linux)
import Glibc
#endif
import Foundation

let core=["id","receipt_schema_version","created_at","tool","provenance_class","canonical_bytes","output_hash","verification_status"]
let uuid=try! NSRegularExpression(pattern:"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
let rfc=try! NSRegularExpression(pattern:"^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2}):(\\d{2})(?:\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$")
func match(_ re:NSRegularExpression,_ s:String)->NSTextCheckingResult?{re.firstMatch(in:s,range:NSRange(s.startIndex...,in:s))}
func timestamp(_ x:Any?)->Bool { guard let s=x as? String, let m=match(rfc,s) else{return false}; func g(_ n:Int)->Int{Int((s as NSString).substring(with:m.range(at:n)))!}; let y=g(1),mo=g(2),d=g(3),h=g(4),mi=g(5),se=g(6); let leap=y%4==0 && (y%100 != 0 || y%400 == 0); let monthDays=[31,leap ? 29 : 28,31,30,31,30,31,31,30,31,30,31]; guard y>=1 && mo>=1 && mo<=12 && d>=1 && d<=monthDays[mo-1] && h<=23 && mi<=59 && se<=59 else{return false}; let z=(s as NSString).substring(with:m.range(at:7)); if z=="Z"{return true}; return Int(z[z.index(z.startIndex,offsetBy:1)..<z.index(z.startIndex,offsetBy:3)])!<=23 && Int(z[z.index(z.startIndex,offsetBy:4)..<z.endIndex])!<=59 }
func b64(_ x:Any?)->Data?{guard let s=x as? String,s.count%4==0,s.range(of:"^[A-Za-z0-9+/]*={0,2}$",options:.regularExpression) != nil,let d=Data(base64Encoded:s),d.base64EncodedString()==s,String(data:d,encoding:.utf8) != nil else{return nil};return d}
struct SHA256 { static let k:[UInt32]=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
 static func hash(_ input:Data)->[UInt8]{var data=Array(input);let bit=UInt64(data.count)*8;data.append(0x80);while data.count%64 != 56{data.append(0)};for i in stride(from:7,through:0,by:-1){data.append(UInt8((bit>>UInt64(i*8))&255))};var h:[UInt32]=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];func rotr(_ x:UInt32,_ n:UInt32)->UInt32{(x>>n)|(x<<(32-n))};for chunk in stride(from:0,to:data.count,by:64){var w=[UInt32](repeating:0,count:64);for i in 0..<16{let j=chunk+i*4;w[i]=UInt32(data[j])<<24|UInt32(data[j+1])<<16|UInt32(data[j+2])<<8|UInt32(data[j+3])};for i in 16..<64{let x=rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3),y=rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]&+x&+w[i-7]&+y};var(a,b,c,d,e,f,g,hh)=(h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7]);for n in 0..<64{let s1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^((~e)&g),t1=hh&+s1&+ch&+k[n]&+w[n],s0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&c)^(b&c),t2=s0&+maj;hh=g;g=f;f=e;e=d&+t1;d=c;c=b;b=a;a=t1&+t2};h[0]&+=a;h[1]&+=b;h[2]&+=c;h[3]&+=d;h[4]&+=e;h[5]&+=f;h[6]&+=g;h[7]&+=hh};return h.flatMap{[UInt8(($0>>24)&255),UInt8(($0>>16)&255),UInt8(($0>>8)&255),UInt8($0&255)]}}
 static func dummyAdd(b:UInt32,a:UInt32)->UInt32{b&+a}
}
func hex(_ b:[UInt8])->String{b.map{String(format:"%02x",$0)}.joined()};func sha(_ d:Data)->String{"sha256:"+hex(SHA256.hash(d))}
func verify(_ r:[String:Any])->[String]{ var f:[String]=[]; for k in core{if r[k] == nil{f.append("missing required member: "+k)}}; if !f.isEmpty{return f}; if let id=r["id"] as? String {if match(uuid,id)==nil{f.append("id is not a lowercase UUID v4")}} else {f.append("id is not a lowercase UUID v4")}; if (r["receipt_schema_version"] as? String) != "0.3"{f.append("receipt_schema_version is not 0.3")}; if !timestamp(r["created_at"]){f.append("created_at is not a valid RFC 3339 timestamp")}; if let t=r["tool"] as? [String:Any]{for k in ["name","version","scope"]{if !((t[k] as? String)?.isEmpty == false){f.append("tool is not an object with name/version/scope strings")}}} else {f.append("tool is not an object with name/version/scope strings")}; let p=r["provenance_class"] as? String; if !(p=="OBSERVED VIA GATEWAY" || p=="LOGGED BY AGENT" || (p?.range(of:"^EXECUTED BY [A-Z0-9][A-Z0-9 ._-]*$",options:.regularExpression) != nil)){f.append("provenance_class is not a known class")}; let raw=b64(r["canonical_bytes"]); if raw == nil{f.append("canonical_bytes is not valid base64 or UTF-8")}; if let oh=r["output_hash"] as? String {if oh.range(of:"^sha256:[0-9a-f]{64}$",options:.regularExpression) == nil{f.append("output_hash is not sha256: plus lowercase hex")} else if let raw=raw,oh != sha(raw){f.append("hash mismatch")}} else {f.append("output_hash is not sha256: plus lowercase hex")}; if (r["verification_status"] as? String) != "verified"{f.append("verification_status is not verified")}; return f }
func profile(_ r:[String:Any])->Bool{guard let d=b64(r["canonical_bytes"]),let p=try? JSONSerialization.jsonObject(with:d) as? [String:Any] else{return false};return p["inputs"] != nil}
func anchor(_ r:[String:Any])->Bool{guard let a=r["anchor"] as? [String:Any],Set(a.keys)==Set(["log","leaf_hash","anchored_at","proof"]),let d=b64(r["canonical_bytes"]),a["leaf_hash"] as? String == sha(d),timestamp(a["anchored_at"]),a["proof"] is [String:Any] else{return false};return true}
func merkleRoot(_ ids:[String])->String{var level=ids.map{Data(SHA256.hash(Data($0.utf8)))};if level.isEmpty{return hex(SHA256.hash(Data()))};while level.count>1{if level.count%2==1{level.append(level.last!)};var next:[Data]=[];for i in stride(from:0,to:level.count,by:2){next.append(Data(SHA256.hash(level[i]+level[i+1])))};level=next};return hex(Array(level[0]))}
func jsonBool(_ x:Any?)->Bool?{guard let v=x else{return nil};switch String(describing:type(of:v)){case "__NSCFBoolean":return (v as! NSNumber).boolValue;case "Bool":return v as? Bool;default:return nil}}
func isInt(_ x:Any?)->Bool{guard let v=x,jsonBool(v)==nil else{return false};guard let n=v as? NSNumber else{return false};let c=n.objCType[0];if c==100||c==102{let d=n.doubleValue;return d==floor(d)&&d>=0&&d<=9007199254740991};return true}
func intVal(_ x:Any?)->Int{(x as? NSNumber)?.intValue ?? 0}
func b64strict(_ x:Any?)->Data?{guard let s=x as? String,s.count%4==0,s.range(of:"^[A-Za-z0-9+/]*={0,2}$",options:.regularExpression) != nil,let d=Data(base64Encoded:s) else{return nil};return d}
func verifyWorkflow(_ w:Any?)->[String]{
// Section 8.2 steps 3-4: offline workflow verification. Returns failure
// strings; empty means valid. NOTE: Section 8.2 steps 1-2 (fetch each step's
// receipt over the network and confirm each receipt exists and is addressed)
// need network access and STAY THE CALLER'S JOB.
guard let m=w as? [String:Any] else{return ["workflow is not a JSON object"]}
guard let steps=m["steps"] as? [Any],!steps.isEmpty else{return ["steps is not a non-empty list"]}
let n=steps.count;var f:[String]=[];var seqs:[Any?]=[];var ids:[Any?]=[]
for i in 0..<n{guard let s=steps[i] as? [String:Any] else{f.append("step \(i) is not an object");seqs.append(nil);ids.append(nil);continue}
let q=s["seq"],rid=s["receipt_id"];if !isInt(q){f.append("step \(i) seq is not an integer")};if !(rid is String){f.append("step \(i) receipt_id is not a string")};seqs.append(q);ids.append(rid)}
if seqs.allSatisfy({isInt($0)}){for i in 0..<n{if intVal(seqs[i]) != i+1{f.append("seq values are not exactly 1..n in order: gap, duplicate, or out of order");break}}}
let idsOk=ids.allSatisfy({$0 is String})
if idsOk{var seen=Set<String>();for r in ids{let s=r as! String;if !seen.insert(s).inserted{f.append("8.2 duplicate receipt_id: "+s);break}}}
if let mr=m["merkle_root"] as? String{if idsOk{let want=merkleRoot(ids.map{$0 as! String});if mr != want{f.append("merkle_root mismatch: expected "+want+", got "+mr)}}}else{f.append("merkle_root is not a string")}
return f}
func verifyChain(_ t:Any?)->[String]{
// Pinned Section 7 chain construction: entry digest = SHA-256 over the raw
// bytes of base64-decoded canonical_bytes (strict decode, fail closed);
// entry 0 prev_digest must be exactly 64 zeros; each later entry's
// prev_digest must equal the lowercase hex digest of the previous entry;
// the last entry must carry close set to boolean true. Chain mechanics
// only: full receipt validation stays the caller's job, not this function.
guard let tl=t as? [Any],!tl.isEmpty else{return ["timeline is not a non-empty list"]}
var f:[String]=[];var prev:String?=nil
for i in 0..<tl.count{guard let e=tl[i] as? [String:Any] else{f.append("entry \(i) is not an object");prev=nil;continue}
let pd=e["prev_digest"]
if i==0{if (pd as? String) != String(repeating:"0",count:64){f.append("entry 0 prev_digest is not 64 zeros")}}
else if !(pd is String){f.append("entry \(i) prev_digest is not a string")}
else if (pd as! String) != prev{f.append("entry \(i) prev_digest does not match digest of entry \(i-1)")}
if let raw=b64strict(e["canonical_bytes"]){prev=hex(SHA256.hash(raw))}else{f.append("entry \(i) canonical_bytes is not valid base64");prev=nil}}
if let last=tl.last as? [String:Any]{if jsonBool(last["close"]) != true{f.append("last entry close is not boolean true")}}else{f.append("last entry close is not boolean true")}
return f}
func asciiJsonV07(_ s:String)->String{
// Re-escape non-ASCII as \uXXXX (surrogate pairs for astral), matching the
// Python reference's ensure_ascii canonical form so digests agree byte for byte.
var o="";o.reserveCapacity(s.count);for sc in s.unicodeScalars{let n=sc.value;if n<0x80{o.append(Character(sc))}else if n<0x10000{o.append(String(format:"\\u%04x",n))}else{let v=n-0x10000;o.append(String(format:"\\u%04x\\u%04x",0xd800+(v>>10),0xdc00+(v&0x3ff)))}};return o}
func chainEntryDigestV07(_ e:[String:Any])->String?{
// -07 hardened entry digest: SHA-256 over the UTF-8 bytes of the canonical
// JSON object {prev_digest, seq, job_id, close, id, tool, provenance_class,
// output_hash} (keys sorted, no whitespace), where output_hash = lowercase
// hex SHA-256 of the base64-decoded canonical_bytes. A missing close member
// digests as false.
guard let cb=e["canonical_bytes"] as? String,let raw=b64strict(cb),
 let id=e["id"] as? String,let job=e["job_id"] as? String,
 let pd=e["prev_digest"] as? String,let pc=e["provenance_class"] as? String,
 let tool=e["tool"] as? String,isInt(e["seq"]) else{return nil}
let oh=hex(SHA256.hash(raw))
let closeVal:Any=e.keys.contains("close") ? (e["close"] ?? false) : false
let payload:[String:Any]=["close":closeVal,"id":id,"job_id":job,"output_hash":oh,"prev_digest":pd,"provenance_class":pc,"seq":intVal(e["seq"]),"tool":tool]
guard let rawBlob=try? JSONSerialization.data(withJSONObject:payload,options:[.sortedKeys]),let rawStr=String(data:rawBlob,encoding:.utf8) else{return nil}
let blob=Data(asciiJsonV07(rawStr).utf8)
return hex(SHA256.hash(blob))}
func verifyChainV07(_ t:Any?)->[String]{
// -07 hardened chain mechanics. The entry digest binds prev_digest, seq,
// job_id, close, id, tool, provenance_class, and output_hash. Genesis = 64
// zeros, seq contiguous from 1, one job_id per chain, close boolean true only
// on the last entry, links match recomputed digests, strict base64 fail
// closed. Honest limit: truncation with re-linking needs an anchored endpoint.
guard let tl=t as? [Any],!tl.isEmpty else{return ["timeline is not a non-empty list"]}
var f:[String]=[];var job:String?=nil;var prev:String?=nil
for i in 0..<tl.count{guard let e=tl[i] as? [String:Any] else{return ["entry \(i) is not an object"]}
if b64strict(e["canonical_bytes"])==nil{return ["entry \(i) canonical_bytes is not valid base64"]}
for k in ["id","tool","provenance_class","job_id","prev_digest"]{if (e[k] as? String)?.isEmpty != false{return ["entry \(i) missing "+k]}}
guard isInt(e["seq"]) else{return ["entry \(i) seq is not an integer"]}
let seq=intVal(e["seq"]);if seq != i+1{f.append("entry \(i) seq \(seq) breaks contiguity (expected \(i+1))")}
let j=e["job_id"] as! String;if i==0{job=j}else if j != job{f.append("entry \(i) job_id mixes jobs")}
let pd=e["prev_digest"] as! String
if i==0{if pd != String(repeating:"0",count:64){f.append("entry 0 prev_digest is not 64 zeros")}}
else if pd != prev{f.append("entry \(i) prev_digest does not match digest of entry \(i-1)")}
if e.keys.contains("close"){if jsonBool(e["close"])==nil{f.append("entry \(i) close is not a boolean")}else if i<tl.count-1&&jsonBool(e["close"])==true{f.append("entry \(i) carries close:true before the last entry")}}
guard let d=chainEntryDigestV07(e) else{return ["entry \(i) canonical_bytes is not valid base64"]};prev=d}
if let last=tl.last as? [String:Any]{if jsonBool(last["close"]) != true{f.append("last entry does not carry close: true")}}else{f.append("last entry does not carry close: true")}
return f}
func emit()->[String:Any]{let raw=Data("{\"inputs\":{\"x\":1},\"outputs\":{\"ok\":true}}".utf8);return ["id":"b6c63ac5-f324-4fa7-ad58-c4bf83faa86a","receipt_schema_version":"0.3","created_at":"2026-09-27T09:00:00Z","tool":["name":"demo_tool","version":"1.0.0","scope":"public"],"provenance_class":"EXECUTED BY SWIFT","canonical_bytes":raw.base64EncodedString(),"output_hash":sha(raw),"verification_status":"verified"]}
func findVectors()->URL{let cwd=URL(fileURLWithPath:FileManager.default.currentDirectoryPath);let candidates=[cwd.appendingPathComponent("vectors"),cwd.appendingPathComponent("../vectors"),cwd.appendingPathComponent("../../vectors"),cwd.appendingPathComponent("aer1-implementations/vectors"),cwd.appendingPathComponent("../aer1-implementations/vectors")];for p in candidates where FileManager.default.fileExists(atPath:p.appendingPathComponent("index.json").path){return p.standardizedFileURL};fatalError("AER-1 vectors/index.json not found from "+cwd.path)}
func findAer1()->URL?{if let env=ProcessInfo.processInfo.environment["AER1_DIR"],!env.isEmpty{let u=URL(fileURLWithPath:env);var isDir:ObjCBool=false;if FileManager.default.fileExists(atPath:u.path,isDirectory:&isDir),isDir.boolValue{return u.standardizedFileURL}};let cwd=URL(fileURLWithPath:FileManager.default.currentDirectoryPath);for rel in ["aer-1","../aer-1","../../aer-1"]{let u=cwd.appendingPathComponent(rel).standardizedFileURL;var isDir:ObjCBool=false;if FileManager.default.fileExists(atPath:u.path,isDirectory:&isDir),isDir.boolValue{return u}};return nil}
let root=findVectors();let mode=CommandLine.arguments.dropFirst().first;if mode=="emit"{print(String(data:try! JSONSerialization.data(withJSONObject:emit()),encoding:.utf8)!);exit(0)};if mode=="verify"{let path=CommandLine.arguments.dropFirst().dropFirst().first ?? "-";let data=path=="-" ? FileHandle.standardInput.readDataToEndOfFile() : (try! Data(contentsOf:URL(fileURLWithPath:path)));let r=try! JSONSerialization.jsonObject(with:data) as! [String:Any];let f=verify(r);if f.isEmpty{print("PASS")}else{print("FAIL "+f.joined(separator:"; "));exit(1)};exit(0)};let idx=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("index.json"))) as! [String:Any];let vs=idx["vectors"] as! [[String:Any]];var pass=0;for v in vs{let r=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(v["fixture"] as! String))) as! [String:Any];var got=verify(r).isEmpty;if v["id"] as? String=="missing-inputs"{got=got&&profile(r)};if v["vector_group"] as? String=="anchored"{got=got&&anchor(r)};let expected=v["expected_verdict"] as! Bool;if got==expected{pass+=1;print("PASS",v["id"]!)}else{print("FAIL",v["id"]!)} };print("CONFORMANCE: \(pass)/\(vs.count)");let corpusOk=pass==vs.count
var chainTotal=0,chainPass=0;let aer1=findAer1()
if aer1==nil{print("[chain] FAIL closed: aer-1 dir not found, chain-vectors.json unreachable")}
else{do{let p=aer1!.appendingPathComponent("chain-vectors.json");guard FileManager.default.fileExists(atPath:p.path) else{throw NSError(domain:"aer1",code:1,userInfo:[NSLocalizedDescriptionKey:"aer-1/chain-vectors.json is missing (no silent pass)"])};let c=try JSONSerialization.jsonObject(with:Data(contentsOf:p)) as! [String:Any];guard let cvs=c["vectors"] as? [Any],!cvs.isEmpty else{throw NSError(domain:"aer1",code:2,userInfo:[NSLocalizedDescriptionKey:"chain vectors list is missing or empty"])};for x in cvs{guard let v=x as? [String:Any] else{throw NSError(domain:"aer1",code:5,userInfo:[NSLocalizedDescriptionKey:"chain vector is not an object"])};let name=v["name"] as? String ?? "?";let ev=v["expected_verdict"] as? String;guard ev=="valid"||ev=="invalid" else{throw NSError(domain:"aer1",code:3,userInfo:[NSLocalizedDescriptionKey:"bad verdict in chain vector "+name])};let te=v["entries"];let tl=(te==nil||te is NSNull) ? v["timeline"] : te;let ff=verifyChain(tl);let got=ff.isEmpty==(ev=="valid");chainTotal+=1;if got{chainPass+=1;print("[chain] PASS",name)}else{print("[chain] FAIL",name,ff.isEmpty ? "" : "("+ff.joined(separator:"; ")+")")}} }catch{print("[chain] FAIL closed:",(error as NSError).localizedDescription)}}
print("CHAIN: \(chainPass)/\(chainTotal)");let chainOk=chainTotal>0&&chainPass==chainTotal
var chainV07Total=0,chainV07Pass=0
if aer1==nil{print("[chain-v07] FAIL closed: aer-1 dir not found, chain-vectors-v07.json unreachable")}
else{do{let p=aer1!.appendingPathComponent("chain-vectors-v07.json");guard FileManager.default.fileExists(atPath:p.path) else{throw NSError(domain:"aer1",code:1,userInfo:[NSLocalizedDescriptionKey:"aer-1/chain-vectors-v07.json is missing (no silent pass)"])};let c=try JSONSerialization.jsonObject(with:Data(contentsOf:p)) as! [String:Any];guard let cvs=c["vectors"] as? [Any],!cvs.isEmpty else{throw NSError(domain:"aer1",code:2,userInfo:[NSLocalizedDescriptionKey:"chain-v07 vectors list is missing or empty"])};for x in cvs{guard let v=x as? [String:Any] else{throw NSError(domain:"aer1",code:5,userInfo:[NSLocalizedDescriptionKey:"chain-v07 vector is not an object"])};let name=v["name"] as? String ?? "?";let ev=v["expected_verdict"] as? String;guard ev=="valid"||ev=="invalid" else{throw NSError(domain:"aer1",code:3,userInfo:[NSLocalizedDescriptionKey:"bad verdict in chain-v07 vector "+name])};let te=v["entries"];let tl=(te==nil||te is NSNull) ? v["timeline"] : te;let ff=verifyChainV07(tl);let got=ff.isEmpty==(ev=="valid");chainV07Total+=1;if got{chainV07Pass+=1;print("[chain-v07] PASS",name)}else{print("[chain-v07] FAIL",name,ff.isEmpty ? "" : "("+ff.joined(separator:"; ")+")")}} }catch{print("[chain-v07] FAIL closed:",(error as NSError).localizedDescription)}}
print("CHAIN-V07: \(chainV07Pass)/\(chainV07Total)");let chainV07Ok=chainV07Total>0&&chainV07Pass==chainV07Total
var merkleOk=false;var merkleCount="0/0"
if aer1==nil{print("[merkle] FAIL closed: aer-1 dir not found, merkle-vectors.json unreachable")}
else{do{let p=aer1!.appendingPathComponent("merkle-vectors.json");guard FileManager.default.fileExists(atPath:p.path) else{throw NSError(domain:"aer1",code:1,userInfo:[NSLocalizedDescriptionKey:"aer-1/merkle-vectors.json is missing (no silent pass)"])};let c=try JSONSerialization.jsonObject(with:Data(contentsOf:p)) as! [String:Any];guard let mvs=c["vectors"] as? [Any],!mvs.isEmpty else{throw NSError(domain:"aer1",code:2,userInfo:[NSLocalizedDescriptionKey:"merkle vectors list is missing or empty"])};guard let dicts=mvs as? [[String:Any]] else{throw NSError(domain:"aer1",code:3,userInfo:[NSLocalizedDescriptionKey:"merkle vectors malformed"])};var mPass=0,mTot=0;for vv in dicts{guard let vf=vv["expected_workflow_verdict"] as? String else{continue};let name=vv["name"] as? String ?? "?";mTot+=1;guard let rids=vv["receipt_ids"] as? [Any],!rids.isEmpty,let rt=vv["expected_root"] as? String,(vf=="valid"||vf=="invalid") else{print("[merkle] FAIL",name,"(malformed vector)");continue};let rb=vv["rejected_by"] as? String ?? "";var steps:[[String:Any]]=[];for (i,r) in rids.enumerated(){steps.append(["seq":i+1,"receipt_id":r])};let wf:[String:Any]=["steps":steps,"merkle_root":rt];let ff=verifyWorkflow(wf);let want=vf=="valid";let ok=ff.isEmpty==want&&(want||rb.isEmpty||ff.contains(where:{$0.contains(rb)}));print("[merkle]",ok ? "PASS" : "FAIL",name,"(verdict=\(vf), failures=\(ff))");if ok{mPass+=1}};guard mTot>0 else{throw NSError(domain:"aer1",code:4,userInfo:[NSLocalizedDescriptionKey:"no workflow-verdict vectors found"])};merkleOk=mPass==mTot;merkleCount="\(mPass)/\(mTot)"}catch{print("[merkle] FAIL closed:",(error as NSError).localizedDescription)}}
print("MERKLE:",merkleCount)
if !(corpusOk&&chainOk&&chainV07Ok&&merkleOk){exit(1)}

const fs=require('fs');
function receipt(x){return typeof x==='string'?JSON.parse(x):{...x}}
function wrap(x){const r=receipt(x),name=(r.tool||{}).name||'unknown';return {specversion:'1.0',id:r.id,source:'/tools/'+name,type:'dev.zambo.aer1.receipt.v1',time:r.created_at,datacontenttype:'application/json',data:r,aer1provenance:r.provenance_class,aer1schemaversion:r.receipt_schema_version||'0.3'}}
function unwrap(x){let ce=receipt(x);if(ce.detail&&typeof ce.detail==='object')ce=ce.detail;if(ce.specversion!=='1.0')throw Error('not a CloudEvents 1.0 event');if(!ce.data||typeof ce.data!=='object')throw Error('CloudEvent data is not an AER-1 receipt');if(ce.id&&ce.id!==ce.data.id)throw Error('CloudEvent id does not match receipt id');return ce.data}
module.exports={wrap,unwrap};
if(require.main===module){const [op,file]=process.argv.slice(2);if(!['wrap','unwrap'].includes(op))process.exit(2);console.log(JSON.stringify((op==='wrap'?wrap:unwrap)(JSON.parse(file?fs.readFileSync(file,'utf8'):fs.readFileSync(0,'utf8')))))}

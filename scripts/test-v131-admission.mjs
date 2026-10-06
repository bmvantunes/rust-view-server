import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {stripTypeScriptTypes} from 'node:module';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
const bytes=await readFile(new URL('../browser/public/request_admission.wasm',import.meta.url));
const source=await readFile(new URL('../browser/src/request-admission.ts',import.meta.url),'utf8');
const context=vm.createContext({WebAssembly,TextEncoder,TextDecoder,fetch:async()=>({ok:true,arrayBuffer:async()=>bytes})});
vm.runInContext(stripTypeScriptTypes(source.replaceAll('export ','')),context);await context.initializeAdmission();
const trace='00-'+'a'.repeat(32)+'-'+'b'.repeat(16)+'-01';
const query={where_expr:{op:'true'},direction:'ascending',offset:0,limit:4};
const envelope=command=>({v:13,type:'command',incarnation:'a'.repeat(32),connection:'1',nonce:'b'.repeat(32),request:{id:1,acquisition:1,previous_acquisition:null,traceparent:trace,command}});
const admit=command=>JSON.parse(JSON.stringify(context.admitEnvelope(envelope(command))));
const change=where_expr=>({command:'change_query',subscription:'s',query:{...query,where_expr}});
const amount=(coefficient,scale)=>({op:'condition',args:{field:'amount',condition:{op:'equal',value:{coefficient,scale}}}});
const got=admit(change(amount('110',0)));assert.deepEqual(got.request.command.query.where_expr.args.condition.value,{coefficient:'11',scale:-1});
for(const expr of [amount('1',10001),amount('x',0),{op:'unsupported'}]){const rejected=admit(change(expr));assert.equal(rejected.type,'command_rejected');assert.deepEqual(rejected.request,{id:1,traceparent:trace,subscription:'s',code:'invalid_query'});}
for(const offset of [-1,Number.MAX_SAFE_INTEGER+1])assert.equal(admit({command:'change_window',subscription:'s',offset,limit:4}).type,'command_rejected');
assert.equal(admit({...change({op:'true'}),quantity:{ignored:'not a number'}}).type,'command');
let depth=[];
for(let n=0;n<=130;n++){let expr={op:'true'};for(let i=0;i<n;i++)expr={op:'not',args:expr};let state;try{const x=admit(change(expr));state=x.type;assert.deepEqual(x.request.command.query.where_expr,expr);}catch(e){assert.match(String(e),/recursion limit exceeded/);state='terminal source recursion';}depth.push({notCount:n,state});}
const last=depth.findLast(x=>x.state==='command').notCount;assert.equal(last,122);assert.equal(depth[last+1].state,'terminal source recursion');
const large=admit({command:'open',subscription:'s',query:{...query,limit:1000000000000000100}});
assert.equal(large.request.command.query.limit,'1000000000000000100');
assert.equal(admit({command:'delete',id:'not-authorized-over-query-socket'}).type,'command'); // native owner rejects; admission never applies it
const wide=change({op:'or',args:Array.from({length:3000},()=>({op:'true'}))});assert.equal(admit(wide).type,'command');
assert.throws(()=>admit({...change({op:'true'}),ignored:'x'.repeat(65536)}),/source frame budget/);
const report={status:'passed',wasm_sha256:createHash('sha256').update(bytes).digest('hex'),scope:'actual admission-only WASM using unchanged native product types; full-envelope source recursion and byte bounds',lastAdmittedNestedNot:last,depth,canonicalDecimal:got.request.command.query.where_expr.args.condition.value,structuralQueryIdentityPreserved:true};
await writeFile(new URL('../evidence/v13.1/admission-unit.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(report.status,last);

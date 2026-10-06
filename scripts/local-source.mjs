/** Small illustrative source producer. Query evaluation stays entirely in the service. */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
const W=path.resolve(import.meta.dirname,'..');
const [config,action]=process.argv.slice(2);
if(!config||!['reset','match','update','delete'].includes(action))throw Error('Usage: local-source.mjs CONFIG reset|match|update|delete');
const require=createRequire(W+'/experiments/v131/package.json');
const pb=require('protobufjs'),root=new pb.Root();
root.resolvePath=(origin,target)=>target==='google/protobuf/descriptor.proto'?require.resolve('protobufjs/google/protobuf/descriptor.proto'):path.resolve(path.dirname(origin),target);
await root.load(W+'/examples/schema-expansion/topics.proto',{keepCase:true});root.resolveAll();
const bindings=JSON.parse(fs.readFileSync(W+'/fixtures/expanded-topics/source-bindings.json','utf8'));
function frame(type,row){const header=Buffer.alloc(6);header.writeUInt32BE(bindings[type].descriptor.schema_id,1);const t=root.lookupType(type);return Buffer.concat([header,t.encode(t.fromObject(row)).finish()]).toString('hex');}
const child=spawn(W+'/bin/generic_kafka_producer_expanded',[config],{stdio:['pipe','pipe','inherit']});
const lines=createInterface({input:child.stdout});
const receipts=[];let ack=0;
const commands=action==='reset'?[['nested_positions','r',null],['shit','a',{label:'Alice',oo:{name:'A',status:1,price:'12.5',note:'Illustrative source row'}}]]: [['nested_positions','r',action==='delete'?null:{details:{name:'A',status:1,price:action==='update'?'9':'7'}}]];
const timer=setTimeout(()=>{child.kill('SIGKILL');},15000);
try{
 let ready=false;
 for await(const line of lines){
  const result=JSON.parse(line);
  if(result.producer_ready)ready=true;
  else if(result.ack===ack){if(result.error)throw Error(result.error);receipts.push(result);}
  else continue;
  if(!ready)continue;
  if(ack===commands.length){process.stdout.write(JSON.stringify({action,receipts})+'\n');break;}
  const [topic,key,row]=commands[ack++];
  child.stdin.write(JSON.stringify({ack,topic,partition:0,timestamp_ms:Date.now(),raw_key_hex:frame('example.common.Key',{account:{id:key}}),...(row===null?{delete:true}:{raw_value_hex:frame(topic==='shit'?'example.Shit':'example.Position',row)})})+'\n');
 }
 if(receipts.length!==commands.length)throw Error('Source producer exited or timed out before all acknowledgements');
}finally{clearTimeout(timer);lines.close();child.stdin.end();if(child.exitCode===null){child.kill('SIGTERM');await new Promise(resolve=>{const kill=setTimeout(()=>child.kill('SIGKILL'),2000);child.once('exit',()=>{clearTimeout(kill);resolve();});});}}

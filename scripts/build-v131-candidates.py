"""Generate isolated single-codec native/browser peers from sealed V12.4 source.
No production source or historical tests are rewritten by this experiment builder.
"""
from pathlib import Path
import os,shutil,subprocess,json,hashlib,sys,zipfile,tempfile
root=Path(__file__).resolve().parent.parent
out=Path(os.environ.get('V13_WORK',str(root.parent/'v131-work-20261002')))/'candidates'
archive=root/'rust-differential-product-20260929-review-checkpoint-v12.4.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='17d16d9fb5f8028c0ab0a92c50a357102a9c7ed1a6d2a2722a43b050902ce099'
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
reports=[]
for codec in ['json','protobuf','msgpack']:
 dest=out/codec;dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for i in z.infolist():
   if i.filename.startswith(('native/','ingestion/','browser/','fixtures/')):
    z.extract(i,dest)
    if i.external_attr>>16&0o111:(dest/i.filename).chmod(0o755)
 (dest/'browser/public').mkdir(exist_ok=True);(dest/'bin').mkdir(exist_ok=True)
 node=dest/'browser/node_modules'
 if not node.exists():node.symlink_to(root/'browser/node_modules',target_is_directory=True)
 if codec!='json':
  exp=dest/'experiments/v131';exp.mkdir(parents=True,exist_ok=True)
  shutil.copytree(root/'experiments/v131/vendor',exp/'vendor',dirs_exist_ok=True)
  shutil.copytree(root/'experiments/v131/js',exp/'js',dirs_exist_ok=True)
  shutil.copytree(root/'experiments/v131/codec',exp/'codec',dirs_exist_ok=True,ignore=shutil.ignore_patterns('target'))
  shutil.copy2(root/'experiments/v131/package.json',exp/'package.json')
  if not (exp/'node_modules').exists():(exp/'node_modules').symlink_to(root/'experiments/v131/node_modules',target_is_directory=True)
  shutil.copytree(root/'admission',dest/'admission',dirs_exist_ok=True,ignore=shutil.ignore_patterns('target'))
  shutil.copy2(root/'browser/src/request-admission.ts',dest/'browser/src/request-admission.ts')
  shutil.copy2(root/'browser/public/request_admission.wasm',dest/'browser/public/request_admission.wasm')
  cargo=dest/'ingestion/Cargo.toml';s=cargo.read_text().replace('[dependencies]','[dependencies]\nproduct-request-admission = { path = "../admission" }\nv13-codec-experiment = { path = "../experiments/v131/codec", default-features = false, features = ["'+codec+'"] }');cargo.write_text(s)
  p=dest/'ingestion/src/bin/view_server.rs';s=p.read_text()
  wire='pb' if codec=='protobuf' else 'mp'
  s=s.replace('type Core=',f'''fn encode_frame(v:&Value)->Result<(Vec<u8>,u64,u64),String>{{let t=Instant::now();let value=v13_codec_experiment::prepare(v)?;let prep=t.elapsed().as_nanos() as u64;let t=Instant::now();let bytes=v13_codec_experiment::encode_{wire}(&value)?;Ok((bytes,prep,t.elapsed().as_nanos() as u64))}}
fn decode_frame(b:&[u8])->Result<Value,String>{{let v=v13_codec_experiment::adapt(&v13_codec_experiment::decode_{wire}(b)?)?;if v["type"]=="command" {{product_request_admission::check_source_envelope(&v)?;}}Ok(v)}}
type Core=''')
  s=s.replace('VecDeque<String>','VecDeque<Vec<u8>>').replace('encoded_bytes:u64,','encoded_bytes:u64,prepare_ns:u64,').replace('encoded_bytes:0,','encoded_bytes:0,prepare_ns:0,')
  old='let started=Instant::now();let text=v.to_string();peer.encode_ns+=started.elapsed().as_nanos() as u64;'
  new='let (text,prep,ns)=match encode_frame(&v){Ok(v)=>v,Err(_)=>{peer.dead=true;return;}};peer.prepare_ns+=prep;peer.encode_ns+=ns;'
  assert old in s;s=s.replace(old,new)
  s=s.replace('Message::Text(text.into())','Message::Binary(text.into())').replace('Ok(Message::Text(text))','Ok(Message::Binary(text))').replace('request=Some(text.to_string());','request=Some(text.to_vec());')
  s=s.replace('serde_json::from_str(&text)','decode_frame(&text)').replace('"/v12"','"/v13"').replace('"view-server.v12"',f'"view-server.v13.{codec}"').replace('json!(1);v["incarnation"]','json!(13);v["incarnation"]').replace('value["v"]!=1','value["v"]!=13')
  s=s.replace('"encode_ns":p.encode_ns,','"encode_ns":p.encode_ns,"prepare_ns":p.prepare_ns,')
  s=s.replace('const INPUT:usize=65536;', 'const INPUT:usize=4*1024*1024;')
  rejection='''    if value["type"]=="command_rejected" {
     let raw=&value["request"];
     if raw.as_object().is_some_and(|m|m.len()==4) && raw["code"]=="invalid_query" {
      if let (Some(rid),Some(trace),Some(sub))=(raw["id"].as_u64(),raw["traceparent"].as_str(),raw["subscription"].as_str()) {
       if rid>peer.last_id && rid<=9_007_199_254_740_991 && trace.len()==55 && sub.len()<=128 {
        peer.last_id=rid;
        enqueue(peer,envelope(&owner,id,peer,json!({"type":"request_error","id":rid,"traceparent":trace,"error":"invalid typed query command","currentAcquisition":owner.current(id,sub)})));continue;
       }
      }
     }
     peer.dead=true;continue;
    }
'''
  s=s.replace('    if value["type"]!="command"',rejection+'    if value["type"]!="command"')
  s=s.replace('serde_json::from_value(value["request"].clone())', 'product_request_admission::admit_command(value["request"]["command"].clone()).and_then(|command| { let mut request=value["request"].clone(); request["command"]=serde_json::to_value(command).map_err(|e|e.to_string())?; serde_json::from_value(request).map_err(|e|e.to_string()) })')
  p.write_text(s)
  p=dest/'browser/src/product.remote.worker.ts';s=p.read_text()
  s=f'''import {{encode,decodeNative,adapt}} from '../../experiments/v131/js/{codec}.mjs';
import {{initializeAdmission,admitEnvelope}} from './request-admission';
const codec='{codec}';
'''+s
  s=s.replace("const text=JSON.stringify(v);const bytes=new TextEncoder().encode(text).length;","const text=encode(v,codec);const bytes=text.byteLength;")
  s=s.replace('scope.onmessage=e=>','scope.onmessage=async e=>').replace("  socket=new WebSocket","  try{await initializeAdmission();}catch(e){fatal(String(e));return;}if(done)return;\n  socket=new WebSocket")
  s=s.replace("send(envelope({type:'command',request:{id:m.id,acquisition:m.acquisition??0,previous_acquisition:m.previousAcquisition??null,traceparent:m.traceparent,command:m.command}}))","send(admitEnvelope(envelope({type:'command',request:{id:m.id,acquisition:m.acquisition??0,previous_acquisition:m.previousAcquisition??null,traceparent:m.traceparent,command:m.command}})))")
  s=s.replace('bytes>65536||socket.bufferedAmount+bytes>131072','bytes>4194304||socket.bufferedAmount+bytes>8388608')
  s=s.replace('v:1','v:13').replace("url.pathname!=='/v12'","url.pathname!=='/v13'").replace("new WebSocket(url,'view-server.v12')",f"new WebSocket(url,'view-server.v13.{codec}')")
  s=s.replace('socket.onopen=',"socket.binaryType='arraybuffer';socket.onopen=")
  s=s.replace("if(done||typeof e.data!=='string')return;","if(done)return;if(!(e.data instanceof ArrayBuffer)){fatal('binary frame required');return;}")
  s=s.replace('new TextEncoder().encode(e.data).length','e.data.byteLength')
  s=s.replace("let v:unknown;try{v=JSON.parse(e.data);}catch{fatal('malformed remote JSON');return;}","let v:unknown;let decodeNs=0,adaptNs=0;try{const t=performance.now();const native=decodeNative(new Uint8Array(e.data),codec);decodeNs=Math.round((performance.now()-t)*1e6);const a=performance.now();v=adapt(native,codec);adaptNs=Math.round((performance.now()-a)*1e6);}catch{fatal('malformed binary frame');return;}")
  s=s.replace('v.v!==1','v.v!==13')
  s=s.replace("   if(!record(v)||v.v!==13","   if(!record(v)||v.v!==13){fatal('incompatible binary envelope version');return;}\n   if(!record(v)||v.v!==13")
  s=s.replace('encodedBytes:e.data.byteLength','encodedBytes:e.data.byteLength,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)')
  p.write_text(s)
 shutil.copy2(root/'experiments/v131/source-recursion.rs',dest/'ingestion/tests/v131_source_recursion.rs')
 # Re-run the preserved native socket schedules against the corresponding binary peer.
 if codec!='json':
  p=dest/'ingestion/tests/v12_socket.rs';s=p.read_text().replace('/v12','/v13').replace('view-server.v12',f'view-server.v13.{codec}').replace('"v":1','"v":13')
  s=s.replace('Message::Text(json!','wire(json!').replace('.to_string().into()', '')
  s=s.replace('Message::Text(t)=>return serde_json::from_str(&t).unwrap()',f'Message::Binary(t)=>return v13_codec_experiment::adapt(&v13_codec_experiment::decode_{wire}(&t).unwrap()).unwrap()')
  s=s.replace('fn command(',f'fn wire(v:Value)->Message{{Message::Binary(v13_codec_experiment::encode_{wire}(&v13_codec_experiment::prepare(&v).unwrap()).unwrap().into())}}\nfn command(')
  vectors=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {hostile} from './scripts/v131-hostile-vectors.mjs'; console.log(JSON.stringify(hostile));"],cwd=root,text=True))[codec]
  rust_vectors='vec!['+','.join('vec!['+','.join(map(str,v))+']' for v in vectors.values())+']'
  s+='\n'+(root/'experiments/v131/hostile-socket.rs').read_text().replace('HOSTILE_BYTES',rust_vectors)
  p.write_text(s)
 # Bounded per-frame diagnostics emitted only at peer shutdown; identical collection policy.
 p=dest/'ingestion/src/bin/view_server.rs';s=p.read_text()
 s=s.replace('encode_ns:u64,','encode_ns:u64,encode_samples:Vec<(u64,u64,u64,u64)>,').replace('encode_ns:0,','encode_ns:0,encode_samples:Vec::new(),')
 if codec=='json':
  s=s.replace('peer.encode_ns+=started.elapsed().as_nanos() as u64;', 'let ns=started.elapsed().as_nanos() as u64;let prep=0;peer.encode_ns+=ns;')
 s=s.replace('peer.encoded_bytes+=text.len() as u64;', 'if peer.encode_samples.len()<16384{peer.encode_samples.push((v["source_sequence"].as_str().and_then(|v|v.parse().ok()).unwrap_or(0),prep,ns,text.len() as u64));}peer.encoded_bytes+=text.len() as u64;')
 s=s.replace('"encode_ns":p.encode_ns,','"encode_ns":p.encode_ns,"encode_samples":p.encode_samples,')
 p.write_text(s)
 # Identical diagnostic-only Worker instrumentation for every candidate.
 p=dest/'browser/src/product.remote.worker.ts';s=p.read_text()
 if codec=='json':
  s=s.replace("let v:unknown;try{v=JSON.parse(e.data);}catch", "let v:unknown;let decodeNs=0,adaptNs=0;try{const t=performance.now();v=JSON.parse(e.data);decodeNs=Math.round((performance.now()-t)*1e6);}catch")
  s=s.replace('encodedBytes:new TextEncoder().encode(e.data).length','encodedBytes:new TextEncoder().encode(e.data).length,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)')
 s=s.replace('const post=(v:unknown)=>scope.postMessage(v);', "const post=(v:unknown)=>{const t=performance.now();scope.postMessage(v);const ns=Math.round((performance.now()-t)*1e6);scope.postMessage({type:'v13_metrics',postCallNs:ns,workerTimeOrigin:performance.timeOrigin,workerEndNs:Math.round(performance.now()*1e6)});};")
 s=s.replace('encodedBytes:e.data.byteLength,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)};', "encodedBytes:e.data.byteLength,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)} as ProductResult['remote'];")
 s=s.replace('encodedBytes:new TextEncoder().encode(e.data).length,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)};', "encodedBytes:new TextEncoder().encode(e.data).length,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)} as ProductResult['remote'];")
 p.write_text(s)
 # Benchmark instrumentation is identical across all candidates and touches the test harness only.
 p=dest/'browser/src/v12-harness.tsx';s=p.read_text().replace("const mounted:Record", "const hookSamples:unknown[]=[];\nconst mounted:Record")
 s=s.replace("const q:ProductQuery={where_expr:distinct?", "const q:ProductQuery={where_expr:distinct?")
 s=s.replace('offset:id%3,limit:2','offset:id%3,limit:Number((globalThis as any).v13Window??2)')
 s=s.replace("mounted[String(id)]={status:","if(view.data)hookSamples.push({id,ns:Math.round(performance.now()*1e6),timeOrigin:performance.timeOrigin,result:view.data});mounted[String(id)]={status:")
 s=s.replace('results,errors,mounted,callbackLog,','results,errors,mounted,callbackLog,hookSamples,')
 p.write_text(s)
 env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'v121-service-target'),CARGO_BUILD_JOBS='2')
 if codec!='json':subprocess.run(['rustup','run','1.96.1','cargo','metadata','--offline','--format-version','1','--manifest-path','ingestion/Cargo.toml'],cwd=dest,env=env,check=True,stdout=subprocess.DEVNULL)
 command=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--bin','view_server','--features','kafka-tls']
 subprocess.run(command,cwd=dest,env=env,check=True);shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/view_server',dest/'bin/view_server')
 # Test-only fault artifact keeps the same wire; ordinary still excludes fault controls.
 env['CARGO_TARGET_DIR']=str(Path(tempfile.gettempdir())/'v121-fault-service-target');command[-1]='kafka-tls,fault-injection'
 subprocess.run(command,cwd=dest,env=env,check=True);shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/view_server',dest/'bin/view_server_faults')
 hashes={p:hashlib.sha256((dest/p).read_bytes()).hexdigest() for p in ['bin/view_server','bin/view_server_faults','browser/src/product.remote.worker.ts','browser/src/v12-harness.tsx','ingestion/src/bin/view_server.rs','ingestion/Cargo.lock']+(['browser/public/request_admission.wasm','browser/src/request-admission.ts','admission/src/lib.rs','admission/Cargo.lock','experiments/v131/js/'+codec+'.mjs','experiments/v131/js/values.mjs','experiments/v131/js/scan.mjs','experiments/v131/codec/src/lib.rs','experiments/v131/codec/Cargo.toml'] if codec!='json' else [])}
 if codec!='json':hashes.update({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (dest/'experiments/v131/vendor').rglob('*') if p.is_file()})
 assert b'V121_FAULT_DIR' not in (dest/'bin/view_server').read_bytes()
 reports.append({'codec':codec,'root':str(dest),'sha256':hashes})
(root/'evidence/v13.1/candidate-builds.json').write_text(json.dumps({'status':'built','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'candidates':reports},indent=2)+'\n')

from pathlib import Path
import subprocess,os,json,hashlib,time,shutil
W=Path(__file__).resolve().parent;out=W.parent/'evidence/native';out.mkdir(parents=True,exist_ok=True)
target=W.parents[1]/'stage0-independent/native-target'
old=Path('/Users/bruno/Projects/rust-view-server/followups/configurable-topics-v1.1-source-presence-20261004/work/ingestion/target/release')
if not (target/'release').exists():subprocess.run(['cp','-cR',str(old),str(target/'release')],check=True)
env={**os.environ,'RUSTC':'/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc','RUSTDOC':'/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc','CARGO_TARGET_DIR':str(target)}
cargo='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo'
def inputs():return {str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for area in ['native','admission','ingestion','experiments/v131/codec'] for p in (W/area).rglob('*') if p.is_file() and 'target' not in p.parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
for label,features,args,source,destination in [('ordinary','kafka-canonical',['--release','--bin','view_server'],target/'release/view_server',W/'bin/view_server_kafka_topics'),('fault','kafka-canonical,fault-injection',['--release','--bin','view_server'],target/'release/view_server',W/'bin/view_server_kafka_topics_faults'),('producer','kafka-canonical',['--example','generic_kafka_producer'],target/'debug/examples/generic_kafka_producer',W/'bin/generic_kafka_producer_fixture'),('probe','kafka-canonical',['--example','source_presence_probe'],target/'debug/examples/source_presence_probe',W/'bin/source_presence_probe')]:
 before=inputs();cmd=[cargo,'build','--locked','--offline','--manifest-path',str(W/'ingestion/Cargo.toml'),'--features',features,*args];stamp=str(time.time_ns());log=out/(label+'-build-'+stamp+'.log');print('START '+label,flush=True);start=time.monotonic()
 with open(log,'w')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 after=inputs();receipt=dict(command=cmd,inputs_before=before,inputs_after=after,inputs_unchanged=before==after,exit=r.returncode,elapsed_seconds=time.monotonic()-start)
 if r.returncode==0 and before==after:
  shutil.copy2(source,destination);receipt['binary']=str(destination.relative_to(W));receipt['sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
  if label in ['producer','probe']:
   link=W/'ingestion/target/debug/examples'/('generic_kafka_producer' if label=='producer' else 'source_presence_probe');link.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,link)
 log.with_suffix('.json').write_text(json.dumps(receipt,indent=2));print('END '+label+': '+str(r.returncode),flush=True)
 if r.returncode or before!=after:raise SystemExit(r.returncode or 1)

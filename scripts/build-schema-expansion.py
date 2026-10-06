#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,hashlib,json,shutil,time
w=Path(__file__).resolve().parents[1];e=w/'evidence/schema-expansion/build';e.mkdir(parents=True,exist_ok=True)
cargo='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo';target=Path('/private/tmp/schema-expansion-v1-target')
env=dict(os.environ,RUSTC='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc',RUSTDOC='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc',RUSTUP_TOOLCHAIN='1.96.1',CARGO_TARGET_DIR=str(target),CARGO_BUILD_JOBS='4')
def sources():return {str(p.relative_to(w)):hashlib.sha256(p.read_bytes()).hexdigest() for root in ['native','ingestion','admission','experiments/v131/codec'] for p in (w/root).rglob('*') if p.is_file() and 'target' not in p.parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
for name,features,args,src in [('view_server_expanded','kafka-canonical',['--bin','view_server'],'view_server'),('view_server_expanded_faults','kafka-canonical,fault-injection',['--bin','view_server'],'view_server'),('generic_kafka_producer_expanded','kafka-canonical',['--example','generic_kafka_producer'],'examples/generic_kafka_producer')]:
 stamp=str(time.time_ns());before=sources();cmd=[cargo,'build','--offline','--locked','--release','--manifest-path',str(w/'ingestion/Cargo.toml'),'--features',features,*args]
 with (e/(name+'-'+stamp+'.log')).open('w') as f:r=subprocess.run(cmd,env=env,cwd=w,stdout=f,stderr=subprocess.STDOUT)
 receipt={'command':cmd,'exit':r.returncode,'rustc':subprocess.check_output([env['RUSTC'],'-Vv'],text=True),'inputs_before':before,'inputs_after':sources()}
 if r.returncode==0 and before==receipt['inputs_after']:
  shutil.copy2(target/'release'/src,w/'bin'/name);receipt['binary_sha256']=hashlib.sha256((w/'bin'/name).read_bytes()).hexdigest()
 (e/(name+'-'+stamp+'.json')).write_text(json.dumps(receipt,indent=2));assert r.returncode==0 and before==receipt['inputs_after'],name
 print(name,receipt['binary_sha256'],flush=True)

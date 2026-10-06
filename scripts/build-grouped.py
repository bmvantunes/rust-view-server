#!/usr/bin/env python3
from pathlib import Path
import subprocess,hashlib,json,time,os
W=Path(__file__).resolve().parents[1];out=W/'evidence/grouped/build';out.mkdir(exist_ok=True);cargo='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo'
def inputs():return {str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest()for d in ['native','ingestion','admission','experiments/v131/codec']for p in (W/d).rglob('*')if p.is_file()and'target'not in p.parts and(p.suffix=='.rs'or p.name in ['Cargo.toml','Cargo.lock'])}
for name,features,target,source in [('view_server_grouped','kafka-canonical',['--bin','view_server'],'view_server'),('view_server_grouped_faults','kafka-canonical,fault-injection',['--bin','view_server'],'view_server'),('generic_kafka_producer_grouped','kafka-canonical',['--example','generic_kafka_producer'],'examples/generic_kafka_producer')]:
 before=inputs();start=time.monotonic();cmd=[cargo,'build','--manifest-path',str(W/'ingestion/Cargo.toml'),'--release','--features',features,'--locked','--offline',*target];stamp=str(time.time_ns())
 with open(out/(name+'-'+stamp+'.log'),'w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 after=inputs();receipt=dict(command=cmd,exit=r.returncode,elapsed_seconds=time.monotonic()-start,inputs_before=before,inputs_after=after);assert before==after
 if r.returncode==0:
  import shutil
  shutil.copy2(W/'ingestion/target/release'/source,W/'bin'/name);receipt['binary_sha256']=hashlib.sha256((W/'bin'/name).read_bytes()).hexdigest()
 (out/(name+'-'+stamp+'.json')).write_text(json.dumps(receipt,indent=2));assert r.returncode==0
 print('BUILT',name,receipt['binary_sha256'],flush=True)

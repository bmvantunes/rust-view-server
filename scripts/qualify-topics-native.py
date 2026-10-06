#!/usr/bin/env python3
"""Finite affected offline native checks and exact per-run evidence retention."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
root=Path(__file__).resolve().parent.parent
out=root.parent/'evidence/native';out.mkdir(exist_ok=True)
commands={
 'native-all':['cargo','test','--locked','--offline','--manifest-path','native/Cargo.toml','--','--test-threads=1'],
 'ingestion-lib':['cargo','test','--locked','--offline','--manifest-path','ingestion/Cargo.toml','--features','kafka-canonical','--lib','--','--test-threads=1'],
 'admission':['cargo','test','--locked','--offline','--manifest-path','admission/Cargo.toml'],
 'generic-owner':['cargo','test','--locked','--offline','--manifest-path','ingestion/Cargo.toml','--features','kafka-canonical','--test','generic_owner','--','--test-threads=1'],
 'source-boundary':['python3','scripts/check-engine-boundary.py'],
 'source-admission':['cargo','test','--locked','--offline','--manifest-path','ingestion/Cargo.toml','--features','kafka-canonical','--test','generic_source_config','--test','wire_registry','--test','v131_source_recursion','--test','partition_metadata','--test','kafka_state','--test','durable_coordinator','--test','v121_fence','--','--test-threads=1'],
 'license':['python3','scripts/audit-topics-licenses.py'],
 'ordinary-build':['cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--features','kafka-canonical','--bin','view_server'],
 'fault-build':['cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--features','kafka-canonical,fault-injection','--bin','view_server'],
}
mode=sys.argv[1];command=commands[mode];run=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');log=out/f'{mode}-{run}.log'
inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for area in ['native','admission','ingestion','experiments/v131/codec'] for p in (root/area).rglob('*') if p.is_file() and ('target' not in p.parts) and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
start=time.monotonic()
with log.open('w') as f:
 result=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT)
after={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for area in ['native','admission','ingestion','experiments/v131/codec'] for p in (root/area).rglob('*') if p.is_file() and ('target' not in p.parts) and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
meta=dict(inputs_unchanged=inputs==after,inputs_after=after,command=command,cwd=str(root),started_utc=run,elapsed_seconds=time.monotonic()-start,returncode=result.returncode,log=log.name,inputs=inputs)
if result.returncode==0 and mode in ['ordinary-build','fault-build']:
 destination=root/'bin'/('view_server_kafka_topics' if mode=='ordinary-build' else 'view_server_kafka_topics_faults');source=root/'ingestion/target/release/view_server'
 import shutil
 shutil.copy2(source,destination);meta['binary']=str(destination.relative_to(root));meta['binary_sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
log.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({k:v for k,v in meta.items() if k not in ['inputs','inputs_after']}));sys.exit(result.returncode)

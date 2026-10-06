from pathlib import Path
import subprocess,os,json,hashlib,time
W=Path(__file__).resolve().parent;out=W.parent/'evidence/native';out.mkdir(parents=True,exist_ok=True)
env={**os.environ,'RUSTC':'/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc','RUSTDOC':'/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc','CARGO_TARGET_DIR':str(W.parents[1]/'stage0-independent/native-target')}
cargo='/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo'
gates=[('rowid-native-all',['--manifest-path',str(W/'native/Cargo.toml')]),('rowid-source-owner',['--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical',*sum((['--test',t]for t in ['source_identity','source_presence','source_presence_original','generic_owner','generic_source_config','wire_registry','v131_source_recursion','partition_metadata','kafka_state','durable_coordinator','v121_fence']),[])]),('rowid-ingestion-lib',['--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical','--lib']),('rowid-fault-presence',['--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical,fault-injection','--test','source_identity','--test','source_presence','--test','source_presence_original'])]
for label,args in gates:
 cmd=[cargo,'test','--locked','--offline',*args,'--','--test-threads=1','--nocapture'];print('START '+label,flush=True);stamp=str(time.time_ns());log=out/(label+'-'+stamp+'.log');start=time.monotonic()
 with open(log,'w')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 log.with_suffix('.json').write_text(json.dumps(dict(command=cmd,exit=r.returncode,elapsed_seconds=time.monotonic()-start),indent=2));print('END '+label+': '+str(r.returncode),flush=True)
 if r.returncode:raise SystemExit(r.returncode)

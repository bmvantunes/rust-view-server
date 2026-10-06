#!/usr/bin/env python3
"""Build the ordinary service and illustrative producer from this checkout only."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
W=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--offline',action='store_true');a=p.parse_args()
env={**os.environ,'RUSTUP_TOOLCHAIN':'1.96.1','CARGO_BUILD_JOBS':os.environ.get('CARGO_BUILD_JOBS','2')}
for name in ['rustc','rustdoc']:
 env[name.upper()]=subprocess.check_output(['rustup','which','--toolchain','1.96.1',name],text=True).strip()
cargo=subprocess.check_output(['rustup','which','--toolchain','1.96.1','cargo'],text=True).strip()
version=subprocess.check_output([env['RUSTC'],'--version'],text=True).strip()
if not version.startswith('rustc 1.96.1 '):raise SystemExit('Expected installed Rust1.96.1; no toolchain download is performed here')
host=next(line.removeprefix('host: ') for line in subprocess.check_output([env['RUSTC'],'-vV'],text=True).splitlines() if line.startswith('host: '))
target=Path(os.environ.get('CARGO_TARGET_DIR',str(W/'.local/target'))).resolve();env['CARGO_TARGET_DIR']=str(target)
cmd=[cargo,'build','--locked','--release','--target',host,'--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical','--bin','view_server','--example','generic_kafka_producer']
if a.offline:cmd.append('--offline')
print(' '.join(cmd),flush=True);subprocess.run(cmd,cwd=W,env=env,check=True)
out=W/'.local/bin';out.mkdir(parents=True,exist_ok=True);hashes={}
for name,rel in [('view_server','view_server'),('generic_kafka_producer','examples/generic_kafka_producer')]:
 shutil.copy2(target/host/'release'/rel,out/name);hashes[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
(out/'BUILD.json').write_text(json.dumps({'rustc':version,'host':host,'command':cmd,'binary_sha256':hashes},indent=2)+'\n')
print(json.dumps(hashes,indent=2))

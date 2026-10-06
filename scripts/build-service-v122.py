from pathlib import Path
import subprocess,os,tempfile,shutil,json,hashlib
root=Path(__file__).resolve().parent.parent
(root/'evidence/v12.2').mkdir(parents=True,exist_ok=True)
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'v121-service-target'),CARGO_BUILD_JOBS='2')
command=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--bin','view_server','--features','kafka-tls']
subprocess.run(command,cwd=root,env=env,check=True);dest=root/'bin/view_server';dest.parent.mkdir(exist_ok=True);shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/view_server',dest)
assert b'V121_FAULT_DIR' not in dest.read_bytes(), 'fault controls leaked into ordinary release'
report=dict(command=command,exit=0,run_id=os.environ.get('ACCEPTANCE_RUN_ID'),binary_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),rustc=subprocess.check_output([rustc,'-Vv'],text=True))
(root/'evidence/v12.2/service-build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

env['CARGO_TARGET_DIR']=str(Path(tempfile.gettempdir())/'v121-fault-service-target')
command[-1]='kafka-tls,fault-injection'
subprocess.run(command,cwd=root,env=env,check=True)
dest=root/'bin/view_server_faults';shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/view_server',dest)
report=dict(command=command,exit=0,run_id=os.environ.get('ACCEPTANCE_RUN_ID'),binary_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),purpose='test-only file barriers; not the release service')
(root/'evidence/v12.2/fault-service-build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

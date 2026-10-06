from pathlib import Path
import subprocess,os,tempfile,shutil,json,hashlib
root=Path(__file__).resolve().parent.parent
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'v12-service-target'),CARGO_BUILD_JOBS='2')
command=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--bin','view_server','--features','kafka-tls']
subprocess.run(command,cwd=root,env=env,check=True);dest=root/'bin/view_server';dest.parent.mkdir(exist_ok=True);shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/view_server',dest)
report=dict(command=command,exit=0,run_id=os.environ.get('ACCEPTANCE_RUN_ID'),binary_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),rustc=subprocess.check_output([rustc,'-Vv'],text=True))
(root/'evidence/v12-service-build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

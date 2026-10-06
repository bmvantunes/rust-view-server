from pathlib import Path
import subprocess,json,os,tempfile
r=Path(__file__).resolve().parent.parent;builds=json.loads((r/'evidence/v13.1/candidate-builds.json').read_text())['candidates'];records=[]
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
for b in builds:
 env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'rust-product-v7-target'),CARGO_BUILD_JOBS='2')
 cmd=['rustup','run','1.96.1','cargo','test','--locked','--offline','--manifest-path','ingestion/Cargo.toml','--features','kafka-tls','--test','v12_socket','--','--nocapture']
 log=r/('evidence/v13.1/native-socket-'+b['codec']+'.log')
 with log.open('w') as f:p=subprocess.run(cmd,cwd=b['root'],env=env,stdout=f,stderr=subprocess.STDOUT)
 records.append({'codec':b['codec'],'exit':p.returncode,'command':cmd});print(records[-1],flush=True);assert p.returncode==0
(r/'evidence/v13.1/native-sockets.json').write_text(json.dumps({'status':'passed','records':records},indent=2)+'\n')

from pathlib import Path
import hashlib,json,os,subprocess,tempfile,time
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v12/measurements';out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():return {p.relative_to(root).as_posix():sha(p) for d in ['native','ingestion'] for p in (root/d).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/d).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
env=dict(os.environ,RUSTC=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip(),RUSTDOC=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustdoc'],text=True).strip(),CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(root/'ingestion/target'))
starting_source=sources()
command=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','ingestion/Cargo.toml','--bin','view_server','--example','v12_measure','--features','kafka-tls']
with (out/'build.log').open('w') as log:subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=root/'ingestion/target/release/examples/v12_measure';service=root/'ingestion/target/release/view_server';runs=[]
for partitions in [1,16,256]:
 with tempfile.TemporaryDirectory(prefix='v12-measure-') as d:
  cmd=[str(binary),str(Path(d)/'canonical.db'),str(partitions)];started=time.time_ns();raw=out/f'p{partitions}.jsonl'
  with raw.open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.PIPE,text=True,cwd=root)
  runs.append(dict(P=partitions,command=cmd,started_ns=started,finished_ns=time.time_ns(),exit=result.returncode,raw=raw.name,raw_sha256=sha(raw)));assert result.returncode==0,result.stderr
assert sources()==starting_source,'Source changed during measurement'
(out/'runs.json').write_text(json.dumps(dict(source=sources(),build_command=command,binary_sha256=sha(binary),service_sha256=sha(service),runs=runs),indent=2)+'\n')
print('Completed three serial controlled quiescent comparisons')

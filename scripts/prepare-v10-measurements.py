"""Build the exact bounded release harness; accepted archives are read-only inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v10/measurements'
label=sys.argv[1];assert label in ['v9','v10']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if label=='v9':
 tree=Path('/private/tmp/v10-accepted-v9');tree.mkdir(exist_ok=True)
 archive=root/'rust-differential-product-20260929-review-checkpoint-v9.zip'
 assert sha(archive)=='d2fe23ef4282e66a3ff4139be35a1303581026573f472b8a0e7133d4f4b6fc65'
 with zipfile.ZipFile(archive) as z:
  for name in z.namelist():
   if name.startswith(('native/','ingestion/')):z.extract(name,tree)
 (tree/'ingestion/src/durable.rs').write_bytes((out/'v9-counter-overlay.rs.txt').read_bytes())
 (tree/'ingestion/examples/v10_measure.rs').write_bytes((root/'ingestion/examples/v10_measure.rs').read_bytes())
else:tree=root
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR='/private/tmp/v10-measure-target')
cmd=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path',str(tree/'ingestion/Cargo.toml'),'--example','v10_measure']
r=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/(label+'-build.log')).write_text(r.stdout+r.stderr);r.check_returncode()
print('Built '+label+'; next: python3 scripts/measure-v10.py '+label)

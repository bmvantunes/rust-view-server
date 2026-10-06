"""Build both candidates before timing. Only additive counters overlay accepted v10."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile,shutil
from v11_counter_overlay import overlay,NAMES
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v11/measurements';out.mkdir(parents=True,exist_ok=True)
label=sys.argv[1];assert label in ['v10','v11']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'rust-differential-product-20260929-review-checkpoint-v10.zip'
assert sha(archive)=='621193770c1869e49aa4d660a08543c958e807e591ab615899c5c29db7574cb3'
if label=='v10':
 tree=Path('/private/tmp/v11-accepted-v10');tree.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for name in z.namelist():
   if name.startswith(('native/','ingestion/')):z.extract(name,tree)
  for name in NAMES:
   content=overlay(name,z.read(name).decode());(tree/name).write_text(content)
   (out/('v10-'+Path(name).stem+'-counter-overlay.txt')).write_text(content)
 (tree/'ingestion/examples/v11_measure.rs').write_bytes((root/'ingestion/examples/v11_measure.rs').read_bytes())
else:tree=root
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_TARGET_DIR='/private/tmp/v11-measure-target')
cmd=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path',str(tree/'ingestion/Cargo.toml'),'--example','v11_measure']
r=subprocess.run(cmd,env=env,text=True,capture_output=True);(out/(label+'-build.log')).write_text(r.stdout+r.stderr);r.check_returncode()
binary=Path('/private/tmp/v11-measure-'+label);shutil.copy2('/private/tmp/v11-measure-target/release/examples/v11_measure',binary)
implementation={p.relative_to(tree).as_posix():sha(p) for folder in ['native','ingestion'] for p in (tree/folder).rglob('*') if p.is_file() and 'target' not in p.relative_to(tree/folder).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
(out/(label+'-build.json')).write_text(json.dumps({'candidate':label,'command':cmd,'exit':r.returncode,'binary_sha256':sha(binary),'harness_sha256':sha(root/'ingestion/examples/v11_measure.rs'),'implementation_sha256':implementation,'archive_sha256':sha(archive),'profile':'release','rustc':subprocess.check_output([rustc,'-Vv'],text=True)},indent=2)+'\n')
print('Built '+label,flush=True)

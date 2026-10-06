"""Create immutable v7 review archive with full member hashes, excluding build/cache/secrets."""
from pathlib import Path
import os,json,hashlib,zipfile
root=Path(__file__).resolve().parent.parent
name='rust-differential-product-20260929-review-checkpoint-v7.zip';archive=root/name
if archive.exists():raise FileExistsError('Never overwrite an existing checkpoint archive')
summary=json.loads((root/'evidence/v7/validation.json').read_text());assert all(g['exit']==0 for g in summary['gates'])
assert hashlib.sha256((root/'rust-differential-product-20260929-review-checkpoint-v6.zip').read_bytes()).hexdigest()==summary['baseline_sha256']
manifest=root/'evidence/v7/manifest.sha256';files=[]
for tree in ['browser','native','ingestion','fixtures','scripts','reports','logs','evidence','investigations','contract-tests','.github']:
 for directory,dirs,names in os.walk(root/tree,followlinks=False):
  dirs[:]=[d for d in dirs if d not in {'node_modules','target','__screenshots__','.vite','v5-baseline-run','__pycache__'} and not (Path(directory)/d).is_symlink()]
  for filename in names:
   p=Path(directory)/filename
   if p==manifest or p.is_symlink() or p.suffix in {'.zip','.pyc'} or filename=='.DS_Store':continue
   if filename.startswith('.env'):raise RuntimeError('Unexpected environment file: '+str(p))
   files.append(p)
files += [root/n for n in ['ARCHITECTURE.md','CONTRACT-MATRIX.md','IMPLEMENTATION-PLAN.md','CLOUD-HANDOFF.md','clippy.toml']]
files=sorted(set(files));manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}\n' for p in files));files.append(manifest)
temporary=archive.with_suffix('.zip.tmp')
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=False) as z:
 for p in files:z.write(p,p.relative_to(root))
with zipfile.ZipFile(temporary) as z:
 assert z.testzip() is None
 for line in z.read(str(manifest.relative_to(root))).decode().splitlines():
  digest,member=line.split('  ',1);assert hashlib.sha256(z.read(member)).hexdigest()==digest,member
 assert hashlib.sha256(z.read('browser/public/product_core.wasm')).hexdigest()==summary['wasm_sha256']
 for required in ['ingestion/src/kafka.rs','ingestion/Cargo.lock','ingestion/tests/kafka_client.rs','evidence/v7/licenses.json','browser/src/v51.browser.test.tsx','native/src/product_engine/distinct.rs']:
  assert required in z.namelist()
temporary.replace(archive)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();(root/(name+'.sha256')).write_text(f'{digest}  {name}\n')
print(json.dumps({'archive':str(archive),'sha256':digest,'wasm_sha256':summary['wasm_sha256'],'files':len(files),'verification':'ZIP CRC + all member hashes + baseline archive hash + required members + WASM'},indent=2))

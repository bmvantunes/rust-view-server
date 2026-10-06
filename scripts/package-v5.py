"""Package explicit checkpoint trees, excluding caches, previous archives and local baseline execution."""
from pathlib import Path
import hashlib, os, zipfile
root = Path(__file__).resolve().parent.parent
name = 'rust-differential-product-20260929-review-checkpoint-v5.zip'
files = []
for tree in ['browser','native','fixtures','scripts','reports','logs','evidence','investigations']:
    for directory, dirs, names in os.walk(root / tree, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {'node_modules','target','__screenshots__','.vite','v5-baseline-run','__pycache__'} and not (Path(directory)/d).is_symlink()]
        for n in names:
            p = Path(directory)/n
            if p.is_symlink() or p.suffix in {'.zip','.pyc'} or n in {'.DS_Store','v5-manifest.sha256'}: continue
            if n.startswith('.env'): raise RuntimeError('Unexpected environment file in package')
            files.append(p)
files += [root/n for n in ['ARCHITECTURE.md','CONTRACT-MATRIX.md','IMPLEMENTATION-PLAN.md','CLOUD-HANDOFF.md']]
files = sorted(set(files))
manifest = root/'evidence/v5-manifest.sha256'
manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}\n' for p in files))
files.append(manifest)
archive = root/name
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files: z.write(p,p.relative_to(root))
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(root/(name+'.sha256')).write_text(f'{digest}  {name}\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for line in z.read('evidence/v5-manifest.sha256').decode().splitlines():
        expected, member = line.split('  ',1)
        assert hashlib.sha256(z.read(member)).hexdigest() == expected, member
    wasm_digest = hashlib.sha256(z.read('browser/public/product_core.wasm')).hexdigest()
    import json
    assert json.loads(z.read('evidence/v5-browser-runtime.json'))['wasmSha256'] == wasm_digest
    assert not any('/node_modules/' in n or '/target/' in n or n.endswith('.zip') for n in z.namelist())
print(f'FILES={len(files)}\nARCHIVE={archive}\nSHA256={digest}\nWASM_SHA256={wasm_digest}\nSIDECAR={root/(name+".sha256")}\nVERIFY=CRC, every manifest member, browser-loaded WASM hash, exclusions passed')

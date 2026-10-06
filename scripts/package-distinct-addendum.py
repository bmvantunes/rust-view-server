"""Package the addendum separately; never overwrite the original v5 archive."""
from pathlib import Path
import hashlib
import json
import os
import zipfile

root = Path(__file__).resolve().parent.parent
name = 'rust-differential-product-20260929-review-checkpoint-v5-distinct-addendum.zip'
archive = root / name
if archive.exists():
    raise FileExistsError(f'Preserve the existing archive before repackaging: {archive}')
original = root / 'rust-differential-product-20260929-review-checkpoint-v5.zip'
assert hashlib.sha256(original.read_bytes()).hexdigest() == 'b61d23b2c7b67526e205a529783af66913cc05565ef73ac6a8ee1e35213a99a3'
manifest = root / 'evidence/distinct-addendum-manifest.sha256'
files = []
for tree in ['browser', 'native', 'fixtures', 'scripts', 'reports', 'logs', 'evidence',
             'investigations', 'contract-tests', '.github']:
    for directory, dirs, names in os.walk(root / tree, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {'node_modules', 'target', '__screenshots__',
                   '.vite', 'v5-baseline-run', '__pycache__'} and not (Path(directory) / d).is_symlink()]
        for filename in names:
            p = Path(directory) / filename
            if p == manifest or p.is_symlink() or p.suffix in {'.zip', '.pyc'} or filename == '.DS_Store':
                continue
            if filename.startswith('.env'):
                raise RuntimeError(f'Unexpected environment file: {p}')
            files.append(p)
files += [root / n for n in ['ARCHITECTURE.md', 'CONTRACT-MATRIX.md', 'IMPLEMENTATION-PLAN.md',
                            'CLOUD-HANDOFF.md', 'clippy.toml']]
files = sorted(set(files))
manifest.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}\n' for p in files))
files.append(manifest)
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files:
        z.write(p, p.relative_to(root))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for line in z.read(str(manifest.relative_to(root))).decode().splitlines():
        digest, member = line.split('  ', 1)
        assert hashlib.sha256(z.read(member)).hexdigest() == digest, member
    wasm = hashlib.sha256(z.read('browser/public/product_core.wasm')).hexdigest()
    assert json.loads(z.read('evidence/distinct-addendum-browser-runtime.json'))['wasmSha256'] == wasm
    assert json.loads(z.read('evidence/distinct-addendum-validation.json'))['wasm_sha256'] == wasm
    assert not any('/node_modules/' in n or '/target/' in n or n.endswith('.zip') for n in z.namelist())
    for member in ['clippy.toml', '.github/workflows/native.yml', 'contract-tests/count_distinct.rs',
                   'investigations/count-distinct/Cargo.lock', 'native/src/product_engine/distinct.rs']:
        assert member in z.namelist()
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(root / (name + '.sha256')).write_text(f'{digest}  {name}\n')
print(f'ARCHIVE={archive}\nFILES={len(files)}\nSHA256={digest}\nWASM_SHA256={wasm}\nVERIFY=CRC, every member hash, browser-loaded WASM, required files, exclusions; original v5 preserved')

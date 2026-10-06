"""Read-only sealed V12.3 integrity review; hashes never imply execution."""
from pathlib import Path
import hashlib, json, zipfile
root = Path(__file__).resolve().parent.parent
name = 'rust-differential-product-20260929-review-checkpoint-v12.3.zip'
archive = root / name
sha = lambda value: hashlib.sha256(value).hexdigest()
expected = 'b35504ee3d90c576db1ee62a5a608f56702426918ac28c7bce6374c87be720a8'
assert sha(archive.read_bytes()) == expected
sidecar = root / (name + '.sha256')
if sidecar.exists():
    assert sidecar.read_text().split() == [expected, name]
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    members = {line.split('  ', 1)[1]: line.split('  ', 1)[0]
               for line in z.read('evidence/v12.3/manifest.sha256').decode().splitlines()}
    assert len(z.namelist()) == len(set(z.namelist()))
    assert set(z.namelist()) == set(members) | {'evidence/v12.3/manifest.sha256'}
    for path, digest in members.items():
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        assert sha(z.read(path)) == digest, path
    state = json.loads(z.read('evidence/v12.3/validation.json'))
    run = 'evidence/v12.3/runs/' + state['run_id'] + '/'
    assert json.loads(z.read(run + 'validation.json')) == state
    assert state['status'] == 'accepted' and state['reused'] == 0 and state['not_run'] == []
    manifest = json.loads(z.read(run + 'inputs.json'))
    assert sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()) == state['input_fingerprint']
    for path, value in manifest.items():
        assert sha(z.read(path)) == value['sha256'], path
        assert bool((z.getinfo(path).external_attr >> 16) & 0o111) == value['executable'], path
    for path, digest in state['artifacts'].items():
        assert sha(z.read(run + path)) == digest, path
    assert len(state['gates']) == 32 and len({g['gate'] for g in state['gates']}) == 32
    for g in state['gates']:
        assert g == json.loads(z.read(run + g['gate'] + '.json'))
        log = z.read(run + g['gate'] + '.log')
        assert sha(log) == g['log_sha256']
        assert json.loads(log.splitlines()[0]) == {k:g[k] for k in ['policy','run_id','gate','command','input_fingerprint']}
        assert g['run_id'] == state['run_id'] and g['input_fingerprint'] == state['input_fingerprint']
        assert g['exit'] == 0 and g['status'] == 'executed' and log.endswith(b'\nEXIT_STATUS=0\n')
    for path, key in [('bin/view_server','service_sha256'), ('bin/view_server_faults','fault_service_sha256'), ('browser/public/product_core.wasm','wasm_sha256')]:
        assert sha(z.read(path)) == state[key]
    assert b'V121_FAULT_DIR' not in z.read('bin/view_server')
    assert b'V121_FAULT_DIR' in z.read('bin/view_server_faults')
    report = {'status':'verified-integrity-only', 'archive_sha256':expected,
              'members':len(members), 'inputs':len(manifest),
              **{k:state[k] for k in ['run_id','input_fingerprint','service_sha256','fault_service_sha256','wasm_sha256']}}
print(json.dumps(report, indent=2))

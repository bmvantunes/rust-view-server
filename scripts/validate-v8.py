"""Fresh v8 correctness gates, preserving all accepted v7 evidence and artifacts."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile,tempfile,shutil
root=Path(__file__).resolve().parent.parent
evidence=root/'evidence/v8';evidence.mkdir(exist_ok=True)
env=os.environ.copy();env['EVIDENCE_PREFIX']='v8'
prior=json.loads((evidence/'gate-exits.json').read_text()) if '--resume' in sys.argv else []
gates=[]
def run(command,log,cwd=root):
    old=next((g for g in prior if g['command']==command and g['log']==log and g['exit']==0),None)
    if old:
        gates.append(old)
        (evidence/'gate-exits.json').write_text(json.dumps(gates,indent=2)+'\n')
        print(log+': reuse passing gate',flush=True)
        return
    with (root/log).open('w') as f:
        f.write('COMMAND '+json.dumps(command)+'\n');f.flush()
        result=subprocess.run(command,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        f.write('\nEXIT_STATUS='+str(result.returncode)+'\n')
    gates.append({'command':command,'log':log,'exit':result.returncode})
    (evidence/'gate-exits.json').write_text(json.dumps(gates,indent=2)+'\n')
    print(log+': exit '+str(result.returncode),flush=True)
    if result.returncode:raise SystemExit('Gate failed: '+log)
run(['python3','scripts/generate-engine-corpus.py','--check'],'logs/golden-fixture-v8.log')
run(['sh','scripts/ci-native.sh'],'logs/native-ci-v8.log')
run(['sh','scripts/test-ingestion.sh'],'logs/ingestion-v8.log')
run(['python3','scripts/prove-engine-boundary.py'],'logs/engine-boundary-negative-v8.log')
run(['python3','scripts/prove-v7-boundary.py'],'logs/source-boundary-negative-v8.log')
run(['python3','scripts/prove-v8-boundary.py'],'logs/storage-boundary-negative-v8.log')
run(['python3','scripts/audit-v8-licenses.py'],'logs/licenses-v8.log')
run(['sh','scripts/build-wasm.sh'],'logs/wasm-v8.log')
run(['sh','scripts/typecheck-browser.sh'],'logs/typescript-v8.log')
run(['sh','scripts/typecheck-contracts.sh'],'logs/type-contracts-v8.log')
run(['node','scripts/direct-wasm-v5.mjs','.'],'logs/direct-wasm-v8.log')
run(['node','scripts/core-oracle-v5.mjs','.'],'logs/oracle-v8.log')
run(['sh','scripts/test-browser.sh'],'logs/browser-v8.log')
with tempfile.TemporaryDirectory(prefix='v8-distinct-') as temporary:
    work=Path(temporary)
    for tree in ['native','scripts','contract-tests','investigations','fixtures']:
        shutil.copytree(root/tree,work/tree,ignore=shutil.ignore_patterns('target','node_modules','__pycache__'))
    shutil.copy2(root/'clippy.toml',work/'clippy.toml')
    run(['sh','scripts/check-count-distinct.sh'],'logs/distinct-v8-run.log',work)
    run(['python3','scripts/prove-distinct-lint.py'],'logs/distinct-lint-v8-run.log',work)
    destination=root/'logs/v8-distinct';destination.mkdir(exist_ok=True)
    for log in (work/'logs').glob('*.log'):shutil.copy2(log,destination/log.name)
wasm=hashlib.sha256((root/'browser/public/product_core.wasm').read_bytes()).hexdigest()
runtime=json.loads((root/'evidence/v8-browser-runtime.json').read_text());assert runtime['wasmSha256']==wasm

accepted=root/'rust-differential-product-20260929-review-checkpoint-v7.zip';baseline=hashlib.sha256(accepted.read_bytes()).hexdigest();assert baseline=='fb2d8b6601a2ce44d75ffe1bd94803550226e71a5f04e7ce042e25147654260a'
checked=[];changed=[]
with zipfile.ZipFile(accepted) as z:
    assert hashlib.sha256(z.read('browser/public/product_core.wasm')).hexdigest()=='7a86f227b1c7d437e9db127075a982e7590b2f15fc154643261385977ead1da7'
    for info in z.infolist():
        name=info.filename
        if info.is_dir():continue
        preserve=name.startswith(('browser/','investigations/','evidence/','logs/','contract-tests/')) or name in ['clippy.toml','native/src/product_engine/distinct.rs','native/Cargo.lock']
        preserve = preserve and name not in ['browser/public/product_core.wasm','browser/public/product_core.sha256','browser/v5-browser-runtime.json']
        if preserve:
            assert (root/name).read_bytes()==z.read(info),'preserved baseline changed: '+name
            checked.append(name)
        elif (root/name).read_bytes()!=z.read(info):changed.append(name)
(evidence/'preservation.json').write_text(json.dumps({'verified':checked,'intentional_changed_baseline_files':changed},indent=2)+'\n')
summary={'gates':gates,'baseline_sha256':baseline,'wasm_sha256':wasm,'wasm_rebuilt':True,'browser':runtime,'real_kafka':'NOT RUN: mock protocol only; no isolated real broker supplied','crash_matrix':'A-G SIGKILL child processes against real SQLite files; D/E broker boundary uses a synced marker, separately integrated mock broker gate','durability':'SQLite WAL/FULL/fullfsync; logical process crash recovery verified; no arbitrary hardware power-loss certification','deployment':'Same-host processes using the same local database; no independent copies, network filesystem, or distributed cross-host fencing','scope_limit':'Attachment truncates section 24 after canonical retained dataset size still lacks a','linux_msk':'Not executed locally'}
(evidence/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

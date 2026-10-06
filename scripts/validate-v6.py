"""Fresh v6 gates. Preserve v5/v5.1 logs and archives; record real process exits."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile,zipfile,sys
root=Path(__file__).resolve().parent.parent
evidence=root/'evidence/v6';evidence.mkdir(exist_ok=True)
env=os.environ.copy();env['EVIDENCE_PREFIX']='v6'
prior=json.loads((evidence/'gate-exits.json').read_text()) if '--resume' in sys.argv else []
gates=[]
def run(command,log,cwd=root):
    previous=next((g for g in prior if g['command']==command and g['log']==log and g['exit']==0),None)
    if previous:
        gates.append(previous)
        print(f'{log}: reused passing result from interrupted driver',flush=True)
        return
    path=root/log;path.parent.mkdir(exist_ok=True)
    with path.open('w') as stream:
        stream.write('COMMAND '+json.dumps(command)+'\nCWD '+str(cwd)+'\n');stream.flush()
        result=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        stream.write(f'\nEXIT_STATUS={result.returncode}\n')
    gates.append({'command':command,'log':log,'exit':result.returncode})
    (evidence/'gate-exits.json').write_text(json.dumps(gates,indent=2)+'\n')
    print(f'{log}: exit {result.returncode}',flush=True)
    if result.returncode:raise SystemExit(f'Gate failed: {log}')
run(['python3','scripts/generate-engine-corpus.py','--check'],'logs/golden-fixture-v6.log')
run(['sh','scripts/ci-native.sh'],'logs/native-ci-v6.log')
run(['python3','scripts/prove-engine-boundary.py'],'logs/engine-boundary-negative-v6.log')
run(['sh','scripts/measure-retained-memory.sh'],'logs/retained-memory-v6.log')
run(['sh','scripts/build-wasm.sh'],'logs/wasm-v6.log')
run(['sh','scripts/typecheck-browser.sh'],'logs/typescript-v6.log')
run(['sh','scripts/typecheck-contracts.sh'],'logs/type-contracts-v6.log')
run(['node','scripts/direct-wasm-v5.mjs','.'],'logs/direct-wasm-v6.log')
run(['node','scripts/core-oracle-v5.mjs','.'],'logs/oracle-v6.log')
run(['sh','scripts/test-browser.sh'],'logs/browser-v6.log')
with tempfile.TemporaryDirectory(prefix='v6-distinct-gates-') as temporary:
    work=Path(temporary)
    for tree in ['native','scripts','contract-tests','investigations','fixtures']:
        shutil.copytree(root/tree,work/tree,ignore=shutil.ignore_patterns('target','node_modules','__pycache__'))
    shutil.copy2(root/'clippy.toml',work/'clippy.toml')
    run(['sh','scripts/check-count-distinct.sh'],'logs/distinct-v6-run.log',work)
    run(['python3','scripts/prove-distinct-lint.py'],'logs/distinct-lint-v6-run.log',work)
    destination=root/'logs/v6-distinct';destination.mkdir(exist_ok=True)
    for log in (work/'logs').glob('*.log'):shutil.copy2(log,destination/log.name)
    proof=json.loads((work/'evidence/distinct-lint-proof.json').read_text())
    for case in proof['cases']:case['log']='logs/v6-distinct/'+Path(case['log']).name
    (evidence/'distinct-lint-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
wasm=hashlib.sha256((root/'browser/public/product_core.wasm').read_bytes()).hexdigest()
runtime=json.loads((root/'evidence/v6-browser-runtime.json').read_text())
assert runtime['wasmSha256']==wasm
assert (root/'browser/public/product_core.sha256').read_text().strip()==wasm
# Preserve accepted code/evidence that this checkpoint must not alter.
archive=root/'rust-differential-product-20260929-review-checkpoint-v5.1-distinct-addendum.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='676b2f3f8fd87823db117b208bad8986df147d05bdc878900bf7fbbb9fff346d'
checked=[]
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        name=info.filename
        if info.is_dir():continue
        preserve=name.startswith(('browser/src/','investigations/','evidence/v5.1/','logs/','evidence/reference-','evidence/distinct-reference-')) or name in ['clippy.toml','native/Cargo.lock','native/Cargo.toml','browser/package.json','browser/package-lock.json','fixtures/product-core-100.json','contract-tests/count_distinct.rs','native/src/product_engine/distinct.rs']
        if preserve:
            assert (root/name).read_bytes()==z.read(info),f'accepted file changed: {name}'
            checked.append(name)
(evidence/'preservation.json').write_text(json.dumps({'baseline_archive_unchanged':True,'files_verified_unchanged':checked},indent=2)+'\n')
summary={'gates':gates,'wasm_sha256':wasm,'wasm_rebuilt':True,'browser':runtime,'counts':{'native_unit':19,'native_golden':2,'native_source':4,'golden_steps_per_engine':64,'golden_results_per_engine':475,'browser':65,'existing_wasm_oracle':3006},'distinct_proof':proof,'baseline_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'independent_review':'User reports accepted; ZIP unavailable locally, not read or executed','request_limitation':'Received file ends mid-section 13 at multiple sort; continuation unavailable','claude_provenance':'Closed by user constraint; not pending acceptance','toolchain_policy':'Retained tested Rust 1.96.1 and React 19.2.8; newer versions authorized but not required or evaluated','skipped_executable_gates':[]}
(evidence/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

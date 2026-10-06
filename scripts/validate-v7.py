"""Reproducible v7 gates; no production Kafka access. Real-broker gate is explicit."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile,tempfile,shutil
root=Path(__file__).resolve().parent.parent
evidence=root/'evidence/v7';evidence.mkdir(exist_ok=True)
env=os.environ.copy();env['EVIDENCE_PREFIX']='v7'
prior=json.loads((evidence/'gate-exits.json').read_text()) if '--resume' in sys.argv else []
gates=[]
def run(command,log,cwd=root):
    old=next((g for g in prior if g['command']==command and g['log']==log and g['exit']==0),None)
    if old:gates.append(old);print(log+': reuse passing gate',flush=True);return
    with (root/log).open('w') as f:
        f.write('COMMAND '+json.dumps(command)+'\n');f.flush()
        result=subprocess.run(command,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
        f.write('\nEXIT_STATUS='+str(result.returncode)+'\n')
    gates.append({'command':command,'log':log,'exit':result.returncode})
    (evidence/'gate-exits.json').write_text(json.dumps(gates,indent=2)+'\n')
    print(log+': exit '+str(result.returncode),flush=True)
    if result.returncode:raise SystemExit('Gate failed: '+log)
run(['python3','scripts/generate-engine-corpus.py','--check'],'logs/golden-fixture-v7.log')
run(['sh','scripts/ci-native.sh'],'logs/native-ci-v7.log')
run(['sh','scripts/test-ingestion.sh'],'logs/ingestion-final-v7.log')
run(['python3','scripts/prove-engine-boundary.py'],'logs/engine-boundary-negative-v7.log')
run(['python3','scripts/prove-v7-boundary.py'],'logs/source-boundary-negative-v7.log')
run(['python3','scripts/audit-v7-licenses.py'],'logs/licenses-v7.log')
run(['sh','scripts/build-wasm.sh'],'logs/wasm-v7.log')
run(['sh','scripts/typecheck-browser.sh'],'logs/typescript-v7.log')
run(['sh','scripts/typecheck-contracts.sh'],'logs/type-contracts-v7.log')
run(['node','scripts/direct-wasm-v5.mjs','.'],'logs/direct-wasm-v7.log')
run(['node','scripts/core-oracle-v5.mjs','.'],'logs/oracle-v7.log')
run(['sh','scripts/test-browser.sh'],'logs/browser-v7.log')
with tempfile.TemporaryDirectory(prefix='v7-distinct-') as temporary:
    work=Path(temporary)
    for tree in ['native','scripts','contract-tests','investigations','fixtures']:
        shutil.copytree(root/tree,work/tree,ignore=shutil.ignore_patterns('target','node_modules','__pycache__'))
    shutil.copy2(root/'clippy.toml',work/'clippy.toml')
    run(['sh','scripts/check-count-distinct.sh'],'logs/distinct-v7-run.log',work)
    run(['python3','scripts/prove-distinct-lint.py'],'logs/distinct-lint-v7-run.log',work)
    destination=root/'logs/v7-distinct';destination.mkdir(exist_ok=True)
    for log in (work/'logs').glob('*.log'):shutil.copy2(log,destination/log.name)
wasm=hashlib.sha256((root/'browser/public/product_core.wasm').read_bytes()).hexdigest()
runtime=json.loads((root/'evidence/v7-browser-runtime.json').read_text());assert runtime['wasmSha256']==wasm
accepted=root/'rust-differential-product-20260929-review-checkpoint-v6.zip';baseline=hashlib.sha256(accepted.read_bytes()).hexdigest();assert baseline=='bd971adf671a7c25eb59d577e98fb80b87aca943a8086112593f53b0675d53d4'
checked=[];changed=[]
with zipfile.ZipFile(accepted) as z:
    for info in z.infolist():
        name=info.filename
        if info.is_dir():continue
        preserve=name.startswith(('browser/src/','investigations/','evidence/','logs/','contract-tests/')) or name in ['clippy.toml','native/src/product_engine/distinct.rs','browser/package.json','browser/package-lock.json']
        if preserve:
            assert (root/name).read_bytes()==z.read(info),'preserved baseline changed: '+name
            checked.append(name)
        elif (root/name).read_bytes()!=z.read(info):changed.append(name)
(evidence/'preservation.json').write_text(json.dumps({'verified':checked,'intentional_changed_baseline_files':changed},indent=2)+'\n')
summary={'gates':gates,'baseline_sha256':baseline,'wasm_sha256':wasm,'wasm_rebuilt':True,'browser':runtime,'real_kafka':'NOT RUN: Docker daemon unavailable; no isolated external broker supplied','librdkafka_mock':'Executed separately; not real-broker evidence','independent_v6_review':'Requested ZIP unavailable locally; user-reported acceptance retained','scope_limit':'Request ends in section 19 at Do not automatically add arbitrary','durability':'Contract/model only; no production durable backend, no in-memory Kafka commits','linux_msk':'Not executed locally'}
(evidence/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

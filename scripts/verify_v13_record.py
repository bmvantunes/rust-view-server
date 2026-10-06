"""Additional V13 bindings; the original 34 gate checks remain in acceptance_v13."""
import hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check(root,evidence,run_id=None):
    builds=read(evidence/'candidate-builds.json')
    assert [b['codec'] for b in builds['candidates']]==['json','protobuf','msgpack']
    by_codec={b['codec']:b for b in builds['candidates']}
    admission=read(evidence/'query-admission.json');assert admission['status']=='passed'
    qualification=read(evidence/'candidate-qualification.json')
    assert qualification['status']=='passed'
    if run_id:
        assert qualification['run_id']==run_id and builds['run_id']==run_id
    sockets=read(evidence/'native-sockets.json')
    assert sockets['status']=='passed' and len(sockets['records'])==3 and all(r['exit']==0 for r in sockets['records'])
    lifetimes=read(evidence/'lifecycles.json')
    assert lifetimes['status']=='passed' and len(lifetimes['records'])==15 and all(r['exit']==0 for r in lifetimes['records'])
    for codec,b in by_codec.items():
        for name in ['row-browser','integer-browser','exact-values','barriers','browser-profile']:
            result=read(evidence/'lifecycle'/codec/(name+'.json'))
            assert result['status']=='passed' and result['release_binary_sha256']==b['sha256']['bin/view_server']
            if run_id:assert result['run_id']==run_id
            if name=='barriers':assert result['fault_binary_sha256']==b['sha256']['bin/view_server_faults']
        protocol=read(evidence/('protocol-'+codec+'.json'))
        assert protocol['status']=='passed' and protocol['source_sha256']==b['sha256']['browser/src/product.remote.worker.ts']
    semantics=read(evidence/'semantic-family.json')
    assert semantics['fixedPairs']==280 and semantics['canonicalNoops']==280 and semantics['poisonRejected']==560
    assert semantics['wasm_sha256']==sha(root/'browser/public/product_core.wasm')
    if run_id:assert semantics['run_id']==run_id
    codecs=read(evidence/'codecs.json')
    assert codecs['status']=='passed' and codecs['crossLanguagePairs']>=70 and codecs['hostileRejectedBothLanguages']>=175
    if run_id:assert codecs['run_id']==run_id
    measurement=read(evidence/'measurement-verification.json')
    assert measurement['status']=='verified' and len(measurement['records'])==75
    assert measurement['rule_sha256']==sha(root/'CODEC-DECISION-RULE.md')
    for record in measurement['records']:
        path=root/'evidence/v13'/record['name'];assert sha(path)==record['raw_sha256']
        raw=read(path);b=by_codec[raw['codec']]
        assert raw['release_binary_sha256']==b['sha256']['bin/view_server']
        for p,h in raw['source_hashes'].items():
            if p in b['sha256']:assert h==b['sha256'][p],p
            else:assert h==sha(root/p),p
    phase=read(root/'evidence/v13/phase-measurements.json')
    assert phase['status']=='passed' and len(phase['records'])==70 and phase['processes']==5
    assert phase['binary_sha256']==codecs['binary_sha256']
    assert phase['harness_sha256']==sha(root/'scripts/profile-v13-phases.mjs')
    assert phase['rule_sha256']==sha(root/'CODEC-DECISION-RULE.md')
    assert all(len(r['samples'])==100 for r in phase['records'])
    return {'status':'verified','run_id':run_id,'decision':measurement['decision'],'measurements':75,'lifecycleExecutions':15,'socketCandidates':3,'workerCandidates':3}

def verify_extra(root,state,run):
    result=check(root,run/'generated/evidence/v13',state['run_id'])
    assert result==read(run/'generated/evidence/v13/evidence-binding.json')
    browser={p:sha(root/p) for p in ['browser/src/product.remote.worker.ts','browser/src/product-provider.tsx','browser/src/product.worker.ts','browser/pnpm-lock.yaml']}
    assert state['browser_sha256']==browser

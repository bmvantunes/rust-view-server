"""Additional V13 bindings; the original 34 gate checks remain in acceptance_v131."""
import hashlib,json,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def bind_measurement_sources(root, raw, rebuilt, measured):
    # Runtime artifacts bind to the exact measured image, while source/lock
    # identities bind to the fresh build. Rebuilt WASM is verified separately
    # against the fresh admission unit and production/candidate executions.
    for name, h in raw['source_hashes'].items():
        if name == 'browser/public/request_admission.wasm':
            assert h == measured['sha256'][name], name
        elif name in rebuilt['sha256']:
            assert h == rebuilt['sha256'][name], name
        else:
            assert h == sha(root/name), name

def check(root,evidence,run_id=None):
    # Candidates use the sealed V12.4 native product. The admission WASM built
    # at the acceptance root must use those same authoritative product types.
    with zipfile.ZipFile(root/'rust-differential-product-20260929-review-checkpoint-v12.4.zip') as archive:
        for name in archive.namelist():
            if name.startswith('native/') and (name.endswith('.rs') or name.endswith(('Cargo.toml','Cargo.lock'))):
                assert (root/name).read_bytes()==archive.read(name),name
    builds=read(evidence/'candidate-builds.json')
    assert [b['codec'] for b in builds['candidates']]==['json','protobuf','msgpack']
    by_codec={b['codec']:b for b in builds['candidates']}
    admission=read(evidence/'query-admission.json');assert admission['status']=='passed'
    admission_unit=read(evidence/'admission-unit.json')
    assert admission_unit['status']=='passed' and admission_unit['wasm_sha256']==sha(root/'browser/public/request_admission.wasm')
    qualification=read(evidence/'candidate-qualification.json')
    assert qualification['status']=='passed'
    if run_id:
        assert qualification['run_id']==run_id and builds['run_id']==run_id
    isolation=read(evidence/'source-isolation.json')
    assert isolation['status']=='passed' and len(isolation['records'])==3
    assert isolation['test_sha256']==sha(root/'experiments/v131/source-recursion.rs')
    if run_id:assert isolation['run_id']==run_id
    sockets=read(evidence/'native-sockets.json')
    assert sockets['status']=='passed' and len(sockets['records'])==3 and all(r['exit']==0 for r in sockets['records'])
    lifetimes=read(evidence/'lifecycles.json')
    assert lifetimes['status']=='passed' and len(lifetimes['records'])==15 and all(r['exit']==0 for r in lifetimes['records'])
    for codec,b in by_codec.items():
        if codec!='json':assert b['sha256']['browser/public/request_admission.wasm']==admission_unit['wasm_sha256']
        for name in ['row-browser','integer-browser','exact-values','barriers','browser-profile']:
            result=read(evidence/'lifecycle'/codec/(name+'.json'))
            assert result['status']=='passed' and result['release_binary_sha256']==b['sha256']['bin/view_server']
            if run_id:assert result['run_id']==run_id
            if name=='barriers':assert result['fault_binary_sha256']==b['sha256']['bin/view_server_faults']
        protocol=read(evidence/('protocol-'+codec+'.json'))
        assert protocol['status']=='passed' and protocol['source_sha256']==b['sha256']['browser/src/product.remote.worker.ts']
    for codec in by_codec:
        lifetimes=read(evidence/('admission-lifetimes-'+codec+'.json'));assert lifetimes['status']=='passed' and lifetimes['finalZeroSubscriptions']
        boundary=read(evidence/('query-admission-'+codec+'.json'));assert boundary['status']=='passed' and all(c['correct'] for c in boundary['cases']) and len(boundary['terminal'])==2
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
    frozen=read(root/'evidence/v13.1/measured-artifacts/index.json')
    measured={b['codec']:b for b in frozen['candidates']}
    for b in measured.values():
        for name,h in b['sha256'].items():assert sha(root/'evidence/v13.1/measured-artifacts'/b['codec']/name)==h
    for record in measurement['records']:
        path=root/'evidence/v13.1'/record['name'];assert sha(path)==record['raw_sha256']
        raw=read(path);b=by_codec[raw['codec']]
        assert raw['release_binary_sha256']==measured[raw['codec']]['sha256']['bin/view_server']
        bind_measurement_sources(root,raw,b,measured[raw['codec']])
    phase=read(root/'evidence/v13.1/phase-measurements.json')
    assert phase['status']=='passed' and len(phase['records'])==70 and phase['processes']==5
    assert phase['binary_sha256']==frozen['phase_codec_sha256']==sha(root/'evidence/v13.1/measured-artifacts/phase-codec-runner')
    assert phase['harness_sha256']==sha(root/'scripts/profile-v131-phases.mjs')
    assert phase['rule_sha256']==sha(root/'CODEC-DECISION-RULE.md')
    assert all(len(r['samples'])==100 for r in phase['records'])
    production=read(evidence/'production-selection.json');assert production['status']=='passed' and production['decision']==measurement['decision']
    if run_id:assert production['run_id']==run_id
    if measurement['decision']!='inconclusive':
        assert production['ordinary_sha256']==sha(root/'bin/view_server')
        assert production['fault_sha256']==sha(root/'bin/view_server_faults')
        assert production['admission_wasm_sha256']==sha(root/'browser/public/request_admission.wasm')
    return {'status':'verified','run_id':run_id,'decision':measurement['decision'],'measurements':75,'lifecycleExecutions':15,'socketCandidates':3,'workerCandidates':3}

def verify_extra(root,state,run):
    result=check(root,run/'generated/evidence/v13.1',state['run_id'])
    assert result==read(run/'generated/evidence/v13.1/evidence-binding.json')
    browser={p:sha(root/p) for p in ['browser/src/product.remote.worker.ts','browser/src/product-provider.tsx','browser/src/product.worker.ts','browser/pnpm-lock.yaml']}
    assert state['browser_sha256']==browser

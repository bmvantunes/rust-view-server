from pathlib import Path
import json,subprocess,os,hashlib,zipfile
r=Path(__file__).resolve().parent.parent;e=r/'evidence/v13.1'
read=lambda p:json.loads(p.read_text())
m=read(e/'measurement-verification.json');assert m['eligible']
if m['decision']=='inconclusive':
 assert not (r/'PRODUCTION-CODEC.json').exists()
 with zipfile.ZipFile(r/'rust-differential-product-20260929-review-checkpoint-v12.4.zip') as z:
  for name in ['ingestion/Cargo.toml','ingestion/Cargo.lock','ingestion/src/bin/view_server.rs','browser/src/product.remote.worker.ts','browser/src/product-provider.tsx','browser/src/product.worker.ts']:
   assert (r/name).read_bytes()==z.read(name),'Unjustified production change: '+name
 report={'status':'passed','decision':'inconclusive','production':'unchanged V12.4 JSON','binary_path':'not applicable: no winner','run_id':os.environ.get('ACCEPTANCE_RUN_ID')}
else:
 selection=read(r/'PRODUCTION-CODEC.json');codec=selection['codec'];assert codec==m['decision']
 assert selection['measurement_report_sha256']==hashlib.sha256((e/'measurement-verification.json').read_bytes()).hexdigest()
 env=dict(os.environ,V13_CANDIDATE_ROOT=str(r),V13_CODEC=codec,V131_EVIDENCE_PREFIX='production-')
 for command in [['node','scripts/test-v131-production.mjs'],['node','scripts/test-v131-admission-lifetimes.mjs'],['node','scripts/test-v131-query-admission.mjs']]:subprocess.run(command,cwd=r,env=env,check=True)
 # The wire crate must activate only its chosen codec. Existing source ingestion
 # separately uses prost and must remain unchanged by this WebSocket task.
 rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
 graph=json.loads(subprocess.check_output(['rustup','run','1.96.1','cargo','metadata','--locked','--offline','--format-version','1','--manifest-path','ingestion/Cargo.toml','--features','kafka-tls'],cwd=r,env=dict(os.environ,RUSTC=rustc)))
 packages={p['id']:p['name'] for p in graph['packages']};resolved={packages[n['id']] for n in graph['resolve']['nodes']}
 wire=next(n for n in graph['resolve']['nodes'] if packages[n['id']]=='v13-codec-experiment')
 assert wire['features']==[codec]
 wire_dependencies={packages[d['pkg']] for d in wire['deps']}
 assert ('view-wire-prost' not in wire_dependencies if codec=='msgpack' else 'rmpv' not in wire_dependencies)
 source=next(n for n in graph['resolve']['nodes'] if packages[n['id']]=='prost')
 assert 'no-recursion-limit' not in source['features']
 report={'status':'passed','decision':codec,'production':'single binary codec; no JSON application fallback','ordinary_sha256':hashlib.sha256((r/'bin/view_server').read_bytes()).hexdigest(),'fault_sha256':hashlib.sha256((r/'bin/view_server_faults').read_bytes()).hexdigest(),'admission_wasm_sha256':hashlib.sha256((r/'browser/public/request_admission.wasm').read_bytes()).hexdigest(),'resolved_native_packages':sorted(resolved),'wire_features':wire['features'],'wire_dependencies':sorted(wire_dependencies),'existing_source_protobuf_decoder_unchanged':True,'run_id':os.environ.get('ACCEPTANCE_RUN_ID')}
(e/'production-selection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

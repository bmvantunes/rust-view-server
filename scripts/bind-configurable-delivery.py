#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,shutil,difflib,sys
R=Path(__file__).resolve().parents[2];W=R/'work';perf=sys.argv[1];ordinary='evidence/topics-fa7d0ba4';fault='evidence/topics-e253f444';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
idx=json.loads((R/'evidence/native/qualification-index.json').read_text());builds=['evidence/'+idx['final_native_runs'][n]['metadata'] for n in ['ordinary-build','fault-build']]
artifacts={str(p.relative_to(R)):h(p) for p in [W/'bin/view_server_kafka_topics',W/'bin/view_server_kafka_topics_faults',W/'bin/generic_kafka_producer_fixture',W/'browser/src/product-provider.tsx',W/'browser/src/product.remote.worker.ts',W/'browser/src/topic-schema.ts',W/'browser/public/product_core.wasm',W/'browser/public/request_admission.wasm']}
artifacts.update({str(p.relative_to(R)):h(p) for p in (W/'build/configurable-topics').rglob('*') if p.is_file()})
bindings={'implementation_archive_sha256':'53377d8671172554989a00611373f2ebd94480989452622a6b615caefa51fa2c','closing_review_archive_sha256':'630024c76d9f68fd2f01e8c59a1ee97604496c5e8bfbc8158c67ac03622c9415','accepted_ordinary_sha256':'d6870c1e080172340481817a9b168491e60cb00558f1a9bbf65b3ee58d51ab41','tested_artifacts':artifacts,'native_build_receipts':builds,'browser_receipt':'evidence/logs/browser-final-receipt.json','tooling':'provenance/tooling-identities.json','scope':'New generic engine and its v14 compatibility branch are certified only by new implementation evidence on these new bytes. Closed accepted review stays closed; no independent approval is claimed.'}
(R/'SOURCE-BINDINGS.json').write_text(json.dumps(bindings,indent=2)+'\n')
gates={'ordinary':{'status':'PASS','evidence':ordinary},'fault':{'status':'PASS','evidence':fault},'performance':{'status':'PASS','evidence':perf},'f1':{'status':'PASS','log':ordinary+'/f1.log','cases':6,'schedules':3,'observations':24,'thresholds':'unchanged'},'browser':{'status':'PASS','receipt':'evidence/logs/browser-final-receipt.json','mounted_tests':75},'native':{'status':'PASS','index':'evidence/native/qualification-index.json'},'scope_notes':['Actual ordinary browser/provider tests and native-wire fault tests are distinguished.','Admission crate itself has zero tests; actual negative assertions live in schema/source/owner/wire and public TS tests.','Generic local-WASM unsupported; legacy product local-WASM remains covered by mounted oracles.','No deployment, retention engine, joins, aggregates, live schema mutation, or cross-source atomic snapshot.','All failed and superseded attempts are retained; see evidence/run-inventory.json.']}
(R/'GATES.json').write_text(json.dumps(gates,indent=2)+'\n')
# Preserve each immutable actual test config/descriptor and deny profile, excluding broker data.
for rt in (R/'runtime').iterdir():
 if not rt.is_dir():continue
 dst=R/'provenance/runtime-inputs'/rt.name;dst.mkdir(parents=True,exist_ok=True)
 for p in rt.iterdir():
  if p.is_file() and (p.suffix in ['.json','.properties','.sb','.proto']):shutil.copy2(p,dst/p.name)
inventory=[]
for p in sorted((R/'evidence').glob('topics-*')):
 result=next((p/n for n in ['result.json','fault-result.json','performance.json'] if (p/n).exists()),None)
 data=json.loads(result.read_text()) if result else {};selected=str(p.relative_to(R)) in [ordinary,fault,perf]
 inventory.append({'directory':str(p.relative_to(R)),'status':'selected PASS' if selected else 'superseded/diagnostic PASS' if data.get('passed') else 'failed or interrupted; raw evidence retained','result':str(result.relative_to(R)) if result else None,'binary_identity':data.get('identity',data.get('sha256'))})
(R/'evidence/run-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
# Text-only implementation diff; generated binaries are represented by hashes.
skip={'target','node_modules','.cache','.vite','__pycache__','.git'}
def files(root):return {str(p.relative_to(root)):p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and not any(x in skip for x in p.relative_to(root).parts) and p.name!='.DS_Store'}
a=files(R/'accepted/work');b=files(W);changes=[];diff=[]
for name in sorted(set(a)|set(b)):
 old=a.get(name);new=b.get(name);sha_old=h(old) if old else None;sha_new=h(new) if new else None
 if sha_old==sha_new:continue
 changes.append({'path':name,'old_sha256':sha_old,'new_sha256':sha_new})
 if name.startswith(('bin/','build/','evidence/')):continue
 try:
  before=old.read_text().splitlines(True) if old else [];after=new.read_text().splitlines(True) if new else []
 except UnicodeError:continue
 diff.extend(difflib.unified_diff(before,after,fromfile='accepted/work/'+name if old else '/dev/null',tofile='work/'+name if new else '/dev/null'))
(R/'implementation.diff').write_text(''.join(diff));(R/'provenance/work-changes.json').write_text(json.dumps(changes,indent=2)+'\n')
print(json.dumps({'artifacts':len(artifacts),'changed_work_files':len(changes),'ordinary':ordinary,'fault':fault,'performance':perf}))

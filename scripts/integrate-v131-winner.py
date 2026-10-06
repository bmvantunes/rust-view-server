"""Install only a correctness-qualified winner of the immutable fresh comparison."""
from pathlib import Path
import json,shutil,hashlib
r=Path(__file__).resolve().parent.parent;e=r/'evidence/v13.1'
read=lambda p:json.loads(p.read_text())
report=read(e/'measurement-verification.json');assert report['eligible'] and report['status']=='verified'
assert read(e/'candidate-qualification.json')['status']=='passed'
codec=report['decision'];assert codec in ['protobuf','msgpack'],'No justified binary winner; leave production unchanged'
assert not (r/'PRODUCTION-CODEC.json').exists(),'Do not reintegrate an existing selection'
b=next(b for b in read(e/'candidate-builds.json')['candidates'] if b['codec']==codec);source=Path(b['root'])
for name,h in b['sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h,(name,'candidate changed')
files=['ingestion/Cargo.toml','ingestion/Cargo.lock','ingestion/src/bin/view_server.rs','ingestion/tests/v12_socket.rs','ingestion/tests/v131_source_recursion.rs','browser/src/product.remote.worker.ts','browser/src/v12-harness.tsx','browser/src/request-admission.ts','browser/public/request_admission.wasm','bin/view_server','bin/view_server_faults']
for name in files:shutil.copy2(source/name,r/name)
# Preserve the 34 acceptance commands. Adapt only their transport wiring to the selected production peer.
p=r/'scripts/v124-browser-support.mjs';p.write_text(p.read_text().replace(':${ws}/v12',':${ws}/v13'))
p=r/'scripts/test-v124-legacy-remote.mjs';p.write_text(p.read_text().replace(':${ws}/v12',':${ws}/v13'))
p=r/'scripts/test-v124-protocol.mjs';original=p.read_text();p.write_text('''// V13.1: the preserved command runs the expanded actual binary Worker schedules.
import {copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
process.env.V13_CANDIDATE_ROOT=resolve(import.meta.dirname,'..');
process.env.V13_CODEC='''+repr(codec)+''';
await import('./test-v131-protocol.mjs');
await copyFile(new URL('../evidence/v13.1/protocol-'''+codec+'''.json',import.meta.url),new URL('../evidence/v12.4/protocol.json',import.meta.url));
''')
# The separate evaluator WASM build remains unchanged; build the admission ABI before remote gates.
p=r/'scripts/build-wasm-v124.py'
if 'scripts/build-v131-codec.py' not in p.read_text():p.write_text(p.read_text()+'''
# Admission-only module required by the selected remote Worker (no evaluator instance).
subprocess.run(['python3','scripts/build-v131-codec.py'],cwd=root,check=True)
''')
selection={'checkpoint':'V13.1','codec':codec,'protocol':13,'path':'/v13','subprotocol':'view-server.v13.'+codec,'decision_rule_sha256':report['rule_sha256'],'measurement_report_sha256':hashlib.sha256((e/'measurement-verification.json').read_bytes()).hexdigest(),'single_codec':True,'json_application_fallback':False,'local_wasm_separate':True}
(r/'PRODUCTION-CODEC.json').write_text(json.dumps(selection,indent=2)+'\n')
print(json.dumps(selection))

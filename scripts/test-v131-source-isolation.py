"""The existing source decoder must retain its default recursion guard in every peer."""
from pathlib import Path
import os,json,subprocess,tempfile,hashlib
r=Path(__file__).resolve().parent.parent;e=r/'evidence/v13.1';records=[]
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
for b in json.loads((e/'candidate-builds.json').read_text())['candidates']:
 env=dict(os.environ,RUSTC=rustc,RUSTDOC=str(Path(rustc).with_name('rustdoc')),CARGO_INCREMENTAL='0',CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'rust-product-v7-target'))
 meta=json.loads(subprocess.check_output(['rustup','run','1.96.1','cargo','metadata','--locked','--offline','--format-version','1','--manifest-path','ingestion/Cargo.toml'],cwd=b['root'],env=env))
 source=next(p for p in meta['packages'] if p['name']=='prost' and p['source'] is not None)
 source_node=next(n for n in meta['resolve']['nodes'] if n['id']==source['id'])
 assert 'no-recursion-limit' not in source_node['features'],source_node
 wire=next((p for p in meta['packages'] if p['name']=='view-wire-prost'),None)
 if b['codec']=='protobuf':
  assert wire and wire['id']!=source['id']
  assert 'no-recursion-limit' in next(n for n in meta['resolve']['nodes'] if n['id']==wire['id'])['features']
 else:assert wire is None
 cmd=['rustup','run','1.96.1','cargo','test','--locked','--offline','--manifest-path','ingestion/Cargo.toml','--features','kafka-tls','--test','v131_source_recursion','--','--nocapture']
 with (e/('source-isolation-'+b['codec']+'.log')).open('w') as f:process=subprocess.run(cmd,cwd=b['root'],env=env,stdout=f,stderr=subprocess.STDOUT)
 assert process.returncode==0,b['codec']
 records.append({'codec':b['codec'],'command':cmd,'exit':process.returncode,'source_decoder':source_node,'wire_package':wire['id'] if wire else None})
(e/'source-isolation.json').write_text(json.dumps({'status':'passed','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'test_sha256':hashlib.sha256((r/'experiments/v131/source-recursion.rs').read_bytes()).hexdigest(),'accepted_depths':[0,99,100],'rejected_depths':[101,120],'records':records},indent=2)+'\n')
print('PASS source recursion guard in all three peers')

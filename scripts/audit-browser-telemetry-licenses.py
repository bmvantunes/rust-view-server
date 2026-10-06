from pathlib import Path
import json,hashlib,shutil
root=Path(__file__).resolve().parent.parent;modules=root/'browser/node_modules';seen={}
def visit(base):
 base=base.resolve();p=json.loads((base/'package.json').read_text());key=p['name']+'@'+p['version']
 if key in seen:return
 assert p.get('license') in ['Apache-2.0','MIT','BSD-3-Clause','ISC'],(key,p.get('license'))
 entry={'name':p['name'],'version':p['version'],'license':p['license'],'dependencies':p.get('dependencies',{}),'peers':p.get('peerDependencies',{}),'notices':[]};seen[key]=entry
 for f in base.iterdir():
  if f.is_file() and f.name.upper().startswith(('LICENSE','NOTICE','COPYING')):
   target=root/'evidence/runtime-health/browser-licenses'/key.replace('/','-')/f.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target);entry['notices'].append({'path':str(target.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 assert entry['notices'],key
 for name in p.get('dependencies',{}):
  candidates=[a/'node_modules'/name for a in [base,*base.parents]]+[modules/name]
  target=next((c for c in candidates if (c/'package.json').is_file()),None);assert target,(key,name);visit(target)
for name in json.loads((root/'browser/package.json').read_text())['dependencies']:visit(modules/name)
(root/'evidence/runtime-health/browser-licenses.json').write_text(json.dumps({'scope':'new browser OTel runtime dependency closure; unchanged build/test dependency licenses remain inherited, not claimed all-permissive','packages':seen},indent=2));print('PASS',len(seen),'runtime packages with preserved permissive notices')

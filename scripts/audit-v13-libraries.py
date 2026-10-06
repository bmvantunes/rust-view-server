"""Pinned resolved experiment dependency graph and permissive-license inventory."""
from pathlib import Path
import json,subprocess,hashlib,os,re,shutil
r=Path(__file__).resolve().parent.parent;exp=r/'experiments/v13';allowed={'MIT','ISC','BSD-2-Clause','BSD-3-Clause','Apache-2.0','Unicode-3.0','Python-2.0','Unlicense'}
meta=json.loads(subprocess.check_output(['rustup','run','1.96.1','cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',str(exp/'codec/Cargo.toml')]))
packages=[]
for p in meta['packages']:
 if p['source'] is not None:assert any(x.strip() in allowed for x in re.split(r' OR |/| AND ',p['license'] or '')),(p['name'],p['license'])
 for f in Path(p['manifest_path']).parent.iterdir():
  if p['source'] is not None and f.is_file() and f.name.upper().startswith(('LICENSE','NOTICE','COPYING')):
   target=exp/'licenses/rust'/(p['name']+'-'+p['version'])/f.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 packages.append({'ecosystem':'rust','name':p['name'],'version':p['version'],'license':p['license'],'id':p['id']})
lock=json.loads((exp/'package-lock.json').read_text());notices={}
for path,p in lock['packages'].items():
 if not path:continue
 base=exp/path;manifest=json.loads((base/'package.json').read_text());license=manifest.get('license',p.get('license'))
 assert license in allowed,(path,license)
 files=[f for f in base.iterdir() if f.is_file() and f.name.upper().startswith(('LICENSE','COPYING','NOTICE'))]
 for f in files:
  notices[str(f.relative_to(exp))]=hashlib.sha256(f.read_bytes()).hexdigest();target=exp/'licenses/npm'/manifest['name']/f.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 packages.append({'ecosystem':'npm','name':manifest['name'],'version':manifest['version'],'license':license,'integrity':p.get('integrity')})
report={'status':'passed','packages':packages,'rust_graph':meta['resolve']['nodes'],'npm_graph':lock,'notice_sha256':notices,'primary_sources':['https://docs.rs/prost/0.14.4/prost/','https://docs.rs/rmpv/1.3.1/rmpv/','https://github.com/msgpack/msgpack-javascript','https://github.com/protobufjs/protobuf.js'], 'additional_permissive_license':'Python-2.0 occurs only in argparse through the pinned development code generator. Preserve its full license; markdown-it-anchor uses Unlicense through the development generator; preserve its full notice too. No copyleft branch is introduced.', 'configuration':{'msgpack-js':'3.1.3 useBigInt64=false; exact integers extension42; decoder length caps and common structural preflight','protobufjs':'8.8.0 static module generated with CLI2.7.0; safe metadata checked before Number; exact bytes never Number','rust':'prost0.14.4 / rmpv1.3.1; input structural preflight before allocation/decode; max depth32'}}
(r/'evidence/v13/libraries.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',len(packages),'resolved packages')

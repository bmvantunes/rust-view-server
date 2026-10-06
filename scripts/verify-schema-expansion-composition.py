#!/usr/bin/env python3
"""Verify exact accepted inputs and complete schema overlay; no migration/overwrite."""
from pathlib import Path,PurePosixPath
import argparse,zipfile,hashlib,json
sha=lambda b:hashlib.sha256(b).hexdigest()
def safe(n):
 p=PurePosixPath(n)
 if p.is_absolute()or'..'in p.parts:raise ValueError('unsafe member '+n)
def manifest(z,prefix,name):
 lines=z.read(prefix+name).decode().splitlines();m={n:h for h,n in(line.split('  ',1)for line in lines)}
 assert {n[len(prefix):]for n in z.namelist()if not n.endswith('/')}==set(m)|{name},'manifest coverage'
 for n,h in m.items():safe(n);assert sha(z.read(prefix+n))==h,n
 return m
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--retention',required=True);p.add_argument('--expansion',required=True);p.add_argument('--dest',required=True);a=p.parse_args();dest=Path(a.dest)
assert dest.name=='work'and not dest.exists(),'new destination ending in work required'
with zipfile.ZipFile(a.expansion)as expansion:
 prefix='schema-expansion-v1/';manifest(expansion,prefix,'FILES.sha256');c=json.loads(expansion.read(prefix+'COMPOSITION.json'))
 assert sha(Path(a.base).read_bytes())==c['accepted_base_sha256'];assert sha(Path(a.retention).read_bytes())==c['retention_overlay_sha256']
 with zipfile.ZipFile(a.base)as base:
  manifest(base,'','MANIFEST.sha256');files={i.filename[5:]:base.read(i)for i in base.infolist()if i.filename.startswith('work/')and not i.is_dir()};modes={i.filename[5:]:(i.external_attr>>16)&0o777 for i in base.infolist()if i.filename.startswith('work/')and not i.is_dir()}
 with zipfile.ZipFile(a.retention)as retention:
  rp='topic-retention-v1.1/';manifest(retention,rp,'FILES.sha256');r=json.loads(retention.read(rp+'COMPOSITION.json'))
  for n in r['project_files']:files[n]=retention.read(rp+n);modes[n]=(retention.getinfo(rp+n).external_attr>>16)&0o777
  assert all(sha(files[n])==h for n,h in r['merged_source_artifact_sha256'].items()),'retention composition'
 for n,h in c['changed_project_files'].items():safe(n);b=expansion.read(prefix+'work/'+n);assert sha(b)==h;files[n]=b;modes[n]=(expansion.getinfo(prefix+'work/'+n).external_attr>>16)&0o777
 def project(n):return n.split('/')[0]!='evidence'and not any(v in PurePosixPath(n).parts for v in ['target','node_modules','.cache','__pycache__','.vitest-attachments','__screenshots__'])
 assert {n:sha(b)for n,b in files.items()if project(n)}==c['composed_project_sha256'],'complete composed inventory'
 dest.mkdir(parents=True)
 for n,b in files.items():safe(n);out=dest/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b);out.chmod(modes[n]or 0o644)
 print(json.dumps({'status':'PASS','files':len(files),'project_files':len(c['composed_project_sha256']),'destination':str(dest),'expansion_sha256':sha(Path(a.expansion).read_bytes())},indent=2))

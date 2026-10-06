#!/usr/bin/env python3
"""Verify sparse overlay coverage and compose a new, exact project from sealed inputs."""
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath

def sha(data):return hashlib.sha256(data).hexdigest()
def safe(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError('unsafe member '+name)
 return p

def project_path(name):
 p=PurePosixPath(name)
 return p.parts[0]!='evidence' and not any(v in p.parts for v in ['target','node_modules','.cache','__pycache__','.vitest-attachments'])

def main():
 a=argparse.ArgumentParser();a.add_argument('--base',required=True);a.add_argument('--overlay',required=True);a.add_argument('--dest',required=True);v=a.parse_args();dest=Path(v.dest)
 if dest.name!='work':raise SystemExit('Destination must end in work, matching the project-relative runner layout.')
 if dest.exists():raise SystemExit('Destination must not exist; composition never overwrites a checkout.')
 with zipfile.ZipFile(v.overlay) as overlay:
  prefix='topic-retention-v1.1/';receipt=json.loads(overlay.read(prefix+'COMPOSITION.json'))
  assert sha(Path(v.base).read_bytes())==receipt['base_sha256'],'base archive identity mismatch'
  manifest={line.split('  ',1)[1]:line.split('  ',1)[0] for line in overlay.read(prefix+'FILES.sha256').decode().splitlines()}
  names={n[len(prefix):] for n in overlay.namelist() if not n.endswith('/')}
  assert names==set(manifest)|{'FILES.sha256'},'overlay manifest coverage mismatch'
  for rel,digest in manifest.items():safe(rel);assert sha(overlay.read(prefix+rel))==digest,rel
  composed={};modes={}
  with zipfile.ZipFile(v.base) as base:
   for info in base.infolist():
    if not info.filename.startswith('work/') or info.is_dir():continue
    rel=info.filename[5:];safe(rel);composed[rel]=base.read(info);modes[rel]=(info.external_attr>>16)&0o777
  for rel in receipt['project_files']:
   safe(rel);assert rel in manifest
   composed[rel]=overlay.read(prefix+rel);modes[rel]=(overlay.getinfo(prefix+rel).external_attr>>16)&0o777
  coverage={rel:sha(data) for rel,data in composed.items() if project_path(rel)}
  assert coverage==receipt['merged_source_artifact_sha256'],'merged source/artifact coverage or bytes differ'
  dest.mkdir(parents=True)
  for rel,data in composed.items():
   out=dest/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);out.chmod(modes[rel] or 0o644)
  print(json.dumps({'status':'PASS','destination':str(dest),'merged_files':len(composed),'source_artifact_files':len(coverage),'base_sha256':receipt['base_sha256'],'overlay_sha256':sha(Path(v.overlay).read_bytes())},indent=2))
if __name__=='__main__':main()

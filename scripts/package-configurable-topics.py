#!/usr/bin/env python3
"""Package source/evidence without build caches, broker data or sealed input copies."""
from pathlib import Path
import hashlib,json,zipfile,sys,os
R=Path(__file__).resolve().parents[2];destination=R.parent/'configurable-topics-v1.zip';excluded={'target','node_modules','.cache','.vite','__pycache__','.git'}
def selected():
 for p in R.rglob('*'):
  rel=p.relative_to(R)
  if rel.parts[0] in {'accepted','closing-review','runtime'} or any(part in excluded for part in rel.parts) or p.is_symlink() or not p.is_file() or p.name=='.DS_Store' or p.name in {'manifest.sha256','package-verification.json'}:continue
  yield p
files=sorted(selected());manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(R))+'\n' for p in files);(R/'manifest.sha256').write_text(manifest);files.append(R/'manifest.sha256')
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
 for p in files:z.write(p,str(p.relative_to(R)))
sha=hashlib.sha256(destination.read_bytes()).hexdigest();destination.with_suffix('.zip.sha256').write_text(sha+'  '+destination.name+'\n')
with zipfile.ZipFile(destination) as z:
 assert z.testzip() is None
 for line in manifest.splitlines():
  expected,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
print(json.dumps({'archive':str(destination),'sha256':sha,'bytes':destination.stat().st_size,'files':len(files)},indent=2))

#!/usr/bin/env python3
from pathlib import Path,PurePosixPath
import hashlib,json,zipfile,shutil,os
W=Path(__file__).resolve().parents[1];R=W.parent;D=W/'deliverables';P=D/'topic-retention-v1.1';D.mkdir(exist_ok=True)
if P.exists():raise RuntimeError('staging directory already exists')
P.mkdir()
base=Path('/Users/bruno/Projects/rust-view-server/followups/grouped-aggregates-v1.2/delivery/grouped-aggregates-v1.2.zip')
old=W.parent.parent/'topic-retention-v1/work'
def sha(b):return hashlib.sha256(b).hexdigest()
def eligible(rel):return PurePosixPath(rel).parts[0]!='evidence' and not any(v in PurePosixPath(rel).parts for v in ['target','node_modules','.cache','__pycache__','.vitest-attachments'])
def copy(rel,source=None):
 source=source or W/rel;target=P/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
base_files={}
with zipfile.ZipFile(base) as z:
 for i in z.infolist():
  if i.filename.startswith('work/') and not i.is_dir():base_files[i.filename[5:]]=sha(z.read(i))
project=[]
roots=['.github','admission','native','ingestion','browser','scripts','examples','fixtures','experiments','proto','build','bin','deploy']
for root in roots:
 if not (W/root).exists():continue
 for directory,dirs,files in os.walk(W/root,followlinks=False):
  dirs[:]=[d for d in dirs if d not in ['target','node_modules','.cache','__pycache__','.vitest-attachments']]
  for name in files:
   source=Path(directory)/name;rel=source.relative_to(W).as_posix()
   if source.is_symlink() or not eligible(rel) or name=='.DS_Store':continue
   if sha(source.read_bytes())!=base_files.get(rel):copy(rel);project.append(rel)
for rel in ['RETENTION-CONTRACT.md','TOPIC-DURABLE-FORMAT.md','RETENTION-V1.1-HANDOFF.md','APPLY.md','GATE-INVENTORY.json','ATTEMPTS.md','RETENTION-REPAIR.diff']:
 copy(rel);project.append(rel)
for rel in ['evidence/repair','evidence/a1','evidence/a2','evidence/grouped/build']:
 shutil.copytree(W/rel,P/rel)
for name in ['retention-931c9a32','retention-93677c24','retention-measure-d9e7f97c']:
 rel='evidence/retention/'+name;shutil.copytree(W/rel,P/rel)
shutil.copytree(old/'evidence/retention',P/'evidence/inherited-v1/retention')
shutil.copytree(old/'evidence/grouped/build',P/'evidence/inherited-v1/build')
for name in ['RETENTION-V1-HANDOFF.md','RETENTION-CONTRACT.md','TOPIC-DURABLE-FORMAT.md']:
 copy('evidence/inherited-v1/'+name,old/name)
copy('handoff/previous-retention-v1-handoff.zip',old/'deliverables/topic-retention-v1/handoff/previous-retention-v1-handoff.zip')
for name in ['topic-retention-v1-focused-review.zip','NEXT-AGENT-TASK.md']:
 copy('review/'+name,Path('/Users/bruno/.codex/attachments/d5b43a7d-26e3-4bd3-ae12-b570c77f0517')/name)
copy('review/USER-REQUEST.txt',Path('/Users/bruno/.codex/attachments/90be6fd1-6249-4651-8f13-4227b497716e/Pasted text.txt'))
merged={k:v for k,v in base_files.items() if eligible(k)}
for rel in project:merged[rel]=sha((P/rel).read_bytes())
receipt={'base_sha256':sha(base.read_bytes()),'prior_overlay_sha256':'0b3ded9cf5f1c7ed2c93e46143965418ec36511752ed92246d22dce39a3b6453','composition':'Extract base work/ to new project root, then overlay the declared project_files. This complete v1.1 overlay includes v1; no intermediate overlay is required.','coverage':'Every merged source/artifact member outside evidence/, target/, node_modules/, .cache/, __pycache__/, .vitest-attachments/. Evidence has complete package-manifest coverage.','project_files':sorted(set(project)),'merged_source_artifact_sha256':dict(sorted(merged.items()))}
(P/'COMPOSITION.json').write_text(json.dumps(receipt,indent=2))
manifest=[]
for file in sorted(p for p in P.rglob('*') if p.is_file()):manifest.append(sha(file.read_bytes())+'  '+file.relative_to(P).as_posix())
(P/'FILES.sha256').write_text('\n'.join(manifest)+'\n')
archive=D/'topic-retention-v1.1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for file in sorted(p for p in P.rglob('*') if p.is_file()):z.write(file,file.relative_to(D).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
assert archive.stat().st_size<45_000_000,archive.stat().st_size
(D/'topic-retention-v1.1.zip.sha256').write_text(sha(archive.read_bytes())+'  '+archive.name+'\n')
print(json.dumps({'package':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'members':len(manifest)+1,'project_changes':len(set(project)),'merged_source_artifacts':len(merged)},indent=2))

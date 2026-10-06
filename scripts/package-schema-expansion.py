#!/usr/bin/env python3
"""Package a complete minimal overlay against the exact accepted composition."""
from pathlib import Path
import zipfile,json,hashlib,difflib,shutil
W=Path(__file__).resolve().parents[1];ROOT=W.parent;INPUTS=ROOT.parent/'schema-expansion-v1-inputs';DEST=ROOT/'delivery/schema-expansion-v1'
sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(INPUTS/'grouped-aggregates-v1.2.zip')as z:base={i.filename[5:]:z.read(i)for i in z.infolist()if i.filename.startswith('work/')and not i.is_dir()}
with zipfile.ZipFile(INPUTS/'topic-retention-v1.1.zip')as z:
 c=json.loads(z.read('topic-retention-v1.1/COMPOSITION.json'))
 for n in c['project_files']:base[n]=z.read('topic-retention-v1.1/'+n)
def project(p):return not any(v in p.parts for v in ['target','node_modules','.cache','__pycache__','.vitest-attachments','__screenshots__']) and p.parts[0]!='evidence'
current={str(p.relative_to(W)):p.read_bytes() for p in W.rglob('*') if p.is_file() and not p.is_symlink() and project(p.relative_to(W))}
# Existing browser run-counter artifacts are unrelated to this overlay.
current={n:b for n,b in current.items()if n in base or n.startswith(('scripts/','native/','ingestion/','browser/src/','examples/schema-expansion/','fixtures/expanded-topics/','build/grouped/','bin/')) or n in ['SCHEMA-EXPANSION-CONTRACT.md','SCHEMA-EXPANSION-HANDOFF.md','SCHEMA-EXPANSION-ATTEMPTS.md','SCHEMA-EXPANSION-GATES.json','SCHEMA-EXPANSION-IDENTITIES.json']}
changed={n:b for n,b in current.items()if n not in base or b!=base[n]}
if DEST.exists():shutil.rmtree(DEST)
DEST.mkdir(parents=True)
for n,b in changed.items():p=DEST/'work'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod((W/n).stat().st_mode&0o777)
# Complete new-task evidence, without inherited evidence, ephemeral brokers or caches.
shutil.copytree(W/'evidence/schema-expansion',DEST/'evidence/schema-expansion')
shutil.copytree(ROOT/'evidence/native',DEST/'evidence/licenses')
diff=[]
for n,b in sorted(changed.items()):
 if n.endswith(('.rs','.ts','.tsx','.mjs','.py','.toml','.proto')):
  diff.extend(difflib.unified_diff(base.get(n,b'').decode().splitlines(True),b.decode().splitlines(True),fromfile='accepted/work/'+n if n in base else '/dev/null',tofile='schema-expansion-v1/work/'+n))
(DEST/'SCHEMA-EXPANSION.diff').write_text(''.join(diff))
receipt={'accepted_base_sha256':'e202466bc8e0c3b51a89963789802f812e3dc481b594330efe63d0818e239465','retention_overlay_sha256':'3261f464757531d2283586f53c16154bea66232eed82d4ec983b05f6e5676fd0','changed_project_files':{n:sha(b)for n,b in sorted(changed.items())},'composed_project_sha256':{n:sha(b)for n,b in sorted({**{n:b for n,b in base.items()if project(Path(n))},**current}.items())}}
(DEST/'COMPOSITION.json').write_text(json.dumps(receipt,indent=2)+'\n')
shutil.copy2(W/'scripts/verify-schema-expansion-composition.py',DEST/'verify-schema-expansion-composition.py')
(DEST/'APPLY.md').write_text('''# Apply schema-expansion-v1\n\nUse the exact grouped v1.2 base and retention v1.1 overlay, then this complete sparse overlay. The verifier checks all three archives and writes a NEW nonexistent destination ending in work. Never overlay an unrelated checkout or automatically migrate old canonical state.\n\n```\npython3 verify-schema-expansion-composition.py --base /absolute/grouped-aggregates-v1.2.zip --retention /absolute/topic-retention-v1.1.zip --expansion /absolute/schema-expansion-v1.zip --dest /absolute/new-candidate/work\n```\n\nUse bin/view_server_expanded, bin/view_server_expanded_faults and bin/generic_kafka_producer_expanded, whose Rust 1.96.1 identities appear in the current handoff. Inherited binaries are not substitutes. See work/SCHEMA-EXPANSION-HANDOFF.md for qualification and unresolved company input.\n''')
manifest={str(p.relative_to(DEST)):sha(p.read_bytes())for p in DEST.rglob('*')if p.is_file()}
(DEST/'FILES.sha256').write_text(''.join(h+'  '+n+'\n'for n,h in sorted(manifest.items())))
archive=ROOT/'schema-expansion-v1.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=False)as z:
 for p in sorted(DEST.rglob('*')):
  if p.is_file():z.write(p,'schema-expansion-v1/'+str(p.relative_to(DEST)))
assert archive.stat().st_size<45000000,archive.stat().st_size
archive.with_suffix('.zip.sha256').write_text(sha(archive.read_bytes())+'  '+archive.name+'\n')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'changed_files':len(changed)},indent=2))

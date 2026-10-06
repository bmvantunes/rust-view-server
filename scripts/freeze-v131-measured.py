"""Preserve exact measured artifacts; immutable once recorded, independent of later rebuild UUIDs."""
from pathlib import Path
import json,hashlib,subprocess,shutil
r=Path(__file__).resolve().parent.parent;e=r/'evidence/v13.1';assert json.loads((e/'candidate-qualification.json').read_text())['status']=='passed'
d=e/'measured-artifacts';assert not d.exists(),'Measured artifacts are immutable'
d.mkdir();index={'candidates':[]}
for b in json.loads((e/'candidate-builds.json').read_text())['candidates']:
 source=Path(b['root']);paths=set(b['sha256'])|{'browser/src/product-provider.tsx','browser/src/product.worker.ts','browser/pnpm-lock.yaml'}
 if b['codec']!='json':paths|={'experiments/v131/codec/Cargo.lock','experiments/v131/codec/src/scan.rs','experiments/v131/package-lock.json','admission/Cargo.toml'}
 hashes={}
 for name in sorted(paths):
  p=(r/name) if name=='experiments/v131/package-lock.json' else (source/name);target=d/b['codec']/name;target.parent.mkdir(parents=True,exist_ok=True)
  result=subprocess.run(['/bin/cp','-c','-p',str(p),str(target)],capture_output=True)
  if result.returncode:shutil.copy2(p,target)
  hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
 index['candidates'].append({'codec':b['codec'],'sha256':hashes})
runner=Path('/private/tmp/v131-codec-target/release/v13-codec-experiment');shutil.copy2(runner,d/'phase-codec-runner');index['phase_codec_sha256']=hashlib.sha256(runner.read_bytes()).hexdigest()
(d/'index.json').write_text(json.dumps(index,indent=2)+'\n')
print('Frozen',len(index['candidates']),'candidate pairs and phase runner')

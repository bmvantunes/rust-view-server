#!/usr/bin/env python3
"""Fresh pinned A1 red regression on sealed v1 in a disposable extraction."""
from pathlib import Path
import argparse,tempfile,zipfile,hashlib,subprocess,json,shutil,os
W=Path(__file__).resolve().parents[1];E=W/'evidence/a2';p=argparse.ArgumentParser();p.add_argument('sealed_v1',type=Path);a=p.parse_args()
assert hashlib.sha256(a.sealed_v1.read_bytes()).hexdigest()=='139438d40ba9c0f47cc8c57cd160263748a9e3540573b6d271844a8c98596a92'
node=os.environ.get('A2_NODE','/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node');version=subprocess.check_output([node,str(W/'browser/node_modules/typescript/bin/tsc'),'--version'],text=True).strip();assert version=='Version 7.0.2'
results={}
with tempfile.TemporaryDirectory(prefix='a1-red-')as temporary:
 root=Path(temporary)
 with zipfile.ZipFile(a.sealed_v1)as z:
  for n in z.namelist():
   if n.startswith(('work/browser/','work/examples/','work/experiments/v131/js/')):z.extract(n,root)
 old=root/'work';probes=old/'evidence/a1/probes';probes.mkdir(parents=True)
 for n in ['dynamic-aggregate-actual-source','exact-inferred-types','required-sound-results','safe-inference']:
  shutil.copy2(W/'evidence/a1/probes'/(n+'.ts'),probes/(n+'.ts'))
 for n in ['dynamic-aggregate-actual-source','exact-inferred-types','required-sound-results']:
  shutil.copy2(W/'evidence/a1/probes'/(n+'.json'),probes/(n+'.json'))
 (old/'browser/node_modules').symlink_to((W/'browser/node_modules').resolve())
 for n in ['dynamic-aggregate-actual-source','exact-inferred-types','required-sound-results']:
  r=subprocess.run([node,str(old/'browser/node_modules/typescript/bin/tsc'),'--noEmit','-p',str(probes/(n+'.json'))],cwd=old,capture_output=True,text=True);text=r.stdout+r.stderr;(E/('a1-red-'+n+'.log')).write_text(text);results[n]={'exit':r.returncode,'diagnostics':text.count('error TS')}
 source_hash=hashlib.sha256((old/'browser/src/topic-schema.ts').read_bytes()).hexdigest()
assert results['dynamic-aggregate-actual-source']['exit']==0 and results['exact-inferred-types']['exit']==0
assert results['required-sound-results']['diagnostics']==4
(E/'A1-RED-RERUN.json').write_text(json.dumps({'status':'PASS','scope':'fresh pinned A1 red reproduction on sealed v1, not runtime execution','compiler':version,'review_shim':False,'source_sha256':source_hash,'results':results},indent=2)+'\n')
print((E/'A1-RED-RERUN.json').read_text())

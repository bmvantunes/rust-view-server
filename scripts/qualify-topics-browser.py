#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,time,datetime
W=Path(__file__).resolve().parents[1];out=W.parent/'evidence/logs';node='/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node';env={**os.environ,'PATH':str(Path(node).parent)+':'+os.environ['PATH']}
def inputs():
 return {str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for base in ['browser/src','experiments/v131/js','fixtures/topics','build/configurable-topics'] for p in (W/base).rglob('*') if p.is_file()}|{str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (W/'browser').iterdir() if p.is_file() and p.suffix in ['.json','.yaml','.ts']}
a=inputs();started=datetime.datetime.now(datetime.timezone.utc).isoformat();results=[]
for name,cmd,cwd in [('browser-mounted-final',['./node_modules/.bin/vp','test','run'],W/'browser'),('types-final-verified',['./node_modules/.bin/tsc','--noEmit'],W/'browser'),('contracts-final-verified',['./node_modules/.bin/tsc','--noEmit','-p','tsconfig.contracts.json'],W/'browser'),('schema-final-verified',[node,'scripts/test-topic-schema.mjs'],W)]:
 t=time.monotonic()
 with (out/(name+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(name=name,command=cmd,exit=r.returncode,elapsed=time.monotonic()-t));print(results[-1],flush=True)
b=inputs();result=dict(passed=all(x['exit']==0 for x in results) and a==b,started=started,inputs=a,inputs_after=b,inputs_unchanged=a==b,checks=results);(out/'browser-final-receipt.json').write_text(json.dumps(result,indent=2));assert result['passed']

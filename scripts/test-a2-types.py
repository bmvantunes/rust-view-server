#!/usr/bin/env python3
"""Pinned complete projects, A1 regressions and A2 presence contracts; no React shim."""
from pathlib import Path
import subprocess,json,re,hashlib,os
W=Path(__file__).resolve().parents[1];E=W/'evidence/a2';B=W/'browser'
node=os.environ.get('A2_NODE','/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node');tsc=B/'node_modules/typescript/bin/tsc'
version=subprocess.check_output([node,str(tsc),'--version'],text=True).strip();assert version=='Version 7.0.2',version
results={}
def run(label,config,expected):
 p=subprocess.run([node,str(tsc),'--noEmit','-p',str(config)],cwd=W,text=True,capture_output=True);text=p.stdout+p.stderr
 (E/(label+'.log')).write_text(text);results[label]={'exit':p.returncode,'diagnostics':len(re.findall(r'error TS\d+',text))}
 assert (p.returncode==0)==expected,(label,text)
 return text
run('contracts-green',B/'tsconfig.contracts.json',True)
run('browser-green',B/'tsconfig.json',True)
run('a1-required-sound-results',W/'evidence/a1/probes/required-sound-results.json',True)
run('a1-dynamic-aggregate-actual-source',W/'evidence/a1/probes/dynamic-aggregate-actual-source.json',False)
run('a1-exact-inferred-types',W/'evidence/a1/probes/exact-inferred-types.json',False)
run('a2-required-safe-errors',E/'probes/required-safe-errors.json',True)
text=run('a2-unsafe-consumer',E/'probes/unsafe-consumer.json',False)
assert text.count('error TS')==8
for name,expected_count in [('grouped-contract.test-d.ts',20),('grouped-dynamic-contract.test-d.ts',8),('shape-contract.test-d.ts',12)]:
 source=(B/'src'/name).read_text();lines=source.splitlines();negative_lines=[i+2 for i,line in enumerate(lines)if '@ts-expect-error' in line];assert len(negative_lines)==expected_count
 unsuppressed=B/'src'/('a2-unsuppressed-'+name);config=E/('unsuppressed-'+name+'.json')
 unsuppressed.write_text('\n'.join('' if '@ts-expect-error' in line else line for line in lines)+'\n')
 config.write_text(json.dumps({'extends':'../../browser/tsconfig.json','include':['../../browser/src/'+unsuppressed.name]}))
 try:
  text=run('unsuppressed-'+name,config,False)
  diagnostic_lines={int(n)for n in re.findall(re.escape(unsuppressed.name)+r'\((\d+),',text)}
  assert set(negative_lines)<=diagnostic_lines,(negative_lines,diagnostic_lines)
  results['unsuppressed-'+name]['negative_expressions']=len(negative_lines)
  results['unsuppressed-'+name]['all_expressions_diagnosed']=True
  (E/'probes'/unsuppressed.name).write_text(unsuppressed.read_text())
 finally:unsuppressed.unlink()
(E/'TYPES.json').write_text(json.dumps({'status':'PASS','compiler':version,'react':json.loads((B/'node_modules/react/package.json').read_text())['version'],'react_types':json.loads((B/'node_modules/@types/react/package.json').read_text())['version'],'review_shim':False,'source_sha256':hashlib.sha256((B/'src/topic-schema.ts').read_bytes()).hexdigest(),'results':results},indent=2)+'\n')
print((E/'TYPES.json').read_text())

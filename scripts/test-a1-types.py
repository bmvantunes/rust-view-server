#!/usr/bin/env python3
"""Pinned source-bound A1 qualification; no React shim or declaration-only check."""
from pathlib import Path
import subprocess,json,re,hashlib,os
W=Path(__file__).resolve().parents[1];E=W/'evidence/a1';B=W/'browser'
node=os.environ.get('A1_NODE','/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node');tsc=B/'node_modules/typescript/bin/tsc'
version=subprocess.check_output([node,str(tsc),'--version'],text=True).strip();assert version=='Version 7.0.2',version
results={}
def run(label,config,expected):
 p=subprocess.run([node,str(tsc),'--noEmit','-p',str(config)],cwd=W,text=True,capture_output=True);text=p.stdout+p.stderr
 (E/(label+'.log')).write_text(text);results[label]={'exit':p.returncode,'diagnostics':len(re.findall(r'error TS\d+',text))}
 assert (p.returncode==0)==expected,(label,text)
 return text
run('contracts-green',B/'tsconfig.contracts.json',True)
run('browser-green',B/'tsconfig.json',True)
run('green-required-sound-results',E/'probes/required-sound-results.json',True)
run('green-dynamic-aggregate-actual-source',E/'probes/dynamic-aggregate-actual-source.json',False)
run('green-exact-inferred-types',E/'probes/exact-inferred-types.json',False)
for name in ['grouped-contract.test-d.ts','grouped-dynamic-contract.test-d.ts']:
 source=(B/'src'/name).read_text();lines=source.splitlines();negative_lines=[i+2 for i,line in enumerate(lines)if '@ts-expect-error' in line]
 if name=='grouped-contract.test-d.ts':assert len(negative_lines)==20
 unsuppressed=B/'src'/('a1-unsuppressed-'+name);config=E/('unsuppressed-'+name+'.json')
 # Keep line locations stable, require a real diagnostic at every original expression.
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

"""Negative source guards for storage dependencies crossing engine boundaries."""
from pathlib import Path
import shutil,subprocess,tempfile
root=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='v8-boundary-') as d:
    work=Path(d)
    for tree in ['native','ingestion','scripts']:
        shutil.copytree(root/tree,work/tree,ignore=shutil.ignore_patterns('target','node_modules','__pycache__'))
    for target,text in [('native/src/engine_contract.rs','use rusqlite::Connection;'),('ingestion/src/durable.rs','use rust_differential_product_core::engine_contract::ProductEngine;')]:
        p=work/target;before=p.read_text();p.write_text(before+'\n'+text+'\n')
        result=subprocess.run(['python3',str(work/'scripts/check-engine-boundary.py')],capture_output=True,text=True)
        print(result.stdout+result.stderr);assert result.returncode!=0,target
        p.write_text(before)
print('PASS both injected storage/evaluator boundary violations rejected')

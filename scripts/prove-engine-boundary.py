"""Mutation proof: the actual native CI command rejects a source-side backend import."""
from pathlib import Path
import tempfile,shutil,subprocess,json
root=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='engine-boundary-proof-') as directory:
    work=Path(directory)
    for folder in ['native','scripts','contract-tests','fixtures']:shutil.copytree(root/folder,work/folder,ignore=shutil.ignore_patterns('target','__pycache__'))
    shutil.copy2(root/'clippy.toml',work/'clippy.toml')
    p=work/'native/src/source.rs'
    p.write_text(p.read_text()+'\nuse timely::dataflow::operators::probe::Handle;\n')
    result=subprocess.run(['sh','scripts/ci-native.sh'],cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    assert result.returncode!=0 and 'source.rs:' in result.stdout and 'engine implementation type crosses boundary' in result.stdout,result.stdout
    print(json.dumps({'command':'sh scripts/ci-native.sh','injection':'native/src/source.rs: use timely::dataflow::operators::probe::Handle','exit':result.returncode,'output':result.stdout},indent=2))

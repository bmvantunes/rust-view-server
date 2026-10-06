from pathlib import Path
import tempfile,shutil,subprocess,json
root=Path(__file__).resolve().parent.parent
proof=[]
for path,injection in [('native/src/engine_contract.rs','use rdkafka::Message;'),('ingestion/src/coordination.rs','use timely::dataflow::Scope;')]:
    with tempfile.TemporaryDirectory(prefix='v7-boundary-') as directory:
        work=Path(directory)
        for folder in ['native','ingestion','scripts','contract-tests','fixtures']:
            shutil.copytree(root/folder,work/folder,ignore=shutil.ignore_patterns('target','__pycache__'))
        shutil.copy2(root/'clippy.toml',work/'clippy.toml')
        p=work/path;p.write_text(p.read_text()+'\n'+injection+'\n')
        result=subprocess.run(['sh','scripts/ci-native.sh'],cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        assert result.returncode==1 and ('crosses product boundary' in result.stdout or 'source adapter imports engine implementation' in result.stdout),result.stdout
        proof.append({'injection':path+': '+injection,'command':'sh scripts/ci-native.sh','exit':result.returncode,'output':result.stdout})
print(json.dumps(proof,indent=2))

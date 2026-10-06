"""Run the actual product CI entry point with forbidden calls in disposable copies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
logs = root / 'logs'
logs.mkdir(exist_ok=True)

def source_hashes():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / 'native').rglob('*') if p.is_file() and 'target' not in p.parts}

before = source_hashes()
results = []
with tempfile.TemporaryDirectory(prefix='distinct-lint-proof-') as temporary:
    sandbox = Path(temporary)
    shutil.copytree(root / 'native', sandbox / 'native', ignore=shutil.ignore_patterns('target'))
    shutil.copytree(root / 'scripts', sandbox / 'scripts')
    shutil.copytree(root / 'contract-tests', sandbox / 'contract-tests')
    shutil.copytree(root / 'fixtures', sandbox / 'fixtures')
    shutil.copy2(root / 'clippy.toml', sandbox / 'clippy.toml')
    example = sandbox / 'native/examples/forbidden_distinct.rs'
    example.parent.mkdir(exist_ok=True)
    for method in ['distinct_total', 'distinct_total_core']:
        invocation = 'distinct_total()' if method == 'distinct_total' else 'distinct_total_core::<isize>()'
        example.write_text('''use differential_dataflow::{input::InputSession, operators::ThresholdTotal};
fn main() {
    timely::execute_directly(|worker| {
        let mut input = InputSession::<u64, String, isize>::new();
        worker.dataflow(|scope| { let _ = input.to_collection(scope).''' + invocation + '''; });
    });
}
''')
        run = subprocess.run(['sh', 'scripts/ci-native.sh'], cwd=sandbox,
                             env=os.environ.copy(), text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        log = f'lint-forbidden-{method}.log'
        (logs / log).write_text('COMMAND sh scripts/ci-native.sh\n'
                               f'INJECTED {example.relative_to(sandbox)}\n'
                               f'SOURCE\n{example.read_text()}\n{run.stdout}\nEXIT {run.returncode}\n')
        assert run.returncode != 0, f'{method} incorrectly passed CI'
        assert 'error: use of a disallowed method' in run.stdout, run.stdout
        assert f'ThresholdTotal::{method}' in run.stdout, run.stdout
        assert not __import__('re').search(r'error\[E\d+\]', run.stdout), run.stdout
        results.append({'method': method, 'command': 'sh scripts/ci-native.sh',
                        'exit': run.returncode, 'log': 'logs/' + log,
                        'failure': 'denied clippy::disallowed_methods'})
assert source_hashes() == before, 'production source changed during negative proof'
evidence = root / 'evidence/distinct-lint-proof.json'
evidence.parent.mkdir(exist_ok=True)
evidence.write_text(json.dumps({'production_sources_unchanged': True, 'cases': results}, indent=2) + '\n')
print(evidence.read_text())

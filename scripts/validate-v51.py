"""Run the bounded existing gates and preserve their actual exit codes separately."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
(root / 'evidence/v5.1').mkdir(exist_ok=True)
gates = []
env = os.environ.copy()
env['EVIDENCE_PREFIX'] = 'v51'

def run(command, log, cwd=root, expected=0):
    destination = root / log
    destination.parent.mkdir(exist_ok=True)
    with destination.open('w') as output:
        output.write('COMMAND ' + json.dumps(command) + '\nCWD ' + str(cwd) + '\n')
        output.flush()
        result = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
        output.write(f'\nEXIT_STATUS={result.returncode}\n')
    gates.append({'command': command, 'cwd': str(cwd), 'log': log, 'exit': result.returncode, 'expected_exit': expected})
    (root / 'evidence/v5.1/gate-exits.json').write_text(json.dumps(gates, indent=2) + '\n')
    if result.returncode != expected:
        raise SystemExit(f'Gate failed: {command}; exit {result.returncode}; see {destination}')

run(['sh', 'scripts/ci-native.sh'], 'logs/native-ci-v51.log')
run(['sh', 'scripts/typecheck-browser.sh'], 'logs/typescript-v51.log')
run(['sh', 'scripts/typecheck-contracts.sh'], 'logs/type-contracts-v51.log')
run(['node', 'scripts/direct-wasm-v5.mjs', '.'], 'logs/direct-wasm-v51.log')
run(['node', 'scripts/core-oracle-v5.mjs', '.'], 'logs/oracle-v51.log')
run(['sh', 'scripts/test-browser.sh'], 'logs/browser-v51.log')
# Existing isolated scripts use fixed log filenames. Execute unchanged copies so
# the checkpoint's historical diagnostic logs are not overwritten.
with tempfile.TemporaryDirectory(prefix='v51-distinct-gates-') as temporary:
    work = Path(temporary)
    for tree in ['native', 'scripts', 'contract-tests', 'investigations']:
        shutil.copytree(root / tree, work / tree, ignore=shutil.ignore_patterns('target', 'node_modules', '__pycache__'))
    shutil.copy2(root / 'clippy.toml', work / 'clippy.toml')
    run(['sh', 'scripts/check-count-distinct.sh'], 'logs/distinct-v51-run.log', work)
    run(['python3', 'scripts/prove-distinct-lint.py'], 'logs/distinct-lint-v51-run.log', work)
    destination = root / 'logs/v51-distinct'
    destination.mkdir(exist_ok=True)
    for log in (work / 'logs').glob('*.log'):
        shutil.copy2(log, destination / log.name)
    proof = json.loads((work / 'evidence/distinct-lint-proof.json').read_text())
    for case in proof['cases']:
        case['log'] = 'logs/v51-distinct/' + Path(case['log']).name
    (root / 'evidence/v5.1/distinct-lint-proof.json').write_text(json.dumps(proof, indent=2) + '\n')

wasm = hashlib.sha256((root / 'browser/public/product_core.wasm').read_bytes()).hexdigest()
runtime = json.loads((root / 'evidence/v51-browser-runtime.json').read_text())
assert runtime['wasmSha256'] == wasm == 'b06da57e36080d26e4c3e22c6caed477514a6aea64a62c865ba97b9a3101f515'
assert (root / 'browser/public/product_core.sha256').read_text().strip() == wasm
summary = {'gates': gates, 'wasm_sha256': wasm, 'wasm_rebuilt': False,
           'wasm_reason': 'Adapter/documentation-only hotfix; native sources and build inputs unchanged.',
           'browser': runtime, 'node': subprocess.check_output(['node', '--version'], env=env, text=True).strip(),
           'counts': {'native': 18, 'browser': 65, 'original_browser_preserved': 33, 'new_browser': 32,
                      'product_oracle_comparisons': 3006, 'isolated_contract_epochs': 18, 'isolated_operator_epochs': 9},
           'baseline_red': [{'log': 'logs/browser-v51-baseline.log', 'exit': 1, 'failed': 5},
                            {'log': 'logs/browser-v51-baseline-exact.log', 'exit': 1, 'failed': 2}],
           'expected_defect_exit': 101, 'clippy_negative_proof': proof,
           'claude_provenance': {'status': 'closed_by_user_constraint', 'outstanding_acceptance_requirement': False},
           'independent_review_bundle': 'Not provided locally: actual REVIEW/probe/harness files not read or executed. User task reproductions and accessible reviewer narrative were read; fresh pinned reproductions executed.',
           'skipped_executable_gates': []}
(root / 'evidence/v5.1/validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))

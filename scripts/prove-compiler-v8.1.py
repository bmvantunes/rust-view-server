"""Real compiler/CI negatives in disposable trees; expected failures are required.

The poisoned full-validator run stops at ingestion, before this gate, so cannot
recurse. Baselines are exact copies; no missing-dependency error is accepted.
"""
from pathlib import Path
import json, os, shutil, subprocess, tempfile
from acceptance_v81 import BASELINES, PREFIX, inputs, snapshot
root = Path(__file__).resolve().parent.parent
cases = []
with tempfile.TemporaryDirectory(prefix='v81-real-red-') as directory:
    work = Path(directory)
    snapshot(root, work, inputs(root))
    for version in BASELINES:
        shutil.copy2(root / (PREFIX + version + '.zip'), work)
    source = work / 'ingestion/src/lib.rs'
    original = source.read_text()
    source.write_text(original + '\ncompile_error!("INDEPENDENT_REVIEW_RESUME_PROBE_DO_NOT_SHIP");\n')
    command = ['python3', 'scripts/validate-v8.1.py']
    result = subprocess.run(command, cwd=work, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    state = json.loads((work / 'evidence/v8.1/validation.json').read_text())
    assert result.returncode != 0 and state['status'] == 'failed', result.stdout
    (root / 'evidence/v81-negative-validation.json').write_text(json.dumps(state, indent=2) + '\n')
    gate = state['gates'][-1]
    assert gate['gate'] == 'ingestion' and gate['command'] == ['sh', 'scripts/test-ingestion.sh']
    log = work / 'evidence/v8.1/runs' / state['run_id'] / 'ingestion.log'
    compiler_output = log.read_text()
    assert 'error: INDEPENDENT_REVIEW_RESUME_PROBE_DO_NOT_SHIP' in compiler_output, compiler_output
    (root / 'logs/v81-real-compile-error.log').write_text(result.stdout + '\n' + compiler_output)
    packaging = subprocess.run(['python3', 'scripts/package-v8.1.py'], cwd=work, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert packaging.returncode != 0 and 'No accepted fresh v8.1 run' in packaging.stdout, packaging.stdout
    assert not (work / (PREFIX + 'v8.1.zip')).exists()
    (root / 'logs/v81-real-poison-package.log').write_text(packaging.stdout)
    cases.append(dict(case='compile_error', command=command, validator_exit=result.returncode,
                      actual_ci_command=gate['command'], compiler_exit=gate['exit'],
                      packaging_exit=packaging.returncode, status='expected-failure',
                      intended_diagnostic='error: INDEPENDENT_REVIEW_RESUME_PROBE_DO_NOT_SHIP'))
    source.write_text(original)
    rustc = subprocess.check_output(['rustup', 'which', '--toolchain', '1.96.1', 'rustc'], text=True).strip()
    env = dict(os.environ, RUSTC=rustc, CARGO_BUILD_JOBS='1',
               CARGO_TARGET_DIR=str(Path(tempfile.gettempdir()) / 'v81-boundary-compiler-target'))
    command = ['rustup', 'run', '1.96.1', 'cargo', 'check', '--locked', '--offline',
               '--manifest-path', 'native/Cargo.toml']
    target = work / 'native/tests/v81_private_boundary.rs'
    target.write_text('use rust_differential_product_core::product_engine::DifferentialProductEngine;\n')
    private = subprocess.run(command + ['--test', 'v81_private_boundary'], cwd=work, env=env,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert private.returncode != 0 and 'error[E0603]: module `product_engine` is private' in private.stdout, private.stdout
    (root / 'logs/v81-private-boundary.log').write_text(private.stdout)
    cases.append(dict(case='private_engine_boundary', command=command + ['--test', 'v81_private_boundary'],
                      exit=private.returncode, status='expected-failure', intended_diagnostic='E0603 private module'))
    target.unlink()
    native = work / 'native/src/lib.rs'
    native.write_text(native.read_text() + '\nuse rusqlite::Connection;\n')
    storage = subprocess.run(command + ['--lib'], cwd=work, env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert storage.returncode != 0 and 'error[E0432]: unresolved import `rusqlite`' in storage.stdout, storage.stdout
    (root / 'logs/v81-storage-compiler-boundary.log').write_text(storage.stdout)
    cases.append(dict(case='native_has_no_storage_dependency', command=command + ['--lib'],
                      exit=storage.returncode, status='expected-failure', intended_diagnostic='E0432 unresolved rusqlite import'))
report = dict(run_id=os.environ.get('ACCEPTANCE_RUN_ID'), status='executed', cases=cases,
              poisoned_source_and_archives='disposable, not shipped')
(root / 'evidence/v81-compiler-negative.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

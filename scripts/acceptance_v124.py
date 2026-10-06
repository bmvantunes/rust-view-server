"""Fresh-only checkpoint acceptance. No cache reuse or configurable production gates.

Source identity includes path, bytes, and executable bit (additions/deletions included).
A private snapshot is tested; the live inputs are monitored and compared throughout.
Generated evidence is integrity-bound separately, never used as a source cache.
"""
from pathlib import Path
import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile

POLICY = 'v12.4-fresh-snapshot-1'
PREFIX = 'rust-differential-product-20260929-review-checkpoint-'
BASELINES = {'v12.3': 'b35504ee3d90c576db1ee62a5a608f56702426918ac28c7bce6374c87be720a8', 'v12.2': '182e24d5911222f943c930059dc9317d44324d0a96c665ee14259fdd57062a09', 'v12.1': 'fc1b6feeaa8f25263073e39fbac19b5b97b1ba9d9a5db9f52e3fcf25081e1b56', 'v12': 'ef1f1c4d7319ab95cdfdf0de608e04ecba0cdb58cbe7b1211360535abac58731', 'v11': '8977405f3ba60a0986fbdf0fa057676a9c5e9799afab3c807a23135f8b6fd382', 'v10': '621193770c1869e49aa4d660a08543c958e807e591ab615899c5c29db7574cb3', 'v9': 'd2fe23ef4282e66a3ff4139be35a1303581026573f472b8a0e7133d4f4b6fc65', 'v8.1': '901f7c5959e856c8002b11b40b621c57982d5eaa72a6228ac948a7f6c0966811', 'v7': 'fb2d8b6601a2ce44d75ffe1bd94803550226e71a5f04e7ce042e25147654260a',
             'v8': '9d40ce674cd6d16d6e8ddf3dc3f44ceef59b06f07ca76c6af2976f4783516203'}
WASM = 'browser/public/product_core.wasm'
SKIP_DIRS = {'node_modules', 'target', '.git', '__pycache__', '.vite',
             '__screenshots__', '.vitest-attachments', 'v5-baseline-run'}
GENERATED = {'bin/view_server_faults', 'bin/view_server', WASM, 'browser/public/product_core.sha256',
             'browser/public/product-core-100.json', 'browser/v5-browser-runtime.json',
             'browser/v5-browser-counters.json'}
TREES = {'bin', 'browser', 'native', 'ingestion', 'fixtures', 'scripts', 'reports',
         'logs', 'evidence', 'investigations', 'contract-tests', '.github'}
GATES = [
    ('toolchain', ['python3', 'scripts/toolchain-v8.1.py']),
    ('acceptance-regressions', ['python3', '-m', 'unittest', 'discover', '-s', 'scripts/tests', '-v']),
    ('golden', ['python3', 'scripts/generate-engine-corpus.py', '--check']),
    ('native', ['sh', 'scripts/ci-native.sh']),
    ('ingestion', ['sh', 'scripts/test-ingestion.sh']),
    ('environment-qualification', ['python3', 'scripts/qualify-v124-environment.py']),
    ('historical-measurement-integrity', ['python3', 'scripts/verify-v124-historical.py']),
    ('engine-boundary', ['python3', 'scripts/prove-engine-boundary.py']),
    ('source-boundary', ['python3', 'scripts/prove-v7-boundary.py']),
    ('storage-boundary', ['python3', 'scripts/prove-v8-boundary.py']),
    ('compiler-negative', ['python3', 'scripts/prove-compiler-v124.py']),
    ('licenses', ['python3', 'scripts/audit-v8-licenses.py']),
    ('service-build', ['python3', 'scripts/build-service-v124.py']),
    ('wasm-build', ['python3', 'scripts/build-wasm-v124.py']),
    ('typescript', ['sh', 'scripts/typecheck-browser.sh']),
    ('type-contracts', ['sh', 'scripts/typecheck-contracts.sh']),
    ('direct-wasm', ['node', 'scripts/direct-wasm-v5.mjs', '.']),
    ('oracle', ['node', 'scripts/core-oracle-v5.mjs', '.']),
    ('integer-admission-oracle', ['node', 'scripts/test-v124-integer-admission.mjs']),
    ('row-canonical-oracle', ['node', 'scripts/test-v124-row-canonical.mjs']),
    ('publication-oracle-regressions', ['node', 'scripts/test-v124-oracle.mjs']),
    ('browser', ['sh', 'scripts/test-browser.sh']),
    ('remote-browser', ['node', 'scripts/test-v124-legacy-remote.mjs']),
    ('quota-red-green', ['python3', 'scripts/test-v124-quota.py']),
    ('provider-lifetimes', ['node', 'scripts/test-v124-provider.mjs']),
    ('remote-protocol', ['node', 'scripts/test-v124-protocol.mjs']),
    ('remote-barriers', ['node', 'scripts/test-v124-barriers.mjs']),
    ('remote-integer-admission', ['node', 'scripts/test-v124-integer-browser.mjs']),
    ('remote-row-canonical', ['node', 'scripts/test-v124-row-browser.mjs']),
    ('remote-exact-values', ['node', 'scripts/test-v124-exact-values.mjs']),
    ('release-profile', ['node', 'scripts/test-v124-browser.mjs']),
    ('profile-verification', ['node', 'scripts/verify-v124-profile.mjs']),
    ('distinct', ['sh', 'scripts/check-count-distinct.sh']),
    ('distinct-lint', ['python3', 'scripts/prove-distinct-lint.py']),
]
WASM_GATES = {'direct-wasm', 'oracle', 'browser', 'publication-oracle-regressions', 'integer-admission-oracle', 'row-canonical-oracle'}
REQUIRED_GENERATED = ['evidence/v12.4/integer-admission.json', 'evidence/v12.4/integer-browser.json', 'evidence/v12.4/integer-browser.log', 'evidence/v12.4/oracle-regressions.json', 'evidence/v12.4/exact-values.json', 'evidence/v12.4/exact-values.log', 'evidence/v12.4/provider.json', 'evidence/v12.4/fault-service-build.json', 'evidence/v12.4/barriers.json', 'evidence/v12.4/barriers.log', 'evidence/v12.4/browser-profile.json', 'evidence/v12.4/browser-profile.log', 'evidence/v12.4/profile-verification.json', 'evidence/v12.4/protocol.json', 'evidence/v12.4/quota-v11.json', 'evidence/v12.4/quota-v12.json', 'evidence/v12.4/quota-current.json', 'evidence/v12.4/service-build.json', 'evidence/v124-remote.json', 'evidence/v124-remote.log', 'evidence/v124-environment.json', 'logs/count-distinct-minimal-addendum.log',
                      'logs/lint-forbidden-distinct_total.log', 'logs/lint-forbidden-distinct_total_core.log',
                      'logs/v124-real-compile-error.log', 'logs/v124-real-poison-package.log',
                      'logs/v124-private-boundary.log', 'logs/v124-storage-compiler-boundary.log',
                      'evidence/v124-negative-validation.json', 'evidence/v124-browser-runtime.json', 'evidence/v124-browser-counters.json',
                      'evidence/v8/licenses.json', 'evidence/distinct-lint-proof.json',
                      'evidence/v124-wasm-build.json', 'evidence/v124-compiler-negative.json']
REQUIRED_GENERATED += ['evidence/v12.4/row-canonical.json', 'evidence/v12.4/row-browser.json', 'evidence/v12.4/row-browser.log']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read_json(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def walk(root):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for d in dirs:
            require(not (Path(directory) / d).is_symlink(), 'Unexpected directory symlink: ' + d)
        for name in sorted(names):
            p = Path(directory) / name
            if name == '.DS_Store' or p.suffix == '.pyc':
                continue
            yield p


def inputs(root):
    result = {}
    for path in walk(root):
        name = path.relative_to(root).as_posix()
        if (name.split('/')[0] in {'logs', 'evidence'} and not name.startswith(('evidence/v12/measurements/', 'evidence/v13-stage0/', 'evidence/v13-stage0-v124/'))) or name in GENERATED:
            continue
        if '/' not in name and ('.zip' in name or name.endswith('.sha256')):
            continue
        require(not path.is_symlink(), 'Unexpected input symlink: ' + name)
        require(not path.name.startswith('.env'), 'Unexpected environment file: ' + name)
        result[name] = {'sha256': sha(path), 'executable': bool(path.stat().st_mode & 0o111)}
    return result


def fingerprint(manifest):
    return digest(canonical(manifest))


def unchanged(root, expected):
    require(inputs(root) == expected, 'Authoritative inputs changed (content, paths or mode)')


def baselines(root):
    actual = {v: sha(root / (PREFIX + v + '.zip')) for v in BASELINES}
    require(actual == BASELINES, 'Baseline archive identity mismatch')
    return actual


@contextlib.contextmanager
def lock(root):
    path = root / 'evidence/v12.4/.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def begin(root):
    state = {'policy': POLICY, 'run_id': str(uuid.uuid4()), 'status': 'running',
             'started_ns': time.time_ns(), 'gates': [], 'reused': 0,
             'not_run': [name for name, _ in GATES]}
    write_json(root / 'evidence/v12.4/validation.json', state)
    return state


def snapshot(root, destination, manifest):
    for name in manifest:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    unchanged(destination, manifest)
    unchanged(root, manifest)
    (destination / 'logs').mkdir(exist_ok=True)
    (destination / 'evidence').mkdir(exist_ok=True)
    # Pinned, installed JS dependencies are a runtime prerequisite, not shipped input.
    (destination / 'browser/node_modules').symlink_to(root / 'browser/node_modules', target_is_directory=True)


def run_gate(command, cwd, env, log, header, monitor):
    with log.open('w') as stream:
        stream.write(json.dumps(header, sort_keys=True) + '\n')
        stream.flush()
        child = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            while child.poll() is None:
                monitor()
                time.sleep(0.25)
            monitor()
        except BaseException:
            import signal
            os.killpg(child.pid, signal.SIGTERM) if child.poll() is None else None
            child.wait()
            raise
        stream.write('\nEXIT_STATUS=' + str(child.returncode) + '\n')
    return child.returncode


def validate(root):
    state = begin(root)  # Invalidate previous green before any preflight can fail.
    current = root / 'evidence/v12.4/validation.json'
    run = root / 'evidence/v12.4/runs' / state['run_id']
    run.mkdir(parents=True)
    try:
        manifest = inputs(root)
        state.update(input_fingerprint=fingerprint(manifest), baseline_sha256=baselines(root))
        write_json(run / 'inputs.json', manifest)
        env = os.environ.copy()
        rustc = subprocess.check_output(['rustup', 'which', '--toolchain', '1.96.1', 'rustc'], text=True).strip()
        env['PATH'] = str(Path(rustc).parent) + os.pathsep + env.get('PATH', '')
        env.update(EVIDENCE_PREFIX='v124', PYTHONDONTWRITEBYTECODE='1',
                   ACCEPTANCE_RUN_ID=state['run_id'])
        with tempfile.TemporaryDirectory(prefix='v124-validated-') as temporary:
            work = Path(temporary)
            snapshot(root, work, manifest)
            env["V12_SERVICE_BINARY"] = str(work / "bin/view_server")
            for version in BASELINES:
                shutil.copy2(root / (PREFIX + version + '.zip'), work)
            for name, command in GATES:
                unchanged(root, manifest)
                unchanged(work, manifest)
                before = sha(work / WASM) if name in WASM_GATES else None
                header = dict(policy=POLICY, run_id=state['run_id'], gate=name, command=command,
                              input_fingerprint=state['input_fingerprint'])
                log = run / (name + '.log')
                started = time.time_ns()
                state['active_gate'] = dict(header, status='running', started_ns=started)
                state['not_run'].remove(name)
                write_json(current, state)
                code = run_gate(command, work, env, log, header, lambda: unchanged(root, manifest))
                unchanged(work, manifest)
                result = dict(header, status='executed', exit=code, started_ns=started,
                              finished_ns=time.time_ns(), log_sha256=sha(log))
                if name in WASM_GATES:
                    result.update(wasm_before=before, wasm_after=sha(work / WASM))
                    require(result['wasm_before'] == result['wasm_after'], 'WASM changed during ' + name)
                write_json(run / (name + '.json'), result)
                state['gates'].append(result)
                state.pop('active_gate')
                write_json(current, state)
                print(name + ': executed exit ' + str(code), flush=True)
                require(code == 0, 'Gate failed: ' + name)
            state['wasm_sha256'] = sha(work / WASM)
            state['fault_service_sha256'] = sha(work / 'bin/view_server_faults')
            state['service_sha256'] = sha(work / 'bin/view_server')
            for folder in ['logs', 'evidence']:
                shutil.copytree(work / folder, run / 'generated' / folder)
            for name in REQUIRED_GENERATED:
                require((run / 'generated' / name).is_file(), 'Missing required result: ' + name)
            state['expected_failures'] = {'distinct_minimal': {'exit': 101, 'outer_gate': 'distinct'},
                                          'compiler_negative': 'intended diagnostics verified',
                                          'distinct_lint': 'both denied methods rejected by native CI'}
            state['artifacts'] = {p.relative_to(run).as_posix(): sha(p) for p in walk(run)}
            # Publish precisely the freshly built/tested artifact only after all gates passed.
            unchanged(root, manifest)
            (root / 'bin').mkdir(exist_ok=True)
            shutil.copy2(work / 'bin/view_server', root / 'bin/view_server')
            shutil.copy2(work / 'bin/view_server_faults', root / 'bin/view_server_faults')
            (root / WASM).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work / WASM, root / WASM)
            (root / 'browser/public/product_core.sha256').write_text(state['wasm_sha256'] + '\n')
            state.update(status='accepted', finished_ns=time.time_ns(), not_run=[])
            write_json(run / 'validation.json', state)
            verify(root, state)
            write_json(current, state)
        print(json.dumps({'status': state['status'], 'run_id': state['run_id'],
                          'wasm_sha256': state['wasm_sha256']}, indent=2))
        return state
    except BaseException as error:
        if 'active_gate' in state:
            state['active_gate'].update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'aborted',
                                        error=str(error), finished_ns=time.time_ns())
        state.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                     error=str(error), finished_ns=time.time_ns())
        write_json(run / 'validation.json', state)
        write_json(current, state)
        raise


def verify(root, state=None):
    state = state if state is not None else read_json(root / 'evidence/v12.4/validation.json')
    require(state.get('policy') == POLICY and state.get('status') == 'accepted', 'No accepted fresh v124 run')
    require(state.get('reused') == 0 and state.get('not_run') == [] and 'active_gate' not in state, 'Incomplete or reused gates')
    run_id = state['run_id']
    require(str(uuid.UUID(run_id)) == run_id, 'Invalid run identity')
    run = root / 'evidence/v12.4/runs' / run_id
    require(read_json(run / 'validation.json') == state, 'Run summary identity mismatch')
    expected = [name for name, _ in GATES]
    require([g.get('gate') for g in state['gates']] == expected, 'Required gate set/order mismatch')
    manifest = read_json(run / 'inputs.json')
    require(fingerprint(manifest) == state['input_fingerprint'], 'Input manifest identity mismatch')
    unchanged(root, manifest)
    require(state['baseline_sha256'] == baselines(root), 'Baseline evidence mismatch')
    require(sha(root / WASM) == state['wasm_sha256'], 'Unvalidated WASM')
    require((root / 'browser/public/product_core.sha256').read_text().strip() == state['wasm_sha256'],
            'WASM sidecar mismatch')
    required = {'inputs.json'} | {n + ext for n in expected for ext in ['.json', '.log']}
    required |= {'generated/' + n for n in REQUIRED_GENERATED}
    require(required <= state['artifacts'].keys(), 'Required evidence missing from artifact index')
    for name, value in state['artifacts'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe artifact path')
        require(sha(run / name) == value, 'Evidence hash mismatch: ' + name)
    for result, (name, command) in zip(state['gates'], GATES):
        require(result == read_json(run / (name + '.json')), 'Gate result mismatch: ' + name)
        require(result['run_id'] == run_id and result['policy'] == POLICY and
                result['input_fingerprint'] == state['input_fingerprint'] and
                result['command'] == command and result['status'] == 'executed' and
                result['exit'] == 0 and result['finished_ns'] >= result['started_ns'],
                'Not a successful fresh gate: ' + name)
        log = run / (name + '.log')
        require(sha(log) == result['log_sha256'], 'Gate log hash mismatch: ' + name)
        header = json.loads(log.read_text().splitlines()[0])
        require(header == {k: result[k] for k in ['policy', 'run_id', 'gate', 'command', 'input_fingerprint']},
                'Gate log identity mismatch: ' + name)
        require(log.read_text().endswith('\nEXIT_STATUS=0\n'), 'Missing successful completion: ' + name)
        if name in WASM_GATES:
            require(result['wasm_before'] == result['wasm_after'] == state['wasm_sha256'],
                    'Direct/browser WASM identity mismatch')
    generated = run / 'generated/evidence'
    require(sha(root / 'bin/view_server') == state['service_sha256'], 'Unvalidated service binary')
    require(sha(root / 'bin/view_server_faults') == state['fault_service_sha256'], 'Unvalidated fault binary')
    for name in ['barriers', 'browser-profile']:
        value = read_json(generated / ('v12.4/' + name + '.json'))
        require(value['status'] == 'passed' and value['run_id'] == run_id and value['release_binary_sha256'] == state['service_sha256'], 'V12.4 browser/profile release binding')
    require(read_json(generated / 'v12.4/barriers.json')['fault_binary_sha256'] == state['fault_service_sha256'], 'Fault barrier binary binding')
    require(read_json(generated / 'v12.4/profile-verification.json')['raw_sha256'] == sha(generated / 'v12.4/browser-profile.json'), 'Profile raw binding')
    exact = read_json(generated / 'v12.4/exact-values.json')
    oracle_regressions = read_json(generated / 'v12.4/oracle-regressions.json')
    expected_cases = ['descending-ties', 'scale-floor', 'unicode-id-ties']
    require(oracle_regressions.get('status') == 'passed' and
            oracle_regressions.get('run_id') == run_id and
            oracle_regressions.get('wasm_sha256') == state['wasm_sha256'] and
            oracle_regressions.get('historical_archive_sha256') == BASELINES['v12.1'],
            'Oracle regression WASM/run/baseline binding')
    require([c.get('name') for c in oracle_regressions.get('cases', [])] == expected_cases and
            all(all(c.get(k) is True for k in ['fresh_wasm_matches_fixed_expected',
                'historical_rejects_correct', 'historical_accepts_poison',
                'repaired_accepts_correct', 'repaired_rejects_poison', 'live_ledger_rejects_poison'])
                for c in oracle_regressions['cases']), 'Missing oracle red/green negatives')
    require(oracle_regressions.get('equivalent_source_noop', {}).get('fresh_wasm_version') == 2 and
            all(oracle_regressions['equivalent_source_noop'].get(k) is True for k in
                ['historical_rejects_correct', 'historical_accepts_poison', 'repaired_accepts_correct', 'repaired_rejects_poison']) and
            exact.get('equivalent_source_noop', {}).get('no_live_publication') is True,
            'Missing equivalent-source version regression')
    require(exact.get('status') == 'passed' and exact.get('run_id') == run_id and
            exact.get('release_binary_sha256') == state['service_sha256'] and
            exact.get('oracle', {}).get('live', 0) >= 4 and
            sorted(exact.get('poisoning_rejected', [])) == sorted(expected_cases),
            'Mounted exact-value regression binding')
    for value, paths in [(oracle_regressions, ['scripts/v124-oracle.mjs', 'scripts/test-v124-oracle.mjs']),
                         (exact, ['scripts/v124-oracle.mjs', 'scripts/test-v124-exact-values.mjs', 'browser/src/product.remote.worker.ts'])]:
        require(value.get('source_hashes') == {p: sha(root / p) for p in paths},
                'Exact-value oracle/harness source binding')
    integer = read_json(generated / 'v12.4/integer-admission.json')
    integer_browser = read_json(generated / 'v12.4/integer-browser.json')
    for value, paths in [(integer, ['scripts/v124-oracle.mjs', 'scripts/test-v124-integer-admission.mjs', 'native/src/product.rs']),
                         (integer_browser, ['scripts/v124-oracle.mjs', 'scripts/test-v124-integer-browser.mjs', 'browser/src/product.remote.worker.ts'])]:
        require(value.get('status') == 'passed' and value.get('run_id') == run_id and
                value.get('historical_archive_sha256') == BASELINES['v12.2'] and
                value.get('source_hashes') == {p: sha(root / p) for p in paths},
                'Integer admission source/run/baseline binding')
    require(integer.get('wasm_sha256') == state['wasm_sha256'] and
            len(integer.get('cases', [])) == 26 and integer.get('invalidCases') == 44 and
            integer.get('equivalentVersionChecked') is True and
            sum(c.get('historicalRejectsAdmitted') is True for c in integer['cases']) == 10 and
            all(all(c.get(k) is True for k in ['wasmMatchesFixedExpected', 'repairedAccepts', 'poisonRejected'])
                for c in integer['cases']), 'Missing integer admission red/green proof')
    require(integer_browser.get('release_binary_sha256') == state['service_sha256'] and
            integer_browser.get('oracle', {}).get('live', 0) >= 1 and
            all(integer_browser.get(k) is True for k in ['historicalRejectsCorrect', 'poisonedValueRejected',
                'poisonedVersionRejected', 'equivalentSourceNoop', 'finalZeroSubscriptions']),
            'Missing mounted integer admission proof')
    row = read_json(generated / 'v12.4/row-canonical.json')
    row_browser = read_json(generated / 'v12.4/row-browser.json')
    for value, paths in [(row, ['scripts/v124-oracle.mjs', 'scripts/test-v124-row-canonical.mjs', 'native/src/product.rs']),
                         (row_browser, ['scripts/v124-oracle.mjs', 'scripts/test-v124-row-browser.mjs', 'browser/src/product.remote.worker.ts', 'browser/src/v12-harness.tsx'])]:
        require(value.get('status') == 'passed' and value.get('run_id') == run_id and
                value.get('historical_archive_sha256') == BASELINES['v12.3'] and
                value.get('source_hashes') == {p: sha(root / p) for p in paths},
                'Row canonical source/run/baseline binding')
    row_cases = ['omitted-label', 'explicit-missing', 'null', 'empty-string', 'value',
                 'ignored-row-field', 'ignored-amount-field', 'ignored-value-label-field']
    red_cases = {'omitted-label', 'ignored-row-field', 'ignored-value-label-field'}
    require(row.get('wasm_sha256') == state['wasm_sha256'] and
            [c.get('name') for c in row.get('cases', [])] == row_cases and
            all(all(c.get(k) is True for k in ['wasmMatchesFixedExpected', 'repairedAccepts',
                    'labelDistinctionsPreserved', 'nativeEquivalentNoop']) and
                all(c.get(k) is (c['name'] in red_cases) for k in ['historicalRejectsCorrect',
                    'historicalAcceptsPoison', 'repairedRejectsPoison']) for c in row['cases']) and
            all(row.get(k) is True for k in ['equivalentVersionChecked',
                'historicalAcceptsPoisonedVersion', 'repairedRejectsPoisonedVersion']),
            'Missing row canonical WASM red/green proof')
    require(row_browser.get('release_binary_sha256') == state['service_sha256'] and
            row_browser.get('oracle', {}).get('live', 0) >= 4 and
            len(row_browser.get('hookRows', [])) == 5 and
            all(row_browser.get(k) is True for k in ['historicalRejectsCorrect', 'historicalAcceptsPoison',
                'poisonedLabelRejected', 'poisonedVersionRejected', 'equivalentSourceNoop',
                'labelDistinctionsPreserved', 'finalZeroSubscriptions']),
            'Missing mounted row canonical proof')
    fault_build = read_json(generated / 'v12.4/fault-service-build.json')
    require(fault_build['exit'] == 0 and fault_build['run_id'] == run_id and fault_build['binary_sha256'] == state['fault_service_sha256'], 'Fault build binding')
    service_build = read_json(generated / 'v12.4/service-build.json')
    remote = read_json(generated / 'v124-remote.json')
    require(service_build['exit'] == 0 and service_build['run_id'] == run_id and service_build['binary_sha256'] == state['service_sha256'], 'Service build binding')
    require(remote['status'] == 'passed' and remote['binary_sha256'] == state['service_sha256'] and remote['lifecycle_iterations'] == 80, 'Real remote browser binding')
    require(read_json(generated / 'v124-browser-runtime.json')['wasmSha256'] == state['wasm_sha256'],
            'Browser-loaded WASM mismatch')
    build = read_json(generated / 'v124-wasm-build.json')
    require(build['run_id'] == run_id and build['fresh_empty_target'] is True and
            build['exit'] == 0 and build['wasm_sha256'] == state['wasm_sha256'], 'No fresh build event')
    oracle_text = (run / 'oracle.log').read_text().split('\n', 1)[1].rsplit('\nEXIT_STATUS=', 1)[0]
    oracle = json.loads(oracle_text)
    require(oracle['wasm_sha256'] == state['wasm_sha256'] and
            any(c.get('result_and_group_checks') == 3006 and c.get('pass') is True for c in oracle['checks']),
            'Missing 3006 executed oracle comparisons')
    require('EXPECTED_DEFECT_EXIT=101' in (run / 'generated/logs/count-distinct-minimal-addendum.log').read_text(),
            'Missing expected COUNT DISTINCT failure')
    return state


def package(root):
    state = verify(root)
    archive = root / (PREFIX + 'v12.4.zip')
    sidecar = Path(str(archive) + '.sha256')
    require(not archive.exists() and not sidecar.exists(), 'Never overwrite a sealed checkpoint')
    files = []
    for path in walk(root):
        name = path.relative_to(root).as_posix()
        if name == 'evidence/v12.4/.lock' or name == 'evidence/v12.4/package-result.json':
            continue
        if name.split('/')[0] not in TREES and '/' in name:
            continue
        if '.zip' in path.name or path.suffix == '.sha256' and '/' not in name:
            continue
        require(not path.is_symlink(), 'Unexpected packaged symlink: ' + name)
        require(not path.name.startswith('.env') and not path.name.endswith(('-wal', '-shm')), 'Unsafe member: ' + name)
        files.append((name, path))
    # Capture exact bytes, then verify this private image as well as the still-current tree.
    with tempfile.TemporaryDirectory(prefix='v124-package-') as temporary:
        stage = Path(temporary)
        for name, path in files:
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        # Baseline ZIPs are external prerequisites; no nested historical archives shipped.
        for v in BASELINES:
            shutil.copy2(root / (PREFIX + v + '.zip'), stage)
        require(read_json(stage / 'evidence/v12.4/validation.json') == state, 'Acceptance changed during copy')
        verify(stage)
        verify(root)
        entries = {name: sha(stage / name) for name, _ in files}
        manifest_name = 'evidence/v12.4/manifest.sha256'
        require(manifest_name not in entries, 'Generated manifest must not be a stale input')
        manifest = ''.join(value + '  ' + name + '\n' for name, value in sorted(entries.items()))
        output = stage / 'checkpoint.zip'
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=False) as z:
            for name in sorted(entries):
                z.write(stage / name, name)
            z.writestr(manifest_name, manifest)
        with zipfile.ZipFile(output) as z:
            require(z.testzip() is None, 'ZIP CRC failure')
            for name, value in entries.items():
                require(digest(z.read(name)) == value, 'ZIP member mismatch: ' + name)
            require(digest(z.read(WASM)) == state['wasm_sha256'], 'ZIP WASM mismatch')
        verify(root)
        # Exclusive create prevents replacing an independently sealed archive.
        with archive.open('xb') as stream:
            stream.write(output.read_bytes())
        archive_hash = sha(archive)
        with sidecar.open('x') as stream:
            stream.write(archive_hash + '  ' + archive.name + '\n')
    receipt = dict(service_sha256=state['service_sha256'], archive=str(archive), sha256=archive_hash, wasm_sha256=state['wasm_sha256'],
                   run_id=state['run_id'], input_fingerprint=state['input_fingerprint'],
                   manifest_entries=len(entries), status='accepted')
    write_json(root / 'evidence/v12.4/package-result.json', receipt)
    print(json.dumps(receipt, indent=2))
    return receipt

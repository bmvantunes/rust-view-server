"""Deterministic orchestration fixtures, not product acceptance evidence.

The separate compiler-negative gate runs real pinned CI and both CLI entrypoints.
"""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acceptance_v81 as a


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='v81-unit-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'browser/node_modules').mkdir(parents=True)
        for name in ['native/src/lib.rs', 'ingestion/src/lib.rs', 'native/tests/contract.rs',
                     'native/Cargo.lock', 'ingestion/Cargo.lock', 'browser/pnpm-lock.yaml',
                     'native/build.rs', 'scripts/build-wasm-v8.1.py', 'clippy.toml']:
            self.put(name, 'fixture input\n')
        for v in a.BASELINES:
            self.put(a.PREFIX + v + '.zip', v)
        self.baselines = {v: a.sha(self.root / (a.PREFIX + v + '.zip')) for v in a.BASELINES}
        self.patch = patch.object(a, 'BASELINES', self.baselines)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.put(a.WASM, 'fixture wasm')
        self.put('browser/public/product_core.sha256', a.sha(self.root / a.WASM) + '\n')
        self.state = self.green()

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def green(self):
        state = a.begin(self.root)
        run = self.root / 'evidence/v8.1/runs' / state['run_id']
        manifest = a.inputs(self.root)
        state.update(input_fingerprint=a.fingerprint(manifest), baseline_sha256=self.baselines,
                     status='accepted', not_run=[], wasm_sha256=a.sha(self.root / a.WASM))
        a.write_json(run / 'inputs.json', manifest)
        for name, command in a.GATES:
            header = dict(policy=a.POLICY, run_id=state['run_id'], gate=name, command=command,
                          input_fingerprint=state['input_fingerprint'])
            log = run / (name + '.log')
            body = json.dumps({'wasm_sha256': state['wasm_sha256'], 'checks': [{'result_and_group_checks': 3006, 'pass': True}]}) if name == 'oracle' else 'FIXTURE RUNNER'
            log.write_text(json.dumps(header) + '\n' + body + '\nEXIT_STATUS=0\n')
            result = dict(header, status='executed', exit=0, started_ns=1, finished_ns=2, log_sha256=a.sha(log))
            if name in a.WASM_GATES:
                result.update(wasm_before=state['wasm_sha256'], wasm_after=state['wasm_sha256'])
            a.write_json(run / (name + '.json'), result)
            state['gates'].append(result)
        for name in a.REQUIRED_GENERATED:
            a.write_json(run / 'generated' / name, {})
        a.write_json(run / 'generated/evidence/v81-browser-runtime.json', {'wasmSha256': state['wasm_sha256']})
        a.write_json(run / 'generated/evidence/v81-wasm-build.json',
                     dict(run_id=state['run_id'], fresh_empty_target=True, exit=0, wasm_sha256=state['wasm_sha256']))
        (run / 'generated/logs/count-distinct-minimal-addendum.log').write_text('EXPECTED_DEFECT_EXIT=101\n')
        state['artifacts'] = {p.relative_to(run).as_posix(): a.sha(p) for p in a.walk(run)}
        a.write_json(self.root / 'evidence/v8.1/validation.json', state)
        a.write_json(run / 'validation.json', state)
        return state

    def rejected(self, state=None):
        path = self.root / 'evidence/v8.1/runs' / self.state['run_id'] / 'validation.json'
        before = path.read_bytes()
        try:
            if state is not None:
                a.write_json(path, state)
            with self.assertRaises((RuntimeError, FileNotFoundError)):
                a.verify(self.root, state)
        finally:
            path.write_bytes(before)

    def test_i_fresh_fixture_packages_and_is_immutable(self):
        with patch('builtins.print'):
            result = a.package(self.root)
        self.assertEqual(result['status'], 'accepted')
        with self.assertRaisesRegex(RuntimeError, 'Never overwrite'):
            a.package(self.root)

    def test_b_source_edit(self):
        self.put('ingestion/src/lib.rs', 'changed')
        self.rejected()

    def test_b_tests_only_edit(self):
        self.put('native/tests/contract.rs', 'changed test')
        self.rejected()

    def test_b_locks_and_build_configuration(self):
        for name in ['native/Cargo.lock', 'ingestion/Cargo.lock', 'browser/pnpm-lock.yaml',
                     'native/build.rs', 'scripts/build-wasm-v8.1.py', 'clippy.toml']:
            with self.subTest(name=name):
                old = (self.root / name).read_text()
                self.put(name, 'changed')
                self.rejected()
                self.put(name, old)

    def test_c_add_delete_and_executable_mode(self):
        added = self.put('native/src/new.rs', '// added')
        self.rejected()
        added.unlink()
        deleted = self.root / 'native/src/lib.rs'
        old = deleted.read_text()
        deleted.unlink()
        self.rejected()
        deleted.write_text(old)
        deleted.chmod(0o755)
        self.rejected()

    def test_d_missing_and_tampered_logs_and_results(self):
        run = self.root / 'evidence/v8.1/runs' / self.state['run_id']
        for name in ['native.log', 'native.json', 'generated/evidence/v81-browser-runtime.json', 'inputs.json']:
            with self.subTest(name=name):
                path = run / name
                old = path.read_bytes()
                path.unlink()
                self.rejected()
                path.write_bytes(old + b' ')
                self.rejected()
                path.write_bytes(old)

    def test_e_empty_missing_duplicate_or_forged_gate(self):
        for gates in [[], self.state['gates'][:-1], self.state['gates'] + [self.state['gates'][0]]]:
            state = copy.deepcopy(self.state)
            state['gates'] = gates
            self.rejected(state)
        state = copy.deepcopy(self.state)
        state['gates'][0]['status'] = 'reused'
        self.rejected(state)

    def test_d_cross_run_log_cannot_be_substituted(self):
        state = copy.deepcopy(self.state)
        state['gates'][0]['run_id'] = 'stale-run'
        self.rejected(state)

    def test_f_moving_tree_invalidates_run(self):
        def moving(command, cwd, env, log, header, monitor):
            self.put('native/src/lib.rs', 'changed during run')
            monitor()
        with patch.object(a, 'run_gate', moving), self.assertRaisesRegex(RuntimeError, 'inputs changed'):
            a.validate(self.root)
        self.rejected()
        self.assertEqual(a.read_json(self.root / 'evidence/v8.1/validation.json')['status'], 'failed')

    def test_g_unvalidated_wasm(self):
        self.put(a.WASM, 'different wasm')
        self.rejected()

    def test_g_browser_hash_disagrees_even_with_updated_artifact_digest(self):
        state = copy.deepcopy(self.state)
        name = 'generated/evidence/v81-browser-runtime.json'
        path = self.root / 'evidence/v8.1/runs' / state['run_id'] / name
        a.write_json(path, {'wasmSha256': 'wrong'})
        state['artifacts'][name] = a.sha(path)
        self.rejected(state)

    def test_h_begin_invalidates_prior_green(self):
        a.begin(self.root)
        self.rejected()

    def test_h_failed_and_interrupted_run_do_not_inherit_green(self):
        for exception, status in [(RuntimeError('fixture failed'), 'failed'), (KeyboardInterrupt(), 'interrupted')]:
            self.green()
            with patch.object(a, 'run_gate', side_effect=exception), self.assertRaises(type(exception)):
                a.validate(self.root)
            self.rejected()
            record = a.read_json(self.root / 'evidence/v8.1/validation.json')
            self.assertEqual(record['status'], status)
            self.assertNotIn('toolchain', record['not_run'])
            self.assertEqual(record['active_gate']['gate'], 'toolchain')
            self.assertEqual(record['active_gate']['status'], 'interrupted' if status == 'interrupted' else 'aborted')

    def test_h_preflight_failure_invalidates_prior_green(self):
        with patch.object(a, 'baselines', side_effect=RuntimeError('missing baseline')):
            with self.assertRaises(RuntimeError):
                a.validate(self.root)
        self.rejected()

    def test_a_compiler_failure_state_cannot_package(self):
        def failed(command, cwd, env, log, header, monitor):
            log.write_text(json.dumps(header) + '\nEXPECTED fixture compiler failure\nEXIT_STATUS=101\n')
            return 101
        with patch.object(a, 'run_gate', failed), patch('builtins.print'), self.assertRaisesRegex(RuntimeError, 'Gate failed'):
            a.validate(self.root)
        with self.assertRaisesRegex(RuntimeError, 'No accepted fresh'):
            a.package(self.root)

    def test_resume_rejected_by_actual_cli(self):
        script = Path(__file__).resolve().parents[1] / 'validate-v8.1.py'
        result = subprocess.run([sys.executable, str(script), '--resume'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments: --resume', result.stderr)

    def test_snapshot_changes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            manifest = a.inputs(self.root)
            a.snapshot(self.root, work, manifest)
            (work / 'native/src/lib.rs').write_text('snapshot changed')
            with self.assertRaisesRegex(RuntimeError, 'inputs changed'):
                a.unchanged(work, manifest)

    def test_missing_artifact_index_and_wrong_baseline(self):
        state = copy.deepcopy(self.state)
        del state['artifacts']['native.log']
        self.rejected(state)
        self.put(a.PREFIX + 'v7.zip', 'wrong archive')
        self.rejected()


if __name__ == '__main__':
    unittest.main()

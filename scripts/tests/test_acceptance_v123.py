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
import acceptance_v123 as a


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='v123-unit-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'browser/node_modules').mkdir(parents=True)
        for name in ['native/src/lib.rs', 'ingestion/src/lib.rs', 'native/tests/contract.rs',
                     'native/Cargo.lock', 'ingestion/Cargo.lock', 'browser/pnpm-lock.yaml',
                     'native/build.rs', 'scripts/build-wasm-v123.py', 'clippy.toml',
                     'scripts/v123-oracle.mjs', 'scripts/test-v123-oracle.mjs',
                     'scripts/test-v123-exact-values.mjs', 'scripts/test-v123-integer-admission.mjs',
                     'scripts/test-v123-integer-browser.mjs', 'native/src/product.rs', 'browser/src/product.remote.worker.ts']:
            self.put(name, 'fixture input\n')
        for v in a.BASELINES:
            self.put(a.PREFIX + v + '.zip', v)
        self.baselines = {v: a.sha(self.root / (a.PREFIX + v + '.zip')) for v in a.BASELINES}
        self.patch = patch.object(a, 'BASELINES', self.baselines)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.put('bin/view_server', 'fixture service')
        self.put('bin/view_server_faults', 'fixture faults')
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
        run = self.root / 'evidence/v12.3/runs' / state['run_id']
        manifest = a.inputs(self.root)
        state.update(input_fingerprint=a.fingerprint(manifest), baseline_sha256=self.baselines,
                     status='accepted', not_run=[], fault_service_sha256=a.sha(self.root / 'bin/view_server_faults'), service_sha256=a.sha(self.root / 'bin/view_server'), wasm_sha256=a.sha(self.root / a.WASM))
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
        a.write_json(run / 'generated/evidence/v123-browser-runtime.json', {'wasmSha256': state['wasm_sha256']})
        a.write_json(run / 'generated/evidence/v123-wasm-build.json',
                     dict(run_id=state['run_id'], fresh_empty_target=True, exit=0, wasm_sha256=state['wasm_sha256']))
        a.write_json(run / 'generated/evidence/v12.3/service-build.json', dict(exit=0, run_id=state['run_id'], binary_sha256=state['service_sha256']))
        a.write_json(run / 'generated/evidence/v123-remote.json', dict(status='passed', binary_sha256=state['service_sha256'], lifecycle_iterations=80))
        for name in ['barriers', 'browser-profile']:
            a.write_json(run / ('generated/evidence/v12.3/' + name + '.json'), dict(status='passed', run_id=state['run_id'], release_binary_sha256=state['service_sha256'], fault_binary_sha256=state['fault_service_sha256']))
        a.write_json(run / 'generated/evidence/v12.3/fault-service-build.json', dict(exit=0, run_id=state['run_id'], binary_sha256=state['fault_service_sha256']))
        a.write_json(run / 'generated/evidence/v12.3/profile-verification.json', dict(raw_sha256=a.sha(run / 'generated/evidence/v12.3/browser-profile.json')))
        oracle_paths = ['scripts/v123-oracle.mjs', 'scripts/test-v123-oracle.mjs']
        browser_paths = ['scripts/v123-oracle.mjs', 'scripts/test-v123-exact-values.mjs', 'browser/src/product.remote.worker.ts']
        cases = [dict(name=name, **{k: True for k in ['fresh_wasm_matches_fixed_expected',
                 'historical_rejects_correct', 'historical_accepts_poison',
                 'repaired_accepts_correct', 'repaired_rejects_poison', 'live_ledger_rejects_poison']})
                 for name in ['descending-ties', 'scale-floor', 'unicode-id-ties']]
        a.write_json(run / 'generated/evidence/v12.3/oracle-regressions.json', dict(status='passed',
                     run_id=state['run_id'], wasm_sha256=state['wasm_sha256'],
                     historical_archive_sha256=self.baselines['v12.1'], cases=cases,
                     equivalent_source_noop=dict(fresh_wasm_version=2,historical_rejects_correct=True,historical_accepts_poison=True,repaired_accepts_correct=True,repaired_rejects_poison=True),
                     source_hashes={p: a.sha(self.root / p) for p in oracle_paths}))
        a.write_json(run / 'generated/evidence/v12.3/exact-values.json', dict(status='passed',
                     run_id=state['run_id'], release_binary_sha256=state['service_sha256'],
                     oracle={'live':4}, equivalent_source_noop={'no_live_publication':True}, poisoning_rejected=[c['name'] for c in cases],
                     source_hashes={p: a.sha(self.root / p) for p in browser_paths}))
        integer_paths = ['scripts/v123-oracle.mjs', 'scripts/test-v123-integer-admission.mjs', 'native/src/product.rs']
        integer_browser_paths = ['scripts/v123-oracle.mjs', 'scripts/test-v123-integer-browser.mjs', 'browser/src/product.remote.worker.ts']
        a.write_json(run / 'generated/evidence/v12.3/integer-admission.json', dict(status='passed',
                     run_id=state['run_id'], wasm_sha256=state['wasm_sha256'],
                     historical_archive_sha256=self.baselines['v12.2'], invalidCases=44, equivalentVersionChecked=True,
                     cases=[dict(wasmMatchesFixedExpected=True, repairedAccepts=True, poisonRejected=True,
                                 historicalRejectsAdmitted=i<10) for i in range(26)],
                     source_hashes={p: a.sha(self.root / p) for p in integer_paths}))
        a.write_json(run / 'generated/evidence/v12.3/integer-browser.json', dict(status='passed',
                     run_id=state['run_id'], release_binary_sha256=state['service_sha256'],
                     historical_archive_sha256=self.baselines['v12.2'], oracle={'live': 1},
                     historicalRejectsCorrect=True, poisonedValueRejected=True, poisonedVersionRejected=True,
                     equivalentSourceNoop=True, finalZeroSubscriptions=True,
                     source_hashes={p: a.sha(self.root / p) for p in integer_browser_paths}))
        (run / 'generated/logs/count-distinct-minimal-addendum.log').write_text('EXPECTED_DEFECT_EXIT=101\n')
        state['artifacts'] = {p.relative_to(run).as_posix(): a.sha(p) for p in a.walk(run)}
        a.write_json(self.root / 'evidence/v12.3/validation.json', state)
        a.write_json(run / 'validation.json', state)
        return state

    def rejected(self, state=None):
        path = self.root / 'evidence/v12.3/runs' / self.state['run_id'] / 'validation.json'
        before = path.read_bytes()
        try:
            if state is not None:
                a.write_json(path, state)
            with self.assertRaises((RuntimeError, FileNotFoundError)):
                a.verify(self.root, state)
        finally:
            path.write_bytes(before)

    def test_oracle_binding_and_negatives_cannot_be_forged_by_rehashing(self):
        for filename, field, value in [('integer-admission', 'wasm_sha256', 'wrong'),
                                       ('integer-admission', 'cases', []),
                                       ('integer-admission', 'invalidCases', 0),
                                       ('integer-browser', 'poisonedValueRejected', False),
                                       ('integer-browser', 'source_hashes', {}),
                                       ('integer-browser', 'release_binary_sha256', 'wrong'),
                                       ('oracle-regressions', 'wasm_sha256', 'wrong'),
                                       ('oracle-regressions', 'cases', []),
                                       ('oracle-regressions', 'source_hashes', {}),
                                       ('exact-values', 'run_id', 'wrong'),
                                       ('exact-values', 'release_binary_sha256', 'wrong'),
                                       ('exact-values', 'poisoning_rejected', [])]:
            state = copy.deepcopy(self.state)
            name = 'generated/evidence/v12.3/' + filename + '.json'
            path = self.root / 'evidence/v12.3/runs' / state['run_id'] / name
            original = path.read_bytes()
            record = a.read_json(path)
            record[field] = value
            a.write_json(path, record)
            state['artifacts'][name] = a.sha(path)
            try:
                self.rejected(state)
            finally:
                path.write_bytes(original)

    def test_stage0_evidence_is_authoritative_input(self):
        self.put('evidence/v13-stage0/review.json', 'changed review')
        self.rejected()

    def test_measurement_evidence_is_authoritative_input(self):
        self.put('evidence/v12/measurements/raw.jsonl', 'changed measurement')
        self.rejected()

    def test_historical_v10_policy_is_not_v123_acceptance(self):
        state = copy.deepcopy(self.state)
        state['policy'] = 'v10-fresh-snapshot-1'
        self.rejected(state)

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
                     'native/build.rs', 'scripts/build-wasm-v123.py', 'clippy.toml']:
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
        run = self.root / 'evidence/v12.3/runs' / self.state['run_id']
        for name in ['native.log', 'native.json', 'generated/evidence/v123-browser-runtime.json', 'inputs.json']:
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
        self.assertEqual(a.read_json(self.root / 'evidence/v12.3/validation.json')['status'], 'failed')

    def test_g_unvalidated_wasm(self):
        self.put(a.WASM, 'different wasm')
        self.rejected()

    def test_g_browser_hash_disagrees_even_with_updated_artifact_digest(self):
        state = copy.deepcopy(self.state)
        name = 'generated/evidence/v123-browser-runtime.json'
        path = self.root / 'evidence/v12.3/runs' / state['run_id'] / name
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
            record = a.read_json(self.root / 'evidence/v12.3/validation.json')
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
        script = Path(__file__).resolve().parents[1] / 'validate-v123.py'
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

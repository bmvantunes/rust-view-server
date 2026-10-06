#!/usr/bin/env python3
"""Verify selected qualification evidence without Kafka; emit a delivery manifest."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/kill-sqlite'
RUNS = {
    'crash_browser': '65dece25-f2f5-42f7-a338-702105d357c9',
    'adversarial': '71f1321c-9f79-491e-8d53-963a6c6c6dc4',
    'producer_fencing': '73407ada-f715-451d-b65d-90746a76b131',
    'benchmark_10k': '4534d249-00d7-4249-b40d-4f88465d7178',
    'benchmark_100k': 'c861861f-07ad-4335-a110-5294d0775d0e',
    'delete_retention': '0a694146-0cbc-42a1-b4f2-b1e554a8cb8a',
    'same_executable': '23bd8ff5-8c40-444b-915e-a6c8c5e4f3bb',
}
RUNTIME_MAP = {
    'view_server': 'view_server_kafka',
    'view_server_faults': 'view_server_kafka_faults',
    'kafka_probe': 'kafka_state_probe',
    'kafka_fencing': 'kafka_fencing_probe',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def local_binding(name):
    if name.startswith('/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime/'):
        return ROOT / 'bin' / RUNTIME_MAP[Path(name).name]
    marker = '/followups/rust-differential-product-20260929/'
    return ROOT / name.split(marker, 1)[1]

summary = {'qualification': 'local-single-whole-topic-owner', 'runs': {},
           'baseline_unchanged': {}, 'baseline_changed': {}, 'binaries': {},
           'regressions': {}, 'benchmarks': []}
for name, run_id in RUNS.items():
    run = EVIDENCE / ('run-' + run_id)
    bindings = json.loads((run / 'bindings-start.json').read_text())
    for recorded, digest in bindings.items():
        path = local_binding(recorded)
        assert sha(path) == digest, f'Binding changed: {run_id}: {path}'
    checks = json.loads((run / 'checks.json').read_text())
    assert checks and any(c.get('passed') is True for c in checks), run_id
    assert all(c.get('passed', True) is not False for c in checks), run_id
    assert all(not c.get('created_files', []) for c in checks), run_id
    summary['runs'][name] = {
        'directory': str(run.relative_to(ROOT)),
        'verified_bindings': len(bindings),
        'passed_assertions': [c['name'] for c in checks if c.get('passed') is True],
    }
    resources_path = run / 'resources.json'
    if resources_path.exists():
        resources = json.loads(resources_path.read_text())
        for c in checks:
            if not c['name'].endswith('-ready') or c['name'].startswith(('seed', 'cleaner')):
                continue
            process = c['name'][:-6]
            samples = [r for r in resources if r['process'] == process and r['elapsed'] <= c['seconds']]
            metrics = next(e['metrics'] for e in c['events'] if e['state'] == 'restore_proven')
            def cpu(r):
                minutes, seconds = r['rss_cpu'].split()[1].split(':')
                return int(minutes) * 60 + float(seconds)
            summary['benchmarks'].append({
                'process': process, 'start_to_ready_seconds': c['seconds'],
                'startup_peak_rss_kib': max(int(r['rss_cpu'].split()[0]) for r in samples),
                'startup_cpu_seconds': max(cpu(r) for r in samples), 'metrics': metrics,
            })

expected_changes = {
    'ingestion/src/durable.rs', 'ingestion/src/durable_coordinator.rs',
    'ingestion/src/faults.rs', 'ingestion/src/lib.rs', 'ingestion/src/bin/view_server.rs',
}
for line in (EVIDENCE / 'baseline.sha256').read_text().splitlines():
    digest, relative = line.split('  ', 1)
    actual = sha(ROOT / relative)
    if relative in expected_changes:
        summary['baseline_changed'][relative] = {'before': digest, 'after': actual}
    else:
        assert digest == actual, f'Unexpected baseline change: {relative}'
        summary['baseline_unchanged'][relative] = actual

for binary in RUNTIME_MAP.values():
    summary['binaries'][binary] = sha(ROOT / 'bin' / binary)
for relative, digest in {
    'browser/public/product_core.wasm': 'f0f6b6710525b06a31095a17a63e017842773893d1a7409599a6d03460c669e1',
    'browser/public/request_admission.wasm': 'a878e8f78c1c99637763987db48519c7bd6f260ba6cc0c12936eb3eea6d84b9d',
}.items():
    assert sha(ROOT / relative) == digest, f'Accepted WASM changed: {relative}'
    summary['baseline_unchanged'][relative] = digest
for log in ['final-ingestion-regressions.log', 'native-regressions.log', 'state-tests-final.log']:
    matches = re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored',
                         (EVIDENCE / log).read_text())
    assert matches and all(m[0] == 'ok' and int(m[2]) == 0 for m in matches), log
    summary['regressions'][log] = {
        'summaries': len(matches), 'reported_passes': sum(int(m[1]) for m in matches),
        'failed': 0, 'ignored': sum(int(m[3]) for m in matches),
    }
proofs = list((EVIDENCE / ('run-' + RUNS['same_executable'])).glob('*-sandbox-proof.json'))
assert len(proofs) >= 6
for path in proofs:
    proof = json.loads(path.read_text())
    assert proof['write_denied'] != 0
    assert all(p['returncode'] != 0 for p in proof['prior_directory_reads_denied'])
summary['filesystem_denial_proofs'] = len(proofs)
summary['cleanup'] = json.loads((EVIDENCE / 'cleanup.json').read_text())
assert all(p['stopped'] for p in summary['cleanup'])
(EVIDENCE / 'final-summary.json').write_text(json.dumps(summary, indent=2) + '\n')

files = set()
for pattern in ['ingestion/src/**/*.rs', 'ingestion/tests/*.rs', 'ingestion/examples/*.rs',
                'ingestion/Cargo.*', 'native/src/*.rs', 'browser/src/product.remote.worker.ts',
                'browser/src/product-provider.tsx', 'scripts/*kill-sqlite*',
                'reports/KILL-SQLITE-*', 'bin/*kafka*', 'bin/view_server',
                'bin/view_server_faults', 'browser/public/*.wasm']:
    files.update(p for p in ROOT.glob(pattern) if p.is_file())
for run_id in RUNS.values():
    files.update(p for p in (EVIDENCE / ('run-' + run_id)).rglob('*') if p.is_file())
files.update(p for p in EVIDENCE.iterdir() if p.is_file() and p.name != 'final-manifest.sha256')
(EVIDENCE / 'final-manifest.sha256').write_text(''.join(
    f'{sha(p)}  {p.relative_to(ROOT)}\n' for p in sorted(files)))
print(json.dumps({'selected_runs': len(RUNS), 'filesystem_proofs': len(proofs),
                  'manifest_files': len(files), 'binaries': summary['binaries'],
                  'verified': True}, indent=2))

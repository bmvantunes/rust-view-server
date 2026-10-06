"""Reproduce the historical defect ONLY in a disposable reviewed-v8 extraction."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile, zipfile
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'evidence/v8.1/reproduction'
PREFIX = 'rust-differential-product-20260929-review-checkpoint-'
BASELINES = {'v8': '9d40ce674cd6d16d6e8ddf3dc3f44ceef59b06f07ca76c6af2976f4783516203',
             'v7': 'fb2d8b6601a2ce44d75ffe1bd94803550226e71a5f04e7ce042e25147654260a'}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for version, digest in BASELINES.items():
        assert hashlib.sha256((ROOT / (PREFIX + version + '.zip')).read_bytes()).hexdigest() == digest
    with tempfile.TemporaryDirectory(prefix='v81-historical-red-') as directory:
        work = Path(directory)
        with zipfile.ZipFile(ROOT / (PREFIX + 'v8.zip')) as archive:
            archive.extractall(work)
        shutil.copy2(ROOT / (PREFIX + 'v7.zip'), work)
        source = work / 'ingestion/src/lib.rs'
        source.write_text(source.read_text() + '\ncompile_error!("INDEPENDENT_REVIEW_RESUME_PROBE_DO_NOT_SHIP");\n')
        results = {}
        for name, command in [('validate', ['python3', 'scripts/validate-v8.py', '--resume']),
                              ('package', ['python3', 'scripts/package-v8.py'])]:
            result = subprocess.run(command, cwd=work, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (OUT / (name + '.log')).write_text(result.stdout)
            results[name] = {'command': command, 'exit': result.returncode}
            assert result.returncode == 0, result.stdout
        results['reused_gates'] = (OUT / 'validate.log').read_text().count('reuse passing gate')
        with zipfile.ZipFile(work / (PREFIX + 'v8.zip')) as archive:
            assert b'INDEPENDENT_REVIEW_RESUME_PROBE_DO_NOT_SHIP' in archive.read('ingestion/src/lib.rs')
            entries = archive.read('evidence/v8/manifest.sha256').decode().splitlines()
            for line in entries:
                digest, member = line.split('  ', 1)
                assert hashlib.sha256(archive.read(member)).hexdigest() == digest
        assert results['reused_gates'] == 15 and len(entries) == 1173
        results.update(poisoned_member_verified=True, verified_manifest_entries=len(entries),
                       poisoned_source_and_archive='Destroyed with disposable directory',
                       review_attachment='Absent; reproduced from supplied task, not missing reviewer material')
        (OUT / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()

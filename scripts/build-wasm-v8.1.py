"""Force an actual release compilation into a new empty target directory."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, tempfile
root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='v81-wasm-target-') as target:
    assert not list(Path(target).iterdir())
    env = os.environ.copy()
    env.update(CARGO_TARGET_DIR=target, CARGO_BUILD_JOBS='1',
               RUSTC=subprocess.check_output(['rustup', 'which', '--toolchain', '1.96.1', 'rustc'], text=True).strip())
    command = ['rustup', 'run', '1.96.1', 'cargo', 'build', '--locked', '--offline', '--release',
               '--target', 'wasm32-unknown-unknown', '--manifest-path', 'native/Cargo.toml', '--lib']
    print('COMMAND ' + json.dumps(command), flush=True)
    result = subprocess.run(command, cwd=root, env=env)
    result.check_returncode()
    wasm = root / 'browser/public/product_core.wasm'
    wasm.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(target) / 'wasm32-unknown-unknown/release/rust_differential_product_core.wasm', wasm)
    value = hashlib.sha256(wasm.read_bytes()).hexdigest()
    (wasm.parent / 'product_core.sha256').write_text(value + '\n')
    report = dict(command=command, run_id=os.environ['ACCEPTANCE_RUN_ID'], exit=result.returncode,
                  fresh_empty_target=True, wasm_sha256=value)
    (root / 'evidence/v81-wasm-build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

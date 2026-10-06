from pathlib import Path
import os,subprocess
root=Path(__file__).resolve().parent.parent
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,CARGO_TARGET_DIR='/private/tmp/v131-codec-target')
subprocess.run(['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','experiments/v131/codec/Cargo.toml'],cwd=root,env=env,check=True)

env['CARGO_TARGET_DIR']='/private/tmp/rust-differential-product-wasm-20260929-target'
subprocess.run(['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--target','wasm32-unknown-unknown','--manifest-path','admission/Cargo.toml','--lib'],cwd=root,env=env,check=True)
import shutil
shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'wasm32-unknown-unknown/release/product_request_admission.wasm',root/'browser/public/request_admission.wasm')

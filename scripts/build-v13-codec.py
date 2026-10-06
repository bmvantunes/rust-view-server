from pathlib import Path
import os,subprocess
root=Path(__file__).resolve().parent.parent
rustc=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip()
env=dict(os.environ,RUSTC=rustc,CARGO_TARGET_DIR='/private/tmp/v13-codec-target')
subprocess.run(['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path','experiments/v13/codec/Cargo.toml'],cwd=root,env=env,check=True)

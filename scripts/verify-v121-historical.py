"""Reverify immutable V12 arithmetic against its own source, never new-source evidence."""
from pathlib import Path
import zipfile,tempfile,subprocess,hashlib
root=Path(__file__).resolve().parent.parent
archive=root/'rust-differential-product-20260929-review-checkpoint-v12.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ef1f1c4d7319ab95cdfdf0de608e04ecba0cdb58cbe7b1211360535abac58731'
with tempfile.TemporaryDirectory(prefix='v121-historical-') as tmp:
 with zipfile.ZipFile(archive) as z:z.extractall(tmp)
 subprocess.run(['python3','scripts/verify-v12-measurements.py'],cwd=tmp,check=True)
print('Historical V12 measurement integrity only; current release profile is a separate fresh gate.')

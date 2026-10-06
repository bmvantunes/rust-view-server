from pathlib import Path
from acceptance_v13 import lock,package
root=Path(__file__).resolve().parent.parent
with lock(root):package(root)

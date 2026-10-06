"""Final acceptance always executes every gate; --resume is intentionally unsupported."""
import argparse
from pathlib import Path
from acceptance_v121 import lock, validate

if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parent.parent
    with lock(root):
        validate(root)

"""Seal only a complete fresh run whose tested inputs and evidence still match."""
import argparse
from pathlib import Path
from acceptance_v12 import lock, package

if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parent.parent
    with lock(root):
        package(root)

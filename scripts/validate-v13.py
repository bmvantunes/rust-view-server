import argparse
from pathlib import Path
from acceptance_v13 import lock,validate
if __name__=='__main__':
 argparse.ArgumentParser(description='Fresh-only V13 acceptance; no resume.').parse_args()
 root=Path(__file__).resolve().parent.parent
 with lock(root):validate(root)

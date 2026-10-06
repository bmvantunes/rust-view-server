#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={}
for root in ['native','ingestion','admission','browser/src','proto','examples/schema-expansion','scripts']:
 for p in (W/root).rglob('*'):
  if p.is_file()and not any(v in p.parts for v in ['node_modules','target','__pycache__','__screenshots__'])and(p.suffix in ['.rs','.ts','.tsx','.mjs','.py','.sh','.proto']or p.name in ['Cargo.toml','Cargo.lock']):source[str(p.relative_to(W))]=sha(p)
artifacts={str(p.relative_to(W)):sha(p)for root in ['fixtures/expanded-topics','build/grouped']for p in (W/root).rglob('*')if p.is_file()}
for n in ['view_server_expanded','view_server_expanded_faults','generic_kafka_producer_expanded']:artifacts['bin/'+n]=sha(W/'bin'/n)
result={'source_sha256':dict(sorted(source.items())),'generated_browser_native_sha256':dict(sorted(artifacts.items())),'compiler':'rustc 1.96.1 (31fca3adb 2026-06-26), explicit RUSTC/RUSTDOC; build receipts retained','base_sha256':'e202466bc8e0c3b51a89963789802f812e3dc481b594330efe63d0818e239465','retention_overlay_sha256':'3261f464757531d2283586f53c16154bea66232eed82d4ec983b05f6e5676fd0'}
(W/'SCHEMA-EXPANSION-IDENTITIES.json').write_text(json.dumps(result,indent=2)+'\n')
print('Bound',len(source),'sources and',len(artifacts),'artifacts')

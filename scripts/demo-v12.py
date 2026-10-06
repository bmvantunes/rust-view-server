"""Finite loopback fixture demo; all data/config live in a temporary directory."""
from pathlib import Path
import json,os,secrets,subprocess,tempfile
root=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='v12-demo-') as tmp:
 p=Path(tmp);feed=p/'fixture.jsonl'
 rows=[{'partition':0,'offset':i,'mutation':{'kind':'upsert','row':{'id':f'row-{i}','category':'a','label':{'state':'value','value':'deterministic fixture'},'quantity':'9223372036854775807','amount':{'coefficient':str(v),'scale':2}}}} for i,v in enumerate([-1001,-201,-201])]
 feed.write_text(''.join(json.dumps(r)+'\n' for r in rows));token=secrets.token_hex(24)
 config={'bind':'127.0.0.1:8765','origin':'http://127.0.0.1:5173','database':str(p/'canonical.db'),'source':{'incarnation':'v12-demo-fixture','topic':'products','schema':'product-v1'},'expected_partitions':[0],'mode':{'kind':'fixture','path':str(feed)},'run_ms':300000,'stop_file':str(p/'stop')}
 path=p/'config.json';path.write_text(json.dumps(config));print('Finite five-minute deterministic fixture. Client token is stored only in '+str(p/'session-token')+'. Read it locally; never place it in a URL.',flush=True);(p/'session-token').write_text(token);(p/'session-token').chmod(0o600)
 subprocess.run([str(root/'bin/view_server'),str(path)],env=dict(os.environ,V12_SESSION_TOKEN=token),check=True)

"""Read-only bounded preflight; never uses a supplied broker endpoint or starts a user service."""
from pathlib import Path
import subprocess,platform,json,shutil
root=Path(__file__).resolve().parent.parent
commands=[]
for cmd in [['docker','info','--format','{{.ServerVersion}} {{.OSType}}'],['java','-version'],['uname','-a']]:
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=15);commands.append({'command':cmd,'exit':r.returncode,'output':r.stdout+r.stderr})
 except (OSError,subprocess.TimeoutExpired) as e:commands.append({'command':cmd,'error':str(e)})
r={'host':platform.platform(),'commands':commands,'real_broker':{'status':'BLOCKED / NOT RUN','reason':'No running Docker daemon or Java runtime; no isolated broker available. No user cluster contacted.'},'linux':{'status':'NOT RUN','reason':'macOS host; configured Linux container runtime unavailable.'},'mock':'Separate freshly executed product gate; not a real broker substitute.'}
assert platform.system()=='Darwin'
assert commands[0].get('exit',1)!=0 and commands[1].get('exit',1)!=0,'Environment changed: reassess isolated real broker/Linux gate'
p=root/'evidence/v12-environment.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

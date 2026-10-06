from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parent.parent
for version in ['v11','v12','current']:
 path=root/('evidence/v12.2/quota-'+version+'.json')
 command=['node','scripts/probe-v122-quota.mjs',str(path)]
 if version!='current':command+=['--baseline='+version]
 subprocess.run(command,cwd=root,check=True)
 outcomes=json.loads(path.read_text())['outcomes']
 assert outcomes[0]['admitted']==(16 if version=='v12' else 20)
 if version!='v11':assert outcomes[1]['admitted']==16 and outcomes[1]['error']=='subscription budget exceeded'

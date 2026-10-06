from pathlib import Path
import os,json
from verify_v13_record import check
root=Path(__file__).resolve().parent.parent
result=check(root,root/'evidence/v13',os.environ.get('ACCEPTANCE_RUN_ID'))
(root/'evidence/v13/evidence-binding.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)

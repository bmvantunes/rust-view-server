from pathlib import Path
import os,json
from verify_v131_record import check
root=Path(__file__).resolve().parent.parent
result=check(root,root/'evidence/v13.1',os.environ.get('ACCEPTANCE_RUN_ID'))
(root/'evidence/v13.1/evidence-binding.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)

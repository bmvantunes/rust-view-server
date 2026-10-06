"""Acceptance-control regressions, not substitutes for native/browser execution."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import acceptance_v13 as a
import acceptance_v124 as old

class V13Acceptance(unittest.TestCase):
 def test_preserves_every_original_gate_and_adds_fixed_qualification(self):
  self.assertEqual(a.GATES[:34],old.GATES)
  self.assertEqual([n for n,_ in a.GATES[34:]],['codec-build','candidate-builds','candidate-qualification','measurement-verification','v13-evidence-binding'])
 def test_source_lock_mode_and_measurements_invalidate(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   paths=['native/src/lib.rs','experiments/v13/package-lock.json','scripts/profile-v13-pipeline.mjs','evidence/v13/pipeline-json-mixed-compat-0.json']
   for p in paths:
    target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('initial')
   manifest=a.inputs(root);self.assertEqual(set(manifest),set(paths))
   for p in paths:
    target=root/p;target.write_text('poison')
    with self.assertRaisesRegex(RuntimeError,'Authoritative inputs changed'):a.unchanged(root,manifest)
    target.write_text('initial')
   target=root/paths[0];target.chmod(0o755)
   with self.assertRaises(RuntimeError):a.unchanged(root,manifest)
 def test_old_evidence_not_recursively_current_input(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for p in ['evidence/v12.4/runs/old/validation.json','evidence/v13/pipeline-protobuf-mixed-compat--4.json','evidence/v13/validation.json']:
    t=root/p;t.parent.mkdir(parents=True,exist_ok=True);t.write_text('{}')
   self.assertEqual(a.inputs(root),{})
 def test_failed_or_incomplete_state_cannot_package(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'evidence/v13/validation.json';p.parent.mkdir(parents=True)
   for state in [{'policy':a.POLICY,'status':'failed'},{'policy':a.POLICY,'status':'accepted','reused':1},{'policy':a.POLICY,'status':'accepted','reused':0,'not_run':['native']}]:
    p.write_text(json.dumps(state))
    with self.assertRaises(RuntimeError):a.verify(root)

if __name__=='__main__':unittest.main()

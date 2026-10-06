"""V13.1 acceptance controls; actual peer tests are separate fixed gates."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import acceptance_v131 as a
import acceptance_v124 as old
from verify_v131_record import bind_measurement_sources
class V131Acceptance(unittest.TestCase):
 def test_preserves_34_commands_and_fresh_binary_gates(self):
  self.assertEqual(a.GATES[:34],old.GATES)
  self.assertEqual([name for name,_ in a.GATES[34:]],['codec-build','candidate-builds','candidate-qualification','measurement-verification','production-selection','v131-evidence-binding'])
 def test_all_admission_rule_measurement_and_measured_artifact_inputs_are_bound(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);names=['admission/src/lib.rs','admission/Cargo.lock','browser/src/request-admission.ts','CODEC-DECISION-RULE.md','PRODUCTION-CODEC.json','experiments/v131/js/values.mjs','scripts/v131-browser-support.mjs','evidence/v13.1/pipeline-msgpack-mixed-compat-0.json','evidence/v13.1/measured-artifacts/msgpack/bin/view_server']
   for name in names:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('before')
   manifest=a.inputs(root);self.assertEqual(set(manifest),set(names))
   for name in names:
    p=root/name;p.write_text('poison')
    with self.assertRaisesRegex(RuntimeError,'Authoritative inputs changed'):a.unchanged(root,manifest)
    p.write_text('before')
 def test_failed_attempts_are_not_measurement_inputs_or_accepted_runs(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ['evidence/v13/pipeline-msgpack-mixed-compat-0.json','evidence/v13.1/development/measurement-attempt-1/pipeline-msgpack-mixed-compat-0.json']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
   self.assertEqual(a.inputs(root),{})
   p=root/'evidence/v13.1/validation.json';p.parent.mkdir(parents=True,exist_ok=True)
   for state in [{'policy':a.POLICY,'status':'failed'},{'policy':a.POLICY,'status':'accepted','reused':1},{'policy':a.POLICY,'status':'accepted','reused':0,'not_run':['production-selection']}]:
    p.write_text(json.dumps(state))
    with self.assertRaises(RuntimeError):a.verify(root)
 def test_measured_wasm_binding_never_substitutes_a_rebuilt_image(self):
  wasm='browser/public/request_admission.wasm';source='admission/src/lib.rs'
  raw={'source_hashes':{wasm:'measured',source:'same-source'}}
  rebuilt={'sha256':{wasm:'fresh-build',source:'same-source'}}
  measured={'sha256':{wasm:'measured'}}
  bind_measurement_sources(Path('/unused'),raw,rebuilt,measured)
  for poisoned in ['fresh-build','different-image']:
   with self.assertRaises(AssertionError):
    bind_measurement_sources(Path('/unused'),{'source_hashes':{wasm:poisoned}},rebuilt,measured)
  with self.assertRaises(AssertionError):
   bind_measurement_sources(Path('/unused'),raw,{'sha256':{wasm:'fresh-build',source:'changed-source'}},measured)
if __name__=='__main__':unittest.main()

"""Exact candidate17 prepared-proof transition; no generic JSON/Python approval."""
from pathlib import Path
import importlib.util
import unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('overlay_proof_transition',HERE/'stage_practice153.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class PreparedProof(unittest.TestCase):
 def test_two_exact_reviewed_transitions(self):
  for name,(old_path,old_sha,new_path,new_sha) in stage.prepared_overlay_proof_specs().items():
   self.assertTrue(stage.prepared_overlay_proof_target(name,new_path,new_sha,17))
   self.assertTrue(stage.prepared_overlay_proof_transition(name,{'path':str(old_path),'sha256':old_sha},new_path,new_sha,{name:new_sha},17))
   self.assertFalse(stage.source_review_allowed(name,new_path,17))
 def test_only_transition_candidate17_exact_target_continues(self):
  for name,(old_path,old_sha,new_path,new_sha) in stage.prepared_overlay_proof_specs().items():
   for candidate in (16,18,20):
    self.assertEqual(stage.prepared_overlay_proof_target(name,new_path,new_sha,candidate),candidate>=17)
    self.assertFalse(stage.prepared_overlay_proof_transition(name,{'path':str(old_path),'sha256':old_sha},new_path,new_sha,{name:new_sha},candidate))
 def test_wrong_new_hash(self):
  for name,(_,_,path,digest) in stage.prepared_overlay_proof_specs().items():
   changed=('1' if digest[0]!='1' else '2')+digest[1:]
   self.assertFalse(stage.prepared_overlay_proof_target(name,path,changed,17))
 def test_wrong_new_path(self):
  for name,(_,_,path,digest) in stage.prepared_overlay_proof_specs().items():
   self.assertFalse(stage.prepared_overlay_proof_target(name,HERE/'other-proof.json',digest,17))
 def test_unknown_json_and_python(self):
  for name,path in [('otherProof',HERE/'unreviewed.json'),('otherBuilder',HERE/'unreviewed.py')]:
   self.assertFalse(stage.prepared_overlay_proof_target(name,path,'0'*64,17))
   self.assertFalse(stage.source_review_allowed(name,path,17))
 def test_old_hash_must_match(self):
  for name,(old_path,_,path,digest) in stage.prepared_overlay_proof_specs().items():
   self.assertFalse(stage.prepared_overlay_proof_transition(name,{'path':str(old_path),'sha256':'f'*64},path,digest,{name:digest},17))
 def test_old_path_must_match(self):
  for name,(_,old_sha,path,digest) in stage.prepared_overlay_proof_specs().items():
   self.assertFalse(stage.prepared_overlay_proof_transition(name,{'path':str(HERE/'different.json'),'sha256':old_sha},path,digest,{name:digest},17))
 def test_explicit_review_required(self):
  for name,(old_path,old_sha,path,digest) in stage.prepared_overlay_proof_specs().items():
   old={'path':str(old_path),'sha256':old_sha}
   self.assertFalse(stage.prepared_overlay_proof_transition(name,old,path,digest,{},17))
   self.assertFalse(stage.prepared_overlay_proof_transition(name,old,path,digest,{name:'f'*64},17))
 def test_existing_python_scope_unchanged(self):
  self.assertTrue(stage.source_review_allowed('packetArchiverSource',HERE/'archive_practice153.py',17))
  self.assertTrue(stage.source_review_allowed('autoPreferencesContinuityWitnessSource',HERE/'check_auto_preferences_continuity153.py',17))
  self.assertFalse(stage.source_review_allowed('overlayStagerTestSource',HERE/'test_stage_overlay_resources.py',17))
if __name__=='__main__':unittest.main()

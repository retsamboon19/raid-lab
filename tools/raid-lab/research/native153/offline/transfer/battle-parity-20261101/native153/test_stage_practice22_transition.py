"""Bound22 and exact integration6-to7 admission; no stager main/native calls."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepared22_under_test',HERE/'stage_practice153.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class Prepared22(unittest.TestCase):
 def test_original_reference3_exact22_selection(self):
  selected=stage.prepare_reference_selection(22,3)
  self.assertEqual(selected['referenceRunIndex'],3)
  self.assertTrue(selected['proof']['inputBindingReady'])
  stage.verify_selected_reference_paths(selected['paths'],selected['proof'],3)
 def test23_rejected_before_any_source_access(self):
  with patch.object(stage,'sha',side_effect=AssertionError('must not read')):
   with self.assertRaises(ValueError):stage.prepare_reference_selection(23,3)
 def test_exact_current_proof_and_builder_targets(self):
  for name,(old,old_sha,new,new_sha) in stage.prepared22_proof_specs().items():
   self.assertTrue(stage.current_prepared_target(name,new,new_sha,22))
   self.assertTrue(stage.current_prepared_transition(name,{'path':str(old),'sha256':old_sha},new,new_sha,{name:new_sha},22))
   self.assertFalse(stage.source_review_allowed(name,new,22))
 def test_transition_only22(self):
  for name,(old,old_sha,new,new_sha) in stage.prepared22_proof_specs().items():
   for index in (21,23):self.assertFalse(stage.current_prepared_transition(name,{'path':str(old),'sha256':old_sha},new,new_sha,{name:new_sha},index))
 def test_exact_hash_path_and_explicit_review(self):
  for name,(old,old_sha,new,new_sha) in stage.prepared22_proof_specs().items():
   self.assertFalse(stage.current_prepared_transition(name,{'path':str(old),'sha256':'f'*64},new,new_sha,{name:new_sha},22))
   self.assertFalse(stage.current_prepared_transition(name,{'path':str(HERE/'other.json'),'sha256':old_sha},new,new_sha,{name:new_sha},22))
   self.assertFalse(stage.current_prepared_transition(name,{'path':str(old),'sha256':old_sha},HERE/'other.json',new_sha,{name:new_sha},22))
   self.assertFalse(stage.current_prepared_transition(name,{'path':str(old),'sha256':old_sha},new,new_sha,{},22))
   self.assertFalse(stage.current_prepared_target(name,new,'f'*64,22))
 def test_carried19_locale_proof_review_remains_exact(self):
  row=stage.prepared19_proof_specs()['localeNativeSourceProof']
  self.assertTrue(stage.current_prepared_target('localeNativeSourceProof',row[2],row[3],22))
  self.assertFalse(stage.current_prepared_transition('localeNativeSourceProof',{'path':str(row[0]),'sha256':row[1]},row[2],row[3],{'localeNativeSourceProof':row[3]},22))
 def test21_historical_paths_and22_new_paths(self):
  self.assertEqual(stage.original_overlay_source_paths(21)['overlayIntegrationProof'].name,'practice-overlay-rng-integration6.json')
  self.assertEqual(stage.original_overlay_source_paths(22)['overlayIntegrationProof'].name,'practice-overlay-rng-integration7.json')
  self.assertEqual(stage.original_overlay_source_paths(21)['overlayIntegrationBuilder'].name,'build_practice19_integration153.py')
  self.assertEqual(stage.original_overlay_source_paths(22)['overlayIntegrationBuilder'].name,'build_practice22_integration153.py')
 def test_no_unknown_python_or_json_review(self):
  for name,path in [('unknownHelper',HERE/'unknown.py'),('unknownProof',HERE/'unknown.json')]:
   self.assertFalse(stage.current_prepared_target(name,path,'a'*64,22))
   self.assertFalse(stage.source_review_allowed(name,path,22))
 def test_current_runtime_globals_and_dispatch_unchanged(self):
  self.assertEqual(stage.original_practice_dispatch(22),stage.original_practice_dispatch(21))
  a=stage.original_locale_runtime_values(stage.original_locale_paths(21));b=stage.original_locale_runtime_values(stage.original_locale_paths(22));self.assertEqual(a,b)
if __name__=='__main__':unittest.main()

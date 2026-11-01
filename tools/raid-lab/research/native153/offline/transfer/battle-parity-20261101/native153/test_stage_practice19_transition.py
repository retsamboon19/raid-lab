"""Candidate19 exact backpressure-repair admission; no stager/native execution."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("practice19_stage_tests",HERE/"stage_practice153.py")
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

class Candidate19(unittest.TestCase):
 def test_exact_five_transitions_and_explicit_review(self):
  self.assertEqual(len(stage.prepared19_proof_specs()),5)
  for name,(old,old_sha,new,new_sha) in stage.prepared19_proof_specs().items():
   prior={"path":str(old),"sha256":old_sha}
   self.assertTrue(stage.current_prepared_target(name,new,new_sha,19))
   self.assertTrue(stage.current_prepared_transition(name,prior,new,new_sha,{name:new_sha},19))
   for index in (18,20,21):
    self.assertFalse(stage.current_prepared_transition(name,prior,new,new_sha,{name:new_sha},index))
   for changed in ({}, {name:"0"*64}):
    self.assertFalse(stage.current_prepared_transition(name,prior,new,new_sha,changed,19))
   for field,value in (("path",str(HERE/"wrong")),("sha256","0"*64)):
    bad=dict(prior);bad[field]=value
    self.assertFalse(stage.current_prepared_transition(name,bad,new,new_sha,{name:new_sha},19))
   self.assertFalse(stage.current_prepared_target(name,HERE/"other",new_sha,19))
   self.assertFalse(stage.current_prepared_target(name,new,"0"*64,19))
   self.assertTrue(stage.current_prepared_target(name,new,new_sha,21))

 def test_legacy_targets_preserved_and_unknown_review_rejected(self):
  for name,(_,_,path,digest) in stage.prepared_overlay_proof_specs().items():
   self.assertTrue(stage.current_prepared_target(name,path,digest,18))
   self.assertFalse(stage.current_prepared_target(name,path,digest,19))
  for name,path in (("arbitraryJson",HERE/"x.json"),("arbitraryPython",HERE/"x.py"),("localeInput",HERE/"practice-localization-binding.json")):
   self.assertFalse(stage.source_review_allowed(name,path,19))
   self.assertFalse(stage.current_prepared_target(name,path,"0"*64,19))

 def aliases(self):
  paths=stage.original_locale_paths(19)
  old=json.loads((HERE/"practice-localization-source153.json").read_text())["inputs"]
  new=json.loads(paths["localeNativeSourceProof"].read_text())["inputs"]
  self.assertEqual(set(old),set(new))
  return paths,old,new

 def test_only_exact_two_proof_derived_locale_aliases_change(self):
  paths,old,new=self.aliases(); changed=[]
  for index,key in enumerate(sorted(old),1):
   if old[key]==new[key]:continue
   changed.append(key);name="localeNativeDependencyProof"+str(index);path=stage.ROOT/key
   prior={"path":str(path),"sha256":old[key]};review={"localeNativeSourceProof":stage.LOCALE19_PROOF_SHA}
   self.assertTrue(stage.locale19_dependency_transition(name,prior,path,new[key],paths,review,19))
   for candidate in (18,20,21):self.assertFalse(stage.locale19_dependency_transition(name,prior,path,new[key],paths,review,candidate))
   self.assertFalse(stage.locale19_dependency_transition(name,prior,path,new[key],paths,{},19))
   self.assertFalse(stage.locale19_dependency_transition(name,{**prior,"sha256":"0"*64},path,new[key],paths,review,19))
   self.assertFalse(stage.locale19_dependency_transition(name,prior,HERE/"wrong",new[key],paths,review,19))
   self.assertFalse(stage.locale19_dependency_transition(name,prior,path,"0"*64,paths,review,19))
   self.assertFalse(stage.locale19_dependency_transition(name+"1",prior,path,new[key],paths,review,19))
  self.assertEqual({Path(k).name for k in changed},{"practice_localization.js","test_practice_localization.js"})

 def test_dependency_key_shift_or_unrelated_change_rejected(self):
  paths,old,new=self.aliases();real_load=stage.json.loads
  index,key=next((i,k) for i,k in enumerate(sorted(old),1) if old[k]!=new[k])
  path=stage.ROOT/key;prior={"path":str(path),"sha256":old[key]};review={"localeNativeSourceProof":stage.LOCALE19_PROOF_SHA}
  target=paths["localeNativeSourceProof"].read_text()
  modified=json.loads(target);modified["inputs"]["arbitrary-dependency"]= "0"*64
  def load(value,*args,**kwargs):return modified if value==target else real_load(value,*args,**kwargs)
  with patch.object(stage.json,"loads",load):
   self.assertFalse(stage.locale19_dependency_transition("localeNativeDependencyProof"+str(index),prior,path,new[key],paths,review,19))

 def test_current_locale_guard_preserves_five_files_and_globals(self):
  paths=stage.original_locale_paths(19);result=stage.verify_original_locale_inputs(paths,19)
  self.assertEqual(result["originalLocaleFixtureFilesVerified"],5)
  self.assertFalse(result["nativeCallsPerformed"]);self.assertFalse(result["filesCopiedByGuard"])
  self.assertEqual(len([k for k in paths if k.startswith("localeNativeDependencyProof")]),26)
  values=stage.original_locale_runtime_values(paths)
  self.assertEqual(values["PRACTICE_LOCALIZATION_FIXTURE_SHA256"],stage.LOCALE_FIXTURE_SHA)
  self.assertEqual(stage.original_locale_paths(18)["localeNativeSourceProof"].name,"practice-localization-source153.json")
  self.assertEqual(stage.original_overlay_source_paths(18)["overlayIntegrationProof"].name,"practice-overlay-rng-integration5.json")
  self.assertEqual(stage.original_overlay_source_paths(19)["overlayIntegrationProof"].name,"practice-overlay-rng-integration6.json")

 def test_historical_continuity_pin_and_new_exact_scope(self):
  self.assertEqual(stage.CONTINUITY_SOURCE_SHA,"cd7e8d802cd864fd3a82f7e7022d475dd8b19620c582fa1b42851f187dce810c")
  self.assertEqual(stage.sha(HERE/"check_auto_preferences_continuity153.py"),stage.CONTINUITY19_SOURCE_SHA)
  self.assertNotEqual(stage.CONTINUITY19_SOURCE_SHA,stage.CONTINUITY_SOURCE_SHA)

if __name__=="__main__":unittest.main()

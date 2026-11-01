"""Candidate20 additive locale scope; synthetic rows only, no native/copy calls."""
from pathlib import Path
from copy import deepcopy
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('complete_locale_stage_test',HERE/'stage_practice153.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class CompleteLocale(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='raidlab-complete-locale-test-only-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'lss'
  wanted=[]
  for i in range(63):
   rel=f'Locale_Test{i//2}.lsc'+('.nds' if i%2 else '') if i<60 else f'Asset/TestFont{i}.bundle'
   wanted.append({'assetKey':f'TEST-ONLY-{i}','privateRelativePath':rel,'privateTarget':str((self.root/rel).resolve()),'bytes':4,'sha256':'1'*64})
  self.proof={'localeTables':30,'localeTableAndSignatureFiles':60,'unionFiles':63,'unionBytes':252,'catalogLocaleEntrySetComplete':True,'baseFixture':{'receiptSha256':stage.LOCALE_FIXTURE_SHA,'unchanged':True},'assets':wanted[:60],'unchangedBaseExtras':wanted[60:]}
  self.plan=[{**row,'target':Path(row['privateTarget']),'existingIdenticalCopy':True} for row in wanted]
  self.receipt={'status':'original153_complete_locale_table_closure_staged','unionFiles':63,'unionBytes':252,'baseFixtureReceiptSha256':stage.LOCALE_FIXTURE_SHA,'installedFilesWritten':False,'catalogsRewritten':False,'signatureBytesChanged':False,'copies':[{'target':str(row['target']),'sha256':row['sha256'],'bytes':row['bytes']} for row in self.plan]}
 def check_scope(self):return stage.validate_complete_locale_plan(self.proof,self.plan,self.receipt,self.root)
 def test_exact63_scope(self):
  result=self.check_scope();self.assertEqual(len(result),63);self.assertEqual(sum(r['bytes'] for r in result),252)
 def test_only20_adds_paths(self):
  self.assertEqual(stage.complete_locale_paths(19),{})
  self.assertEqual(set(stage.complete_locale_paths(20)),{'completeLocaleSourceProof','completeLocaleFixtureHelper','completeLocaleFixtureReceipt','completeLocaleStagerTestSource'})
 def test_old_guard_rejected_before_access(self):
  with self.assertRaisesRegex(ValueError,'candidate20'):stage.verify_complete_locale_inputs({},19)
 def test_exact_pinned_hash_before_import(self):
  paths=stage.complete_locale_paths(20)
  with patch.object(stage,'sha',return_value='f'*64),patch.object(stage.importlib.util,'spec_from_file_location',side_effect=AssertionError('must not import')):
   with self.assertRaisesRegex(ValueError,'input differs'):stage.verify_complete_locale_inputs(paths,20)
 def test_runtime_globals_dispatch_preserved(self):
  paths=stage.original_locale_paths(19);values=stage.original_locale_runtime_values(paths)
  self.assertEqual(set(values),{'PRACTICE_LOCALIZATION_BINDING','PRACTICE_LOCALIZATION_BINDING_SHA256','PRACTICE_LOCALIZATION_FIXTURE','PRACTICE_LOCALIZATION_FIXTURE_SHA256'})
  self.assertEqual(values['PRACTICE_LOCALIZATION_BINDING_SHA256'],stage.LOCALE_BINDING_SHA)
  self.assertEqual(values['PRACTICE_LOCALIZATION_FIXTURE_SHA256'],stage.LOCALE_FIXTURE_SHA)
  self.assertEqual(stage.original_practice_dispatch(20),stage.original_practice_dispatch(19))
 def test_no_new_generic_python_json_review(self):
  for name,path in [('completeLocaleFixtureHelper','helper.py'),('completeLocaleSourceProof','proof.json')]:self.assertFalse(stage.source_review_allowed(name,Path(path),20))
 def test_wrong_table_scope(self):
  self.proof['localeTables']=29
  with self.assertRaises(ValueError):self.check_scope()
 def test_missing_plan_entry(self):
  self.plan.pop()
  with self.assertRaises(ValueError):self.check_scope()
 def test_missing_receipt_entry(self):
  self.receipt['copies'].pop()
  with self.assertRaises(ValueError):self.check_scope()
 def test_base_five_changed(self):
  self.proof['baseFixture']['receiptSha256']='f'*64
  with self.assertRaises(ValueError):self.check_scope()
 def test_absent_copy(self):
  self.plan[0]['existingIdenticalCopy']=False
  with self.assertRaises(ValueError):self.check_scope()
 def test_duplicate_copy(self):
  self.plan[1]=deepcopy(self.plan[0])
  with self.assertRaises(ValueError):self.check_scope()
 def test_path_escape(self):
  self.plan[0]['target']=self.root.parent/'outside'
  with self.assertRaises(ValueError):self.check_scope()
 def test_relative_path_escape(self):
  self.proof['assets'][0]['privateRelativePath']='../outside'
  with self.assertRaises(ValueError):self.check_scope()
 def test_plan_hash_mismatch(self):
  self.plan[0]['sha256']='f'*64
  with self.assertRaises(ValueError):self.check_scope()
 def test_receipt_hash_mismatch(self):
  self.receipt['copies'][0]['sha256']='f'*64
  with self.assertRaises(ValueError):self.check_scope()
 def test_receipt_target_mismatch(self):
  self.receipt['copies'][0]['target']=str(self.root/'other')
  with self.assertRaises(ValueError):self.check_scope()
 def test_union_size_mismatch(self):
  self.receipt['unionBytes']=253
  with self.assertRaises(ValueError):self.check_scope()
 def test_installed_write_claim_rejected(self):
  self.receipt['installedFilesWritten']=True
  with self.assertRaises(ValueError):self.check_scope()
if __name__=='__main__':unittest.main()

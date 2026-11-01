"""Synthetic filesystem contracts for the exact original-overlay input verifier."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('overlay_stage_test',HERE/'stage_practice153.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class OverlayFiles(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='raidlab-overlay-test-only-');self.addCleanup(self.temp.cleanup)
  self.source=Path(self.temp.name)/'installed';self.target=Path(self.temp.name)/'private';self.rows=[]
  for name in ['globalgamemanagers','globalgamemanagers.assets','resources.assets','sharedassets0.assets']:
   rel=Path('nikke_Data')/name;a=self.source/rel;b=self.target/rel;a.parent.mkdir(parents=True,exist_ok=True);b.parent.mkdir(parents=True,exist_ok=True)
   value=('TEST-ONLY '+name).encode()+b'\x00\r\n';a.write_bytes(value);b.write_bytes(value)
   self.rows.append(dict(relative=str(rel),source=str(a),private=str(b),byteLength=len(value),sha256=hashlib.sha256(value).hexdigest()))
  self.proof={'builtinCopies':self.rows}
 def verify(self):return stage.verify_overlay_bootstrap_copies(self.proof,self.source,self.target)
 def test_exact_four_copies(self):
  result=self.verify();self.assertEqual(len(result),4);self.assertEqual(result[2]['target'],self.rows[2]['private'])
 def test_private_tamper(self):
  p=Path(self.rows[2]['private']);p.write_bytes(b'X'*p.stat().st_size)
  with self.assertRaisesRegex(ValueError,'bytes differ'):self.verify()
 def test_installed_tamper(self):
  p=Path(self.rows[2]['source']);p.write_bytes(b'X'*p.stat().st_size)
  with self.assertRaisesRegex(ValueError,'bytes differ'):self.verify()
 def test_missing_private(self):
  Path(self.rows[0]['private']).unlink()
  with self.assertRaises(FileNotFoundError):self.verify()
 def test_wrong_target_path(self):
  self.rows[0]['private']=self.rows[0]['source']
  with self.assertRaisesRegex(ValueError,'paths differ'):self.verify()
 def test_wrong_source_path(self):
  self.rows[0]['source']=self.rows[0]['private']
  with self.assertRaisesRegex(ValueError,'paths differ'):self.verify()
 def test_missing_row(self):
  self.rows.pop()
  with self.assertRaisesRegex(ValueError,'four'):self.verify()
 def test_duplicate_row(self):
  self.rows[3]=deepcopy(self.rows[0])
  with self.assertRaisesRegex(ValueError,'four'):self.verify()
 def test_unexpected_bootstrap_file(self):
  self.rows[3]['relative']='nikke_Data/unknown.assets'
  with self.assertRaisesRegex(ValueError,'four'):self.verify()
 def test_same_install_target_rejected(self):
  with self.assertRaisesRegex(ValueError,'paths differ'):stage.verify_overlay_bootstrap_copies(self.proof,self.source,self.source)
 def test_relative_source_evidence(self):
  for value in ['transfer/battle-parity-20261101/native153/loading-overlay-show2-source.json',r'transfer\battle-parity-20261101\native153\loading-overlay-show2-source.json']:
   self.assertEqual(stage.overlay_source_path(value),HERE/'loading-overlay-show2-source.json')
 def test_source_path_escape(self):
  for value in ['../x','transfer/other-proof.json',str(HERE/'loading-overlay-show2-source.json')]:
   with self.assertRaises(ValueError):stage.overlay_source_path(value)
 def test_no_general_json_review_bypass(self):
  self.assertFalse(stage.source_review_allowed('overlayInput',Path('binding.json'),16))
  self.assertFalse(stage.source_review_allowed('randomPythonSource',Path('random.py'),16))
  self.assertTrue(stage.source_review_allowed('autoPreferencesContinuityWitnessSource',Path('specific.py'),16))
  self.assertFalse(stage.source_review_allowed('autoPreferencesContinuityWitnessSource',Path('specific.py'),15))
 def test_actual_runtime_globals(self):
  binding=HERE/'practice-loading-overlay-binding.json';popup=HERE/'practice-popup-control-source.json'
  values=stage.original_overlay_runtime_values({'overlayInput':binding,'popupControlInput':popup})
  self.assertEqual(set(values),{'PRACTICE_LOADING_OVERLAY_BINDING','PRACTICE_POPUP_CONTROL_SOURCE','PRACTICE_POPUP_CONTROL_SOURCE_SHA256'})
  self.assertEqual(values['PRACTICE_LOADING_OVERLAY_BINDING'],json.loads(binding.read_text()))
  self.assertEqual(values['PRACTICE_POPUP_CONTROL_SOURCE'],json.loads(popup.read_text()))
  self.assertEqual(values['PRACTICE_POPUP_CONTROL_SOURCE_SHA256'],hashlib.sha256(popup.read_bytes()).hexdigest())
 def test_original_module_before_probe(self):
  self.assertEqual(stage.original_overlay_module_order(('geometrySource','probeSource','rngStateVerifierSource')),('geometrySource','rngStateVerifierSource','overlaySource','probeSource'))
 def test_duplicate_or_missing_module_rejected(self):
  for rows in [(),('probeSource','probeSource'),('overlaySource','probeSource')]:
   with self.assertRaises(ValueError):stage.original_overlay_module_order(rows)
if __name__=='__main__':unittest.main()

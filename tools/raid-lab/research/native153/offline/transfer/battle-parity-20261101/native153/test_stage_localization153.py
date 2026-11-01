"""Candidate18 locale admission/dispatch only; no mutating stager/native run."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("locale_stager_under_test153", HERE / "stage_practice153.py")
stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)


class LocaleStageTests(unittest.TestCase):
    def test_current_five_files_sources_and_runtime_globals_validate_read_only(self):
        paths = stage.original_locale_paths()
        result = stage.verify_original_locale_inputs(paths)
        self.assertEqual(result["originalLocaleFixtureFilesVerified"], 5)
        self.assertFalse(result["nativeCallsPerformed"])
        self.assertFalse(result["filesCopiedByGuard"])
        self.assertEqual(len([key for key in paths if key.startswith("localeNativeDependencyProof")]), 26)
        self.assertEqual(len([key for key in paths if key.startswith("localePrivateFile")]), 5)
        values = stage.original_locale_runtime_values(paths)
        self.assertEqual(values["PRACTICE_LOCALIZATION_BINDING_SHA256"], stage.sha(paths["localeInput"]))
        self.assertEqual(values["PRACTICE_LOCALIZATION_FIXTURE_SHA256"], stage.sha(paths["localeFixtureReceipt"]))
        self.assertEqual(values["PRACTICE_LOCALIZATION_FIXTURE"]["status"], "original153_local_fixture_bytes_staged")

    def test_each_new_control_input_is_hash_pinned(self):
        actual_sha = stage.sha
        for key in stage.original_locale_paths():
            paths = stage.original_locale_paths(); target = paths[key]
            def different(path):
                return "0" * 64 if Path(path) == target else actual_sha(path)
            with self.subTest(key=key), patch.object(stage, "sha", different), self.assertRaisesRegex(ValueError, "locale input"):
                stage.verify_original_locale_inputs(paths)

    def test_known_original_source_dependency_hash_is_required(self):
        actual_sha = stage.sha
        target = HERE / "locale17-original-sql-path-source.json"
        def different(path):
            return "0" * 64 if Path(path) == target else actual_sha(path)
        with patch.object(stage, "sha", different), self.assertRaisesRegex(ValueError, "source dependency"):
            stage.verify_original_locale_inputs(stage.original_locale_paths())

    def test_missing_copy_cannot_pass_as_a_valid_copy_plan(self):
        helper_spec = importlib.util.spec_from_file_location("locale_copy_guard_mock153", HERE / "stage_local_locale153.py")
        helper = importlib.util.module_from_spec(helper_spec); helper_spec.loader.exec_module(helper)
        proof, actual = helper.prepare()
        for change in ("missing", "short"):
            rows = [dict(row) for row in actual]
            if change == "missing": rows[0]["existingIdenticalCopy"] = False
            else: rows.pop()
            fake = SimpleNamespace(prepare=lambda: (proof, rows))
            fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
            api = SimpleNamespace(spec_from_file_location=lambda *args: fake_spec, module_from_spec=lambda spec: fake)
            with self.subTest(change=change), patch.object(stage.importlib, "util", api), self.assertRaisesRegex(ValueError, "five original"):
                stage.verify_original_locale_inputs(stage.original_locale_paths())

    def test_existing_module_relative_order_is_preserved_and_locale_is_unique(self):
        before = ("settingsSource", "rngStateVerifierSource", "overlaySource", "probeSource")
        after = stage.original_locale_module_order(before)
        self.assertEqual(tuple(name for name in after if name != "localeSource"), before)
        self.assertEqual(after[-2:], ("localeSource", "probeSource"))
        for broken in (("localeSource", "probeSource"), ("probeSource", "probeSource"), ("overlaySource",)):
            with self.subTest(broken=broken), self.assertRaises(ValueError): stage.original_locale_module_order(broken)

    def test_existing_five_overlay_proof_targets_are_unmodified_at18(self):
        for name, spec in stage.prepared_overlay_proof_specs().items():
            self.assertTrue(stage.prepared_overlay_proof_target(name, spec[2], spec[3], 18))
            self.assertFalse(stage.prepared_overlay_proof_target(name, spec[2], "0" * 64, 18))
        self.assertFalse(stage.prepared_overlay_proof_target("localeInput", HERE / "practice-localization-binding.json", stage.LOCALE_BINDING_SHA, 18))
        self.assertFalse(stage.source_review_allowed("localeInput", Path("binding.json"), 18))
        self.assertFalse(stage.source_review_allowed("localeFixtureHelper", Path("helper.py"), 18))

    def test_actual_dispatch_waits_pins_and_finishes_on_error(self):
        javascript = r'''
const assert=require('assert'),vm=require('vm');
const source=process.argv[1],legacy=process.argv[2];
function boot(options={}){
 const refs=[],events=[],calls=[];let callback;
 const error=Object.assign(new Error('original-native-error'),{nativeFrames:[{rva:'0x123'}]});
 const native={ref:strong=>{assert.equal(strong,true);return 'strong-root';}};
 const state={ready:false},fault={error:'preserved-original-first-fault'};
 const env={runtime:{originalRuntime:true},roots:refs,finishing:false,firstAsyncFault:fault,
  record:r=>events.push(r),finish:()=>{calls.push('finish');},
  fail:(phase,e)=>{calls.push(['fail',phase,e]);if(options.failThrows)throw Error('diagnostic-sink-fault');},
  startOriginalPracticeLocalization:(runtime,pin,emit,done)=>{
   assert.equal(runtime,env.runtime);assert.equal(emit,env.record);assert.equal(pin(native),native);
   calls.push('localization');callback=done;return state;},
  runOriginalPracticeProbe:(emit,finish)=>{
   assert.equal(emit,env.record);assert.equal(finish,env.finish);calls.push('probe');
   if(options.probeThrows)throw error;return 'original-probe-state';}};
 vm.runInNewContext(source,env);
 return {env,refs,events,calls,error,state,fault,done:e=>callback(e)};
}
let h=boot();assert.deepEqual(h.calls,['localization']);assert.deepEqual(h.refs,['strong-root']);
assert.equal(h.env.NATIVE153_ACTIVE_LOCALIZATION,h.state);h.done(null);
assert.deepEqual(h.calls,['localization','probe']);assert.equal(h.env.NATIVE153_ACTIVE_PRACTICE,'original-probe-state');
assert.equal(h.env.firstAsyncFault,h.fault);
h=boot();h.done(h.error);assert(!h.calls.includes('probe'));assert(h.calls.includes('finish'));
assert.equal(h.calls.find(x=>Array.isArray(x))[2],h.error);assert.equal(h.events[0].nativeFrames,h.error.nativeFrames);
assert.equal(h.env.firstAsyncFault,h.fault);
h=boot({probeThrows:true});h.done(null);assert(h.calls.includes('finish'));
assert.equal(h.calls.find(x=>Array.isArray(x))[1],'practice_dispatch_error');
h=boot();h.env.finishing=true;h.done(null);assert(!h.calls.includes('probe'));
h=boot({failThrows:true});assert.throws(()=>h.done(h.error),/diagnostic-sink-fault/);assert(h.calls.includes('finish'));
let oldCalls=0;vm.runInNewContext(legacy,{record:()=>{},finish:()=>{},runOriginalPracticeProbe:()=>++oldCalls});assert.equal(oldCalls,1);
console.log('actual staged dispatch pending/success/error/pin/lifetime controls PASS; no native calls');
'''
        result = subprocess.run(["node", "-e", javascript, stage.original_practice_dispatch(18), stage.original_practice_dispatch(17)],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__": unittest.main()

"""Synthetic broker lifecycle controls. Never launches a native player/backend."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("native_practice_job_under_test", HERE / "native_practice_job.py")
broker = importlib.util.module_from_spec(spec); sys.modules[spec.name] = broker; spec.loader.exec_module(broker)
real_verify_runtime = broker.verify_runtime
NATIVE = HERE.parents[1] / "transfer/battle-parity-20261101/native153"
gate = broker.load_module(NATIVE / "rng-state/archive_gate.py", "synthetic_broker_rng_gate")


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="native-practice-broker-test-")
        self.base = Path(self.temporary.name).resolve(); self.sandbox = self.base / "sandbox"
        self.game = self.sandbox / "NIKKE/NIKKE/game"; (self.game / "NKAB/dist").mkdir(parents=True)
        self.service = self.sandbox / "native-service"; self.directory = self.service / "releases/synthetic"
        self.directory.mkdir(parents=True)
        self.patches = [patch.object(broker, "SANDBOX", self.sandbox), patch.object(broker, "no_private_player", lambda: None),
                        patch.object(broker, "verify_runtime", lambda data: None)]
        for item in self.patches: item.start()
        self.inventory = {}; self.named = {}; self.rows = {"normal": {"values": {"exact": 1}}, "private": {"values": {"exact": 1}}}
        self.resources = {}
        for group in ("core", "dp"):
            path = self.sandbox / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch" / group / "chunk/store.cdb"
            path.parent.mkdir(parents=True); path.write_bytes(b"synthetic-store-" + group.encode()); self.resources[group] = path
        self.expected = json.loads((NATIVE / "rng-state/expected1/run1-onstart-shared-rng.json").read_text())
        self.write("rngExpectedFile", "expected.json", self.expected)
        self.write("fixtureFile", "fixture.json", {"provenance": "synthetic test fixture only"})
        self.write("mode", "mode.json", {"waveId": 6801001, "timeLimit": 90, "characters": [{"tableId": tid} for tid, _ in broker.IDENTITIES]})
        self.write("preferenceBaselineFile", "preferences.json", {"rows": self.rows})
        self.write("isolationProofFile", "isolation.json", {"bindings": {}})
        self.write("decoderBuildReceiptFile", "decoder.json", {"provenance": "synthetic decoder stub only"})
        self.write("resource", "resources.json", {"provenance": "synthetic resource receipt only"})
        self.write("bundleFile", "bundle.js", b"// SYNTHETIC HOST TEST ONLY; no native code\n")
        self.packet_name = "practice15-original-result.pb"
        slot = self.game / broker.SLOT; slot.write_bytes(b"// SYNTHETIC PREVIOUS SLOT\n")
        prior = self.sandbox / "synthetic-prior"; prior.mkdir()
        (prior / "verification.json").write_text('{"provenance":"synthetic previous archive"}')
        shutil.copyfile(slot, prior / "scene-probe.js")
        initial = {broker.SLOT: {"sha256": broker.sha(slot), "archivePath": str(prior / "scene-probe.js"),
            "verificationPath": str(prior / "verification.json"), "verificationSha256": broker.sha(prior / "verification.json")}}
        config = {"sandbox_root": str(self.sandbox), "max_seconds": 60, "expected_files": {"GameAssembly.dll": {"sha256": broker.CLIENT}},
                  "diagnostic_files": {broker.SLOT: {"sha256": broker.sha(self.named["bundleFile"])}}}
        self.write("configTemplateFile", "config.json", config)
        staging = {"captureSha256": "synthetic-capture", "fullSharedRngStateRequired": True,
            "sources": {key: {"path": str(self.named[name]), "sha256": broker.sha(self.named[name])} for key, name in
                (("fixtureInput", "fixtureFile"), ("rngExpectedInput", "rngExpectedFile"), ("modeInput", "mode"), ("packetDecoderBuildReceipt", "decoderBuildReceiptFile"))},
            "resourceReceipts": {"synthetic": {"path": str(self.named["resource"]), "sha256": broker.sha(self.named["resource"])}}}
        self.write("stagingTemplateFile", "staging.json", staging)
        self.held = False; self.closed = 0; self.execute_calls = 0; self.progress = []; self.failure = None; self.mutate_resource = False
        test = self
        class FakeLease:
            def __init__(self, path): self.path = path
            def acquire(self):
                if test.held: raise type("RunnerBusy", (RuntimeError,), {})("synthetic busy")
                test.held = True
            def close(self): test.held = False; test.closed += 1
        class FakeHost:
            def validate(self, path, fresh_output=True):
                if test.failure == "validate": raise RuntimeError("synthetic host validation failure")
                value = broker.read_json(path); output = Path(value["output_dir"])
                if fresh_output and output.exists() and any(output.iterdir()): raise ValueError("nonfresh synthetic output")
                return {"plan_sha256": broker.sha(path), "output_dir": str(output)}
            def execute(self, path, ready):
                assert test.held
                test.execute_calls += 1
                if test.failure == "execute": raise RuntimeError("synthetic host execution failure")
                value = broker.read_json(path); output = Path(value["output_dir"]); output.mkdir()
                result = {"returncode": 0, "timed_out": False, "stdout": '{"phase":"player_pid","pid":1234}',
                          "elapsed_seconds": 0.01, "desktop": "NikkeCatalogProbe_SYNTHETIC"}
                broker.fresh_json(output / "native-player-run.json", result)
                (output / "player.log").write_text("SYNTHETIC CONTROL ONLY")
                terminal, observations = test.terminal()
                if test.failure == "rng":
                    observations[0]["actual"]["drawCount"] = "0"
                events = observations + [terminal, {"phase": "quit_requested"}]
                (test.game / "scene-events.jsonl").write_text("\n".join(json.dumps(row) for row in events) + "\n")
                for name in broker.LOGS[1:]: (test.game / name).write_text("SYNTHETIC CONTROL ONLY")
                (test.game / test.packet_name).write_bytes(b"\x0a\x0d\x00")
                if test.mutate_resource: test.resources["core"].write_bytes(b"synthetic changed resource")
                return result
        class FakeDecoder:
            def decode_archived_packet(self, packet, report, terminal, mode, receipt):
                if test.failure == "decode": raise ValueError("synthetic decoder failure")
                value = {"status": "passed", "provenance": "SYNTHETIC DECODER TEST DOUBLE ONLY", "originalWire": {
                    "path": str(packet), "sha256": broker.sha(packet), "byteLength": packet.stat().st_size},
                    "typedReadback": {"waveId": 6801001, "battleDuration": 90000, "characterCount": 5,
                        "monsterCount": 35, "characterTids": [tid for tid, _ in broker.IDENTITIES]}}
                broker.fresh_json(report, value)
                return {"status": "passed", "reportSha256": broker.sha(report), "rawPacketSha256": broker.sha(packet)}
        data = {"releaseId": "synthetic", "packetBasename": self.packet_name, "files": self.inventory, "initialSharedArtifacts": initial}
        self.write("manifest", "manifest.json", {"provenance": "SYNTHETIC UNPUBLISHED TEST RELEASE ONLY"}, inventory=False)
        self.release = SimpleNamespace(data=data, directory=self.directory, path=self.named["manifest"], sha=broker.sha(self.named["manifest"]),
            file=lambda name: self.named[name], lease_module=SimpleNamespace(NativeRunnerLease=FakeLease), host=FakeHost(), gate=gate,
            resource=SimpleNamespace(verify_resource_receipts=lambda paths: {"verifiedChunks": 1, "provenance": "synthetic"}),
            preference=SimpleNamespace(read_exact_values=lambda: copy.deepcopy(self.rows)), decoder=FakeDecoder(), expected=self.expected)

    def write(self, key, name, value, inventory=True):
        path = self.directory / name
        path.write_bytes(value if isinstance(value, bytes) else (json.dumps(value) + "\n").encode())
        self.named[key] = path
        if inventory: self.inventory[name] = broker.sha(path)

    def terminal(self):
        observations = [{"status": "original_practice_full_shared_rng_observed", "boundaryPhase": phase,
            "expectedFileSha256": broker.RNG_SHA, "referenceRunIndex": 1, "source": self.expected["phases"][phase]["source"],
            "actual": copy.deepcopy(self.expected["phases"][phase]["state"]), "passed": True, "mismatchFields": [], "mismatchArrayIndices": [],
            "comparedArrayElements": 56, "rngStateWritten": False, "rngMethodsInvoked": False, "sameOriginalOnStartBoundary": True} for phase in ("enter", "leave")]
        snapshot = {"seen": {"enter": True, "leave": True}, "fault": None, "observations": copy.deepcopy(observations),
            "expectedFileSha256": broker.RNG_SHA, "referenceRunIndex": 1, "comparedArrayElementsPerBoundary": 56,
            "rngStateWritten": False, "rngMethodsInvoked": False, "typedArrayAccessorPrimedOutsideNativeHooks": True, "helperInstallsHooks": False}
        return {"status": "original_practice_terminal_result", "completeBattle": True, "resultCaptured": True, "result": 1, "spotResult": 1,
            "originalAntiCheat": {"waveId": 6801001, "battleDuration": 90000, "characterCount": 5, "monsterCount": 35},
            "inputSourceSha256": broker.FIXTURE_SHA, "statisticsAndPacketCapturedBeforeCleanup": True,
            "verification": {"passed": True}, "originalPacketExported": True, "fullSharedRngState": snapshot,
            "fullAccuracyVerified": False, "rounds": [{"duration": 90, "isWin": True, "squadTotal": "9007199254740993", "characters": [
                {"entityId": index + 4096, "tableId": tid, "nameCode": name, "outgoingDamage": "100", "outgoingActualDamage": "90"}
                for index, (tid, name) in enumerate(broker.IDENTITIES)]}]}, observations

    def prepare(self, ident="a" * 24):
        return broker.prepare_job(self.release.path, ident, self.release.sha, self.progress.append, runtime=self.release)

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        # Explicitly verify the newly allocated child before recursive cleanup.
        root = self.base.resolve(); temp = Path(tempfile.gettempdir()).resolve()
        assert root.parent == temp and root.name.startswith("native-practice-broker-test-") and not root.is_symlink()
        self.temporary.cleanup()

    def test_full_synthetic_job_preserves_bytes_int64_and_lease_until_archive(self):
        p = self.prepare(); self.assertTrue(self.held)
        report = broker.run_job(p)
        self.assertEqual(report["score"], "9007199254740993")  # copied, never summed from synthetic characters
        self.assertEqual(Path(report["packet"]["path"]).read_bytes(), b"\x0a\x0d\x00")
        self.assertEqual(broker.read_json(Path(report["evidence"]["verificationPath"]))["status"], "passed")
        self.assertFalse(self.held); self.assertEqual(self.execute_calls, 1)
        self.assertFalse((self.game / self.packet_name).exists())
        self.assertEqual(self.progress, ["prepared", "running_private_player", "archived"])
        with self.assertRaises(broker.BrokerError): broker.run_job(p)

    def test_two_jobs_use_same_native_basename_but_fresh_archives(self):
        first = broker.run_job(self.prepare()); first_hash = broker.sha(Path(first["evidence"]["verificationPath"]))
        second = broker.run_job(self.prepare("b" * 24))
        self.assertNotEqual(first["packet"]["path"], second["packet"]["path"])
        self.assertEqual(broker.sha(Path(first["evidence"]["verificationPath"])), first_hash)
        self.assertEqual(self.execute_calls, 2)

    def test_unknown_shared_artifact_refuses_before_mutation(self):
        path = self.game / "scene-events.jsonl"; path.write_text("unknown unarchived evidence")
        with self.assertRaises(broker.BrokerError): self.prepare()
        self.assertEqual(path.read_text(), "unknown unarchived evidence"); self.assertEqual(self.execute_calls, 0); self.assertFalse(self.held)

    def test_busy_and_existing_job_refuse(self):
        self.held = True
        with self.assertRaisesRegex(broker.BrokerError, "busy"): self.prepare()
        self.held = False; p = self.prepare(); p.lease.close()
        before = {path.name: broker.sha(path) for path in p.root.iterdir() if path.is_file()}
        with self.assertRaises(FileExistsError): self.prepare()
        self.assertEqual(before, {path.name: broker.sha(path) for path in p.root.iterdir() if path.is_file()})
        self.assertEqual(self.execute_calls, 0)

    def test_preparation_failure_restores_exact_prior_script(self):
        original = (self.game / broker.SLOT).read_bytes(); self.failure = "validate"
        with self.assertRaisesRegex(RuntimeError, "validation"): self.prepare()
        self.assertEqual((self.game / broker.SLOT).read_bytes(), original); self.assertFalse(self.held)
        self.assertTrue((self.service / "jobs" / ("a" * 24) / "preparation-error.json").exists())

    def test_failed_decode_and_missing_rng_never_return_success(self):
        for failure, ident in (("decode", "a" * 24), ("rng", "b" * 24)):
            self.failure = failure
            with self.assertRaises(broker.BrokerError): broker.run_job(self.prepare(ident))
            verify = broker.read_json(self.service / "jobs" / ident / "output/verification.json")
            self.assertEqual(verify["status"], "failed"); self.assertFalse(self.held)

    def test_changed_resource_and_preferences_fail_with_evidence(self):
        self.mutate_resource = True
        with self.assertRaises(broker.BrokerError): broker.run_job(self.prepare())
        value = broker.read_json(self.service / "jobs" / ("a" * 24) / "output/verification.json")
        self.assertFalse(value["resourceInputIdentitiesUnchanged"]); self.assertEqual(value["status"], "failed")
        self.rows["normal"]["values"]["exact"] = 2
        with self.assertRaises(broker.BrokerError): self.prepare("b" * 24)

    def test_unavailable_release_and_actual_historical14_rejected(self):
        with self.assertRaisesRegex(broker.BrokerError, "No approved"): broker.load_release(self.directory / "missing.json", "a" * 64)
        actual = NATIVE.parents[2] / "tools/raid-lab/private/native-player153-20261101/practice-output14"
        verification = broker.read_json(actual / "verification.json"); staging = broker.read_json(actual / "staging.json")
        with self.assertRaises(broker.BrokerError): broker.admit_verification(verification, staging, self.expected, gate)

    def test_cli_unavailable_is_json_error_without_execution(self):
        output = io.StringIO()
        with patch.object(sys, "stdout", output):
            status = broker.main(["--release-manifest", str(self.directory / "absent.json"), "--manifest-sha256", "a" * 64,
                "--job-id", "c" * 24, "--fixture-id", broker.FIXTURE, "--input-source-sha256", broker.FIXTURE_SHA,
                "--result-schema", broker.SCHEMA])
        row = json.loads(output.getvalue())
        self.assertEqual((status, row["type"], row["code"]), (2, "error", "native_release_unavailable"))
        self.assertEqual(self.execute_calls, 0)

    def test_traversal_and_hardlink_source_refused(self):
        with self.assertRaises(broker.BrokerError): broker.inside(self.directory, "../escape")
        linked = self.directory / "synthetic-linked-file"
        import os
        os.link(self.named["bundleFile"], linked)
        with self.assertRaises(broker.BrokerError): broker.bound(linked)

    def test_complete_synthetic_release_admission_and_changed_manifest_refusal(self):
        # Only admission plumbing is mocked here. No synthetic release is ever
        # written under the real sandbox, registered, or executed by the player.
        checks = {"FIXTURE_SHA": broker.sha(self.named["fixtureFile"]), "RNG_SHA": broker.sha(self.named["rngExpectedFile"]),
                  "PREF_BASELINE_SHA": broker.sha(self.named["preferenceBaselineFile"]), "ISOLATION_SHA": broker.sha(self.named["isolationProofFile"])}
        runtime = self.base / "synthetic-runtime"; runtime.mkdir()
        host = runtime / "host.py"; lease = runtime / "lease.py"; host.write_text("# synthetic only"); lease.write_text("# synthetic only")
        with patch.multiple(broker, **checks), patch.object(broker, "HOST", host), patch.object(broker, "LEASE", lease):
            terminal, observations = self.terminal()
            build = {"sourceInputs": {"synthetic.cs": {"path": "synthetic", "sha256": "a" * 64}},
                     "artifacts": {"synthetic.dll": {"path": "synthetic", "sha256": "b" * 64}}, "dotnet": {"sha256": "c" * 64}}
            self.write("decoderBuildReceiptFile", "decoder.json", build)
            self.write("decoderOriginalBuildReceiptFile", "original-decoder-build.json", build)
            staging = broker.read_json(self.named["stagingTemplateFile"])
            staging.update(captureSha256=broker.CAPTURE_SHA, originalResultFilename=self.packet_name)
            staging["sources"]["packetDecoderBuildReceipt"]["sha256"] = broker.sha(self.named["decoderOriginalBuildReceiptFile"])
            validation = {"status": "passed", "exitCode": 0, "timedOut": False, "completeBattle": True,
                "originalPacketExportVerified": True, "requiredPreferenceStorageControlsPassed": True,
                "requiredFullSharedRngStateVerified": True, "frozenSourceInputsUnchanged": {"synthetic": True},
                "firstFailures": [], "nativeExceptions": [], "originalPacketExportFailures": [], "terminalResults": [terminal],
                "captureSha256": broker.CAPTURE_SHA, "fullSharedRngStateObservations": observations,
                "fullSharedRngStateVerification": gate.verify(observations, terminal, self.expected, broker.RNG_SHA),
                "artifacts": {"scene-probe.js": broker.sha(self.named["bundleFile"]), "config.json": broker.sha(self.named["configTemplateFile"])}}
            self.write("approvedPacket", "approved-synthetic.pb", b"\x0a\x00")
            raw = {"sha256": broker.sha(self.named["approvedPacket"]), "byteLength": 2}
            validation["originalPacketArtifact"] = {**raw, "format": "protobuf_wire"}
            self.write("approvedDecode", "approved-decode.json", {"status": "passed", "originalWire": raw})
            self.write("approvedValidation", "approved-verification.json", validation)
            self.write("approvedStaging", "approved-staging.json", staging)
            for key in ("rngArchiveGateFile", "resourceVerifierFile", "preferenceReaderFile", "decoderModuleFile"):
                self.write(key, key + ".py", b"# SYNTHETIC MODULE PLACEHOLDER, never executed\n")
            manifest = {"schemaVersion": 1, "approved": True, "releaseId": "synthetic", "engine": "original153",
                "fixtureId": broker.FIXTURE, "inputSourceSha256": broker.FIXTURE_SHA, "clientSha256": broker.CLIENT,
                "resultSchema": broker.SCHEMA, "packetBasename": self.packet_name, "files": self.inventory,
                "operationsPrerequisites": {"diagnosticLaunchersUseSameLease": True},
                "runtime": {"hostSha256": broker.sha(host), "leaseSha256": broker.sha(lease)},
                **{key: path.relative_to(self.directory).as_posix() for key, path in self.named.items() if key != "manifest"},
                "nativeValidation": {}}
            for key, digest_key, name in (("receiptFile", "receiptSha256", "approvedValidation"), ("stagingFile", "stagingSha256", "approvedStaging"),
                ("packetFile", "packetSha256", "approvedPacket"), ("decoderFile", "decoderSha256", "approvedDecode")):
                manifest["nativeValidation"][key] = self.named[name].name
                manifest["nativeValidation"][digest_key] = broker.sha(self.named[name])
            self.write("manifest", "manifest.json", manifest, inventory=False)
            self.release.decoder.validate_build_receipt = lambda _: {"provenance": "synthetic only"}
            modules = {"_approved_practice_host": self.release.host, "_approved_practice_lease": self.release.lease_module,
                "_approved_practice_rng_gate": gate, "_approved_practice_resources": self.release.resource,
                "_approved_practice_preferences": self.release.preference, "_approved_practice_decoder": self.release.decoder}
            digest = broker.sha(self.named["manifest"])
            with patch.object(broker, "load_module", lambda path, name: modules[name]):
                release = broker.load_release(self.named["manifest"], digest)
                self.assertEqual(release.data["packetBasename"], self.packet_name)
                self.assertEqual(self.execute_calls, 0)
                self.named["manifest"].write_text('{"approved":false}')
                with self.assertRaises(broker.BrokerError): broker.load_release(self.named["manifest"], digest)

    def test_runtime_requires_all_intro_builtins_and_rechecks_live_bytes(self):
        runtime = self.base / "runtime-validation"; runtime.mkdir()
        paths = [runtime / name for name in ("host.py", "lease.py", "harness.py")]
        for item in paths: item.write_bytes(b"synthetic runtime source")
        files = {}
        for relative in broker.REQUIRED_RUNTIME | set(broker.REQUIRED_BUILTINS):
            path = self.sandbox / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"synthetic required dependency")
            files[relative] = broker.sha(path)
        builtin_hashes = {name: files[name] for name in broker.REQUIRED_BUILTINS}
        value = {"runtime": {"hostSha256": broker.sha(paths[0]), "leaseSha256": broker.sha(paths[1]),
            "harnessSha256": broker.sha(paths[2]), "requiredFiles": files}}
        with patch.object(broker, "HOST", paths[0]), patch.object(broker, "LEASE", paths[1]), patch.object(broker, "HARNESS", paths[2]), \
             patch.object(broker, "REQUIRED_BUILTINS", builtin_hashes):
            real_verify_runtime(value)
            key = next(iter(builtin_hashes)); digest = files.pop(key)
            with self.assertRaises(broker.BrokerError): real_verify_runtime(value)
            files[key] = digest; (self.sandbox / key).write_bytes(b"synthetic changed builtin")
            with self.assertRaises(broker.BrokerError): real_verify_runtime(value)


if __name__ == "__main__":
    unittest.main()

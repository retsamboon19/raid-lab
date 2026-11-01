"""One original loading-lifecycle diagnostic under the private runner lease."""
from pathlib import Path
import importlib.util
import json
import os
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(ROOT / "tools/raid-lab")]
from native_runner_lease import NativeRunnerLease
import stage_practice153 as stage
from copy_complete153_store import record_stat, ensure_closed
import check_auto_preferences_continuity153 as prefs

S = stage.SANDBOX
# Exact final source review acknowledged by both component owners. Never derive
# approval hashes from mutable inputs at execution time.
REVIEWED_STAGE_SHA = "635015f15bea045cc6be7f07599ac948cc7895b885670fead5295aa245a47d43"
REVIEWED_INTEGRATION_SHA = "1dec8c991be9233d13ebd904adb884ae00fb1e9e5a05f00f0993351e49265cdc"
PREDECESSOR_VERIFICATION_SHA = "0500de21ed0945d073c3e167c53beec195eb7d0b815e3c91c29789c731a55784"
SOURCE_PINS = {
    "practice-locale-table-closure-source153.json": "9cef725daf5479187e7a61b469cbf04d62031d1a045497f0ce4caaa00f92479f",
    "test_stage_complete_locale153.py": "2d69075464ca99ecfc6895a60a54e04cd1e493df9c4409dac5c1f41c7a9de3d2",
    "practice20-complete-locale-integration1.json": "510e4ca59e6bd60184e9a90b187dc60cd8cd962a11136612ff9880626c3aaee5",
    "stage_locale_table_closure153.py": "f32a2649417213d9c3f72110f4978dbb842ff4b8e264c467b101e99feb819af2",
    "practice19-source-proof-correction.json": "e655eca610c2ec9a2f2a875f8b97d66ed8d673009bbdf2bc3ce5f65d8c5cbcf5",
    "build_practice19_integration153.py": "96887efb0fa77ad63d028da90c8f0604fa4656eeef2945ab83712e5cf93f2d56",
    "practice-localization-source19.json": "967e08d23f701589daa96ffb9478dbb3c0bf01122b29c3e750d6738925fda5c6",
    "practice-localization-source153.json": "803d44e83cfd73035635a51c720210d16afcedce629b5c185c08d157c97300ae",
    "test_practice_localization.js": "653097ec9343fe538dedab3acaac954f90c367c055d999573a8ff0e6e0b4d208",
    "practice_localization.js": "6d26af5d439d4d1dce86e6e1a7242ae8ca46aea3746f61f576cc8a4bf0d4ab14",
    "practice-localization-binding.json": "7621643f35dce4a77c4b8b1b99f2f64cbacee29bcecf4ec697f27a6b03efe2d8",
    "stage_local_locale153.py": "081ff464819a55710e1bdd1f6c2cabcba737491f021a3b648b32d3aef6c5e908",
    "build_overlay_integration153.py": "0451af9280941140ef584c417e4d98955f2160ae972fc23c91edc1aa7b118ae7",
    "test_practice_overlay_bootstrap.js": "99b3ecfe75de1fb2e4917625b6be6924d981fb758e1c43686163e81d0bd0f252",
    "practice_geometry.js": "9120bdd08675e001d763bcdecd4e4e3d12d9d2e944a8ba561686c77316c77af0",
    "practice_probe.js": "a446c7e7ae6ce5799e23bea8fe85483a633dc5a7aeac699d40bc982c8e705730",
    "practice_frame_scheduler.js": "5ee060ef400f44b509bcbedaeef6819695eb9d9543cb6f9bc09a49c65bd005f5",
    "practice_overlay_bootstrap.js": "e013e7f207f6f6355d2a68f38722b35f9a62049b69909cd18b58def3662d8b5b",
    "test_practice_rng_probe_boundary.js": "2365598f15030b5eb7d5a19a44b3496c8ca002de4d0fa17426407653a5cd68c5",
    "test_practice_packet_writer.js": "6603bae2bb7bc3b71469cb78584759975b48d307fe4e7f5d52fd61c78fc9758c",
    "check_auto_preferences_continuity153.py": "f7b532ba3e9b5c9393aac244ccbf98eaf168da688a8bc1a391af6ccf2da44412",
    "archive_practice153.py": "2dbfd56e1ba2c4d65768113653ea2f44c0a72af1c9af73f4473bb2bbc2ff6619",
}
REVIEWED_CHANGES = {
    "localeNativeSourceProof": SOURCE_PINS["practice-localization-source19.json"],
    "localeRuntimeTestSource": SOURCE_PINS["test_practice_localization.js"],
    "localeSource": SOURCE_PINS["practice_localization.js"],
    "overlayIntegrationProof": REVIEWED_INTEGRATION_SHA,
    "overlayIntegrationBuilder": SOURCE_PINS["build_practice19_integration153.py"],
    "overlayTestSource": SOURCE_PINS["test_practice_overlay_bootstrap.js"],
    "geometrySource": SOURCE_PINS["practice_geometry.js"],
    "probeSource": SOURCE_PINS["practice_probe.js"],
    "schedulerSource": SOURCE_PINS["practice_frame_scheduler.js"],
    "overlaySource": SOURCE_PINS["practice_overlay_bootstrap.js"],
    "packetArchiverSource": SOURCE_PINS["archive_practice153.py"],
    "rngProbeBoundaryTestSource": SOURCE_PINS["test_practice_rng_probe_boundary.js"],
    "binaryPacketWriterTestSource": SOURCE_PINS["test_practice_packet_writer.js"],
    "autoPreferencesContinuityWitnessSource": SOURCE_PINS["check_auto_preferences_continuity153.py"],
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    with path.open("x", encoding="utf-8") as sink:
        json.dump(value, sink, indent=2)
        sink.write("\n")


def main():
    if sys.argv[1:] != ["--run"]:
        raise ValueError("Only the reviewed one-shot --run operation is supported")
    pins = {**SOURCE_PINS, "stage_practice153.py": REVIEWED_STAGE_SHA,
            "practice-overlay-rng-integration6.json": REVIEWED_INTEGRATION_SHA}
    for name, digest in pins.items():
        if stage.sha(HERE / name) != digest:
            raise ValueError("Reviewed source is not frozen: " + name)
    previous = S / "practice-output20"
    if stage.sha(previous / "verification.json") != PREDECESSOR_VERIFICATION_SHA:
        raise ValueError("Preserved successful native20 verification changed")
    verification20 = json.loads((previous / "verification.json").read_text())
    if stage.sha(previous / "staging.json") != verification20["artifacts"]["staging.json"]:
        raise ValueError("Preserved native20 staging binding changed")
    service = S / "native-service"
    service.mkdir(exist_ok=True)
    with NativeRunnerLease(service / "runner.lock"):
        with (S / "practice21-orchestration.jsonl").open("x", encoding="utf-8") as sink:
            def event(status, **values):
                row = {"status": status, **values}
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                print(json.dumps(row), flush=True)
            event("exclusive_lease_acquired", pid=os.getpid(), path=str(service / "runner.lock"))
            try:
                ensure_closed(verification20["actualPlayerPid"])
                old = json.loads((previous / "staging.json").read_text())
                # Carry previously reviewed literal hashes forward, never
                # approve mutable files by recomputing their present hashes.
                review = dict(old["reviewedChangedSourceHashes"])
                review.update(REVIEWED_CHANGES)
                stage.main(21, reference_run=2, reviewed_source_changes=[name + "=" + digest for name, digest in review.items()])
                staging = json.loads((S / "practice-staging21.json").read_text())
                plan_sha = json.loads((S / "practice-plan21.json").read_text())["plan_sha256"]
                event("candidate21_frozen", planSha256=plan_sha, sourceSha256=staging["sourceSha256"])
                if prefs.main(21, "pre", plan_sha):
                    raise ValueError("Preference pre-witness failed")
                def groups():
                    return {name: record_stat(stage.CORE.parent / name / "chunk/store.cdb") for name in ("core", "dp")}
                before_stats = groups()
                before = {"schemaVersion": 1, "planSha256": plan_sha, "groupStats": before_stats,
                    "fullStoreBefore": before_stats["core"],
                    "completeStoreReceiptSha256": stage.sha(S / "complete-current153-store1.json"),
                    "completeDpStoreReceiptSha256": stage.sha(S / "complete-current153-dp-store1.json"),
                    "resourceGuards": staging["resourceReadback"], "fullPayloadRehashed": False}
                before_path = S / "practice21-full-store-input-before.json"
                write(before_path, before)
                ready = json.loads((previous / "integration-ready.json").read_text())
                ready.update({"plan_sha256": plan_sha,
                    "staging_receipt_sha256": stage.sha(S / "practice-staging21.json"),
                    "original_result_filename": staging["originalResultFilename"],
                    "full_store_input_before_receipt_sha256": stage.sha(before_path),
                    "auto_preference_pre_witness_sha256": stage.sha(S / "practice21-auto-preferences-pre.json"),
                    "full_shared_rng_state_required": True, "original_intro_scene_required": True,
                    "original_loading_overlay_required": True,
                    "original_localization_initialization_required": True,
                    "complete_original_locale_table_closure_required": True,
                    "hypothesis": "Replay original captured reference2 with its own exact snapshot payloads, seed and full shared RNG expectation, using the unchanged successful native20 runtime/resources. Complete 90 seconds and independently decode the original packet for paired comparison."})
                ready_path = S / "practice-integration-ready21.json"
                write(ready_path, ready)
                host = load("reviewed_practice21_host", ROOT / "tools/raid-lab/native_player_host.py")
                event("one_private_desktop_run_begin", planSha256=plan_sha)
                result = host.execute(S / "sandbox-practice21.json", ready_path)
                event("one_private_desktop_run_returned", returncode=result["returncode"], timedOut=result["timed_out"])
                pids = [json.loads(line)["pid"] for line in result["stdout"].splitlines()
                        if line.startswith("{") and json.loads(line).get("phase") == "player_pid"]
                if len(pids) != 1:
                    raise ValueError("Exactly one actual private player PID required")
                dead = ensure_closed(pids[0])
                if prefs.main(21, "post", plan_sha, pids[0]):
                    raise ValueError("Preference post-witness failed")
                paths = {name: Path(item["path"]) for name, item in staging["sources"].items()}
                resource_paths = {name: Path(item["path"]) for name, item in staging["resourceReceipts"].items()}
                resource_after = stage.verify_resource_receipts(resource_paths)
                cutscene = json.loads((HERE / "practice-cutscene-control-source.json").read_text())
                resource_after["cutscenePrivateBuiltinCopies"] = stage.verify_cutscene_builtin_copies(
                    cutscene, ROOT / "NIKKE/NIKKE/game", stage.GAME)
                resource_after["originalOverlayInputs"] = stage.verify_original_overlay_inputs(paths, 21)
                resource_after["originalLocaleInputs"] = stage.verify_original_locale_inputs(paths, 21)
                resource_after["completeLocaleInputs"] = stage.verify_complete_locale_inputs(paths, 21)
                after_stats = groups()
                after = {"schemaVersion": 1, "planSha256": plan_sha, "deadChild": dead,
                    "groupStats": after_stats, "fullStoreAfter": after_stats["core"],
                    "fullStoreInputUnchanged": before_stats == after_stats,
                    "fullReadbackReceiptReusable": before_stats == after_stats,
                    "fullPayloadRehashed": False, "resourceGuards": resource_after}
                output = S / "practice-output21"
                write(output / "practice21-full-store-input-before.json", before)
                write(output / "practice21-full-store-input-after.json", after)
                if before_stats != after_stats:
                    raise ValueError("Private core/DP store changed")
                archive = load("reviewed_practice21_archive", HERE / "archive_practice153.py")
                archive.main(21)
                verification = json.loads((output / "verification.json").read_text())
                event("candidate21_archived", statusValue=verification["status"],
                    verificationSha256=stage.sha(output / "verification.json"), actualPlayerPid=pids[0],
                    completeBattle=verification.get("completeBattle"))
            except Exception as error:
                event("candidate21_orchestration_failure", error=str(error), stack=traceback.format_exc())
                raise


if __name__ == "__main__":
    main()

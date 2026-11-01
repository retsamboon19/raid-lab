"""Archive one completed private practice candidate, including failures intact."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
GAME = SANDBOX / "NIKKE/NIKKE/game"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_archive_plan(staging, output, reserved_names=()):
    """Deduplicate exact cross-map aliases only within this fresh invocation."""
    output = Path(output)
    root = output.resolve()
    reserved = {name.casefold() for name in reserved_names}
    identities, destinations, actions = {}, {}, []
    for group in ("sources", "resourceReceipts"):
        for name, item in staging[group].items():
            if not isinstance(name, str) or not name or name in (".", "..") or any(c in name for c in ("/", "\\", ":")):
                raise ValueError("Frozen archive key must be a single filename component")
            source = Path(item["path"])
            identity = (source.resolve(), item["sha256"])
            if name in identities:
                if identities[name] != identity:
                    raise ValueError("Conflicting frozen archive key/path/hash alias: " + name)
                continue
            target = output / ("frozen-" + name + source.suffix)
            if target.parent.resolve() != root:
                raise ValueError("Frozen archive target must be a direct output child")
            destination = target.name.casefold()
            if destination in reserved or destination in destinations:
                raise ValueError("Frozen archive destination collision: " + target.name)
            if target.exists() or target.is_symlink():
                raise FileExistsError(target)
            identities[name] = identity
            destinations[destination] = name
            actions.append((name, source, item["sha256"], target))
    return actions


def main(index):
    suffix = str(index)
    output = SANDBOX / ("practice-output" + suffix)
    if (output / "verification.json").exists():
        raise FileExistsError("Preserve original private verification")
    staging = json.loads((SANDBOX / ("practice-staging" + suffix + ".json")).read_text())
    run = json.loads((output / "native-player-run.json").read_text())
    if run["plan_sha256"] != staging["planSha256"]:
        raise ValueError("Native output and frozen plan differ")
    def copy(source, target):
        if target.exists():
            raise FileExistsError(target)
        shutil.copyfile(source, target)
        if sha(source) != sha(target):
            raise ValueError("Archived copy differs: " + str(source))
    pairs = [(GAME / "NKAB/dist/scene-probe.js", "scene-probe.js"),
             (SANDBOX / ("practice" + suffix + "-source.js"), "practice-source.js"),
             (SANDBOX / ("sandbox-practice" + suffix + ".json"), "config.json"),
             (SANDBOX / ("practice-plan" + suffix + ".json"), "plan.json"),
             (SANDBOX / ("practice-staging" + suffix + ".json"), "staging.json"),
             (SANDBOX / ("practice-integration-ready" + suffix + ".json"), "integration-ready.json"),
             (SANDBOX / "bootstrap-receipt.json", "bootstrap-receipt.json"),
             (SANDBOX / "network-receipt.json", "network-receipt.json"),
             (SANDBOX / "current-tables-provenance.json", "current-tables-provenance.json"),
             (HERE / "stage_practice153.py", "frozen-stager.py")]
    reserved = [target for _, target in pairs] + ["scene-events.jsonl", "headless-bootstrap.log", "offline-network.log", "verification.json"]
    if staging.get("originalResultFilename"):
        reserved.append(staging["originalResultFilename"])
    frozen = frozen_archive_plan(staging, output, reserved)
    for name in ("scene-events.jsonl", "headless-bootstrap.log", "offline-network.log"):
        if (GAME / name).exists():
            copy(GAME / name, output / name)
    for source, target in pairs:
        copy(source, output / target)
    result_filename = staging.get("originalResultFilename")
    packet_present = False
    if result_filename:
        expected_extension = "pb" if index >= 14 else "json"
        if not re.fullmatch(r"practice" + str(index) + r"-original-result\." + expected_extension, result_filename):
            raise ValueError("Original result path must be the frozen private basename")
        if (GAME / result_filename).is_file():
            copy(GAME / result_filename, output / result_filename)
            packet_present = True
    unchanged = {}
    for name, path, expected_sha, target in frozen:
        unchanged[name] = sha(path) == expected_sha
        if unchanged[name]:
            copy(path, target)
    preference_witnesses = None
    preference_storage_passed = True
    preference_plan = staging.get("autoPreferenceControlPlan")
    if preference_plan:
        preference_witnesses = {}
        for phase, key in (("pre", "preWitnessPath"), ("post", "postWitnessPath")):
            path = Path(preference_plan[key])
            if path.is_file():
                row = json.loads(path.read_text())
                copy(path, output / path.name)
                preference_witnesses[phase] = {"sha256": sha(path), "evidence": row}
        preference_storage_passed = all(phase in preference_witnesses and
            preference_witnesses[phase]["evidence"]["status"] == "passed" and
            preference_witnesses[phase]["evidence"]["planSha256"] == staging["planSha256"] and
            preference_witnesses[phase]["evidence"]["helperSourceSha256"] == preference_plan["witnessHelperSourceSha256"] and
            preference_witnesses[phase]["evidence"]["writesPerformed"] is False
            for phase in ("pre", "post"))
        if preference_storage_passed:
            post = preference_witnesses["post"]["evidence"]
            preference_storage_passed = post["normalTwoPreferencesUnchanged"] is True and \
                post["specificPrivateDword1PersistenceVerified"] is True and \
                post["preWitnessSha256"] == preference_witnesses["pre"]["sha256"]
    rows = [json.loads(line) for line in (output / "scene-events.jsonl").read_text().splitlines()]
    failures = [row for row in rows if row.get("status") == "first_failure"]
    natives = [row for row in rows if row.get("phase") == "native_exception"]
    terminal = [row for row in rows if row.get("status") == "original_practice_terminal_result"]
    packet_failures = [row for row in rows if row.get("status") == "original_practice_packet_export_failed"]
    stop = next((row for row in reversed(rows) if "completedUpdateCalls" in row), {})
    proofs = [row for row in rows if row.get("status") in (
        "original_mechanical_prefabs_registered", "captured_practice_static_transporter_installed",
        "original_practice_context_created", "original_practice_wave_group_load_ready",
        "captured_practice_fixture_prepared", "original_aim_on_init_prerequisites_ready",
        "original_mechanical_prefab_hierarchy_ready", "original_practice_on_start_observed",
        "original_practice_loaded_inputs_verified")]
    pool_observations = [row for row in rows if row.get("status") in (
        "original_practice_skill_pool_entry", "original_practice_skill_pool_returned",
        "original_practice_fx_getter_return_inside_pool", "original_fx_controller_verified",
        "original_timeline_controller_verified", "original_graphic_options_prerequisites_verified",
        "original_graphic_options_on_init_verified", "practice_fx_cleanup_observer_installed",
        "practice_skeleton_setup_observer_installed", "original_skeleton_setup_move_next_entered",
        "original_skeleton_setup_null_guard_observed", "practice_skeleton_source_observer_installed",
        "original_skeleton_addresses_returned", "original_skeleton_source_loader_returned",
        "original_skeleton_source_constructed", "skeleton_source_observer_error",
        "original_practice_dp_registration_started", "original_practice_dp_registration_ready",
        "original_practice_rng_readback", "original_practice_playing_controls",
        "original_auto_contents_gate_readback", "original_practice_auto_preference_inputs_prepared")]
    finished = bool(terminal) and terminal[-1].get("completeBattle") is True and terminal[-1].get("verification", {}).get("passed") is True
    packet_exported = not result_filename or (packet_present and terminal[-1].get("originalPacketExported") is True if terminal else False)
    independent_decode = None
    if staging.get("independentManagedPacketDecodeRequired"):
        independent_decode = {"status": "not_available", "reason": "Original binary packet or completed export proof absent"}
        if packet_exported:
            try:
                if not all(unchanged.values()):
                    raise ValueError("Frozen decoder/input evidence changed; refuse execution")
                decoder_path = Path(staging["sources"]["packetArchiveDecoderSource"]["path"])
                spec = importlib.util.spec_from_file_location("archived_packet_decoder153", decoder_path)
                decoder = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(decoder)
                independent_decode = decoder.decode_archived_packet(output / result_filename,
                    output / ("practice" + suffix + "-independent-packet-decode.json"), terminal[-1],
                    json.loads(Path(staging["sources"]["modeInput"]["path"]).read_text()),
                    Path(staging["sources"]["packetDecoderBuildReceipt"]["path"]))
            except Exception as error:
                independent_decode = {"status": "failed", "errorType": type(error).__name__, "error": str(error),
                                      "rawOriginalPacketPreserved": True}
        packet_exported = packet_exported and independent_decode["status"] == "passed"
    rng_gate = None
    rng_gate_passed = index < 15
    if index >= 15:
        try:
            if staging.get("fullSharedRngStateRequired") is not True or not all(unchanged.values()):
                raise ValueError("Frozen required full RNG guard manifest/input proof missing or changed")
            gate_path = Path(staging["sources"]["rngArchiveGateSource"]["path"]).resolve()
            if gate_path != (HERE / "rng-state/archive_gate.py").resolve():
                raise ValueError("Exact reviewed full RNG archive gate path differs")
            expected_item = staging["sources"]["rngExpectedInput"]
            spec = importlib.util.spec_from_file_location("full_rng_archive_gate153", gate_path)
            gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
            rng_gate = gate.verify(rows, terminal[-1] if terminal else {},
                json.loads(Path(expected_item["path"]).read_text()), expected_item["sha256"])
            rng_gate_passed = rng_gate["status"] == "passed"
        except Exception as error:
            rng_gate = {"status": "failed", "required": True, "errors": [type(error).__name__ + ": " + str(error)]}
    passed = finished and packet_exported and not packet_failures and not failures and not natives and all(unchanged.values()) and run["returncode"] == 0 and not run["timed_out"] and preference_storage_passed and rng_gate_passed
    pid = re.search(r'"pid":\s*(\d+)', run.get("stdout", ""))
    report = {"schemaVersion": 1, "status": "passed" if passed else "failed", "scope": staging["scope"],
              "planSha256": staging["planSha256"], "captureSha256": staging["captureSha256"],
              "elapsedSeconds": run["elapsed_seconds"], "exitCode": run["returncode"], "timedOut": run["timed_out"],
              "privateDesktop": run["desktop"], "actualPlayerPid": int(pid[1]) if pid else None,
              "frozenSourceInputsUnchanged": unchanged, "firstFailures": failures, "nativeExceptions": natives,
              "autoPreferenceWitnesses": preference_witnesses, "requiredPreferenceStorageControlsPassed": preference_storage_passed,
              "partialProofs": proofs, "terminalResults": terminal, "completeBattle": finished,
              "originalPacketExportFailures": packet_failures,
              "independentManagedPacketDecode": independent_decode,
              "fullSharedRngStateVerification": rng_gate, "requiredFullSharedRngStateVerified": rng_gate_passed if index >= 15 else None,
              "fullSharedRngStateObservations": [row for row in rows if row.get("status") in
                  ("original_practice_full_shared_rng_observed", "original_practice_full_shared_rng_read_failed")],
              "originalPoolAndSingletonObservations": pool_observations,
              "originalPacketFilename": result_filename, "originalPacketFilePresent": packet_present,
              "originalPacketArtifact": {"filename": result_filename, "byteLength": (output / result_filename).stat().st_size,
                  "sha256": sha(output / result_filename), "format": staging.get("originalResultFormat", "native_diagnostic_json"),
                  "bytesRewritten": False} if packet_present else None,
              "originalPacketExportVerified": packet_exported,
              "observedPlaying": stop.get("observedPlaying", False),
              "completedUpdateCalls": stop.get("completedUpdateCalls", 0), "advancedTicks": stop.get("advancedTicks", 0),
              "normalNativeQuitRequested": any(row.get("phase") == "quit_requested" for row in rows),
              "shutdownExceptionsRetained": [row for row in rows if row.get("phase") == "native_shutdown_exception"],
              "fullAccuracyVerified": False, "productionIntegrated": False,
              "artifacts": {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    target = output / "verification.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"path": str(target), "sha256": sha(target), "status": report["status"],
                      "completedUpdateCalls": report["completedUpdateCalls"], "nativeErrors": len(natives),
                      "allFrozenInputsUnchanged": all(unchanged.values())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", type=int, required=True)
    main(parser.parse_args().candidate_index)

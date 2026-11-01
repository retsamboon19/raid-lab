"""Freeze captured settings+original snapshot constructor/converter readbacks; no battle."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
GAME = SANDBOX / "NIKKE/NIKKE/game"
HOOK = ROOT / "NIKKE/NIKKE/game/NKAB/dist/hi_shiftup_dont_mind_me.js"
HOOK_SHA = "779557044a3c3a72feb503ed9561b068fb4bd4e58e2946bcf4156e2e505727e9"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    config_path = SANDBOX / "sandbox-snapshot-readback1.json"
    if config_path.exists():
        raise FileExistsError("Preserve prior snapshot candidate")
    previous = SANDBOX / "catalog-bootstrap-output1"
    if json.loads((previous / "verification.json").read_text())["status"] != "passed" or \
            sha(previous / "scene-probe.js") != sha(GAME / "NKAB/dist/scene-probe.js"):
        raise ValueError("Previous native source must be archived exactly")
    if sha(HOOK) != HOOK_SHA:
        raise ValueError("Frozen dependency package changed")
    paths = {"driver": HERE / "candidate-modules/headless_driver.js",
             "settingsSource": HERE / "practice_settings.js",
             "settingsInput": HERE / "practice-settings-input.json",
             "reconstructionSource": HERE / "replay-input/reconstruct_snapshots.js",
             "originalInput": HERE / "replay-input/run1/native-replay-input.json",
             "expectedReadbacks": HERE / "replay-input/run1/native-conversion-expected.json"}
    settings = json.loads(paths["settingsInput"].read_text())
    actual_input = json.loads(paths["originalInput"].read_text())
    expected = json.loads(paths["expectedReadbacks"].read_text())
    if len(actual_input["characters"]) != 5 or actual_input["captureSha256"] != expected["captureSha256"] or \
            actual_input["captureSha256"] != settings["sourceCaptureSha256"]:
        raise ValueError("Captured inputs/readbacks/settings do not share the original reference")
    source = paths["driver"].read_text()
    source = source.replace("verified:retval.toInt32()!==0", "verified:(retval.toInt32() & 0xff)!==0")
    marker = '        record({phase:"original_tables_loaded"});'
    if source.count(marker) != 1:
        raise ValueError("Native table completion marker changed")
    source = source.replace(marker, marker + '''
        const pin=value=>{ if (!value || value.isNull()) throw new Error("Missing original retained object");
          roots.push(value.ref(true)); return value; };
        const staticImage=Il2Cpp.domain.assembly("NK.Runtime.StaticData").image;
        const emit=row=>record({phase:"captured_snapshot_readback",...row});
        record({phase:"captured_snapshot_readback_started",battleStarted:false,catalogInitialized:false});
        initializeCapturedPracticeSettings(runtime,pin,emit);
        const replay=runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,
          globalThis.CAPTURED_REPLAY_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED);
        globalThis.CAPTURED_NATIVE_SNAPSHOT_RECONSTRUCTION=replay;
        if (!replay.passed || replay.snapshots.length!==5 || replay.converted.length!==5)
          throw new Error("Five original snapshot conversions did not pass");
        record({phase:"captured_snapshot_readback_complete",passed:true,
          snapshots:replay.snapshots.length,converted:replay.converted.length,
          captureSha256:globalThis.CAPTURED_REPLAY_INPUT.captureSha256,
          battleStarted:false,catalogInitialized:false,transporterInstalled:false});
        finish(); return;''')
    source = source.replace("runMechanicsLifecycleProbe(record,finish,true);",
                           'throw new Error("Input readback scope cannot dispatch battle");')
    source = source.replace("__TABLE_ARCHIVE__", json.dumps(str(SANDBOX / "current-tables.zip")))
    source = source.replace("__SCRATCH_PROFILE__", json.dumps(str(SANDBOX / "profile")))
    source += "\nglobalThis.PRACTICE_SETTINGS_INPUT=" + json.dumps(settings, separators=(",", ":")) + ";\n"
    source += "globalThis.CAPTURED_REPLAY_INPUT=" + json.dumps(actual_input, separators=(",", ":")) + ";\n"
    source += "globalThis.CAPTURED_REPLAY_EXPECTED=" + json.dumps(expected, separators=(",", ":")) + ";\n"
    source += paths["settingsSource"].read_text() + "\n" + paths["reconstructionSource"].read_text()
    sys.path.insert(0, str(ROOT / "event-selector/chainsaw-man/catalog-repair/hook-testing"))
    from build_bundle import parse, DELIMITER
    headers, modules = parse(HOOK.read_bytes())
    dependencies = modules[2:]
    modules[0] = json.dumps({"version": 3, "file": "nmm_030.js", "sources": [], "names": [], "mappings": ""}, separators=(",", ":")).encode()
    modules[1] = source.encode()
    headers[1], headers[2] = f"{len(modules[0])} /src/nmm_030.js.map", f"{len(modules[1])} /src/nmm_030.js"
    # The old root logs are exact immutable archived prefixes; clear only after
    # matching their archived bytes so the new readback cannot consume stale events.
    for root_name, archive_name in (("scene-events.jsonl", "scene-events-appended.jsonl"),
                                    ("headless-bootstrap.log", "headless-bootstrap-appended.log"),
                                    ("offline-network.log", "offline-network-appended.log")):
        current, archived = GAME / root_name, previous / archive_name
        if current.exists():
            if not archived.is_file() or sha(current) != sha(archived):
                raise ValueError("Preserve exact previous native log before clearing " + root_name)
            current.unlink()
    (GAME / "NKAB/dist/scene-probe.js").write_bytes("\n".join(headers).encode()+DELIMITER+DELIMITER.join(modules))
    check_headers, check_modules = parse((GAME / "NKAB/dist/scene-probe.js").read_bytes())
    if check_headers != headers or check_modules[2:] != dependencies:
        raise ValueError("Frozen Frida dependencies changed")
    source_path = SANDBOX / "snapshot-readback1-source.js"
    with source_path.open("x", encoding="utf-8") as sink:
        sink.write(source)
    config = json.loads((SANDBOX / "sandbox-table-bootstrap1.json").read_text())
    config["output_dir"] = str(SANDBOX / "snapshot-readback-output1")
    for item in config["diagnostic_files"].values():
        item["sha256"] = sha(Path(item["path"]))
    with config_path.open("x", encoding="utf-8") as sink:
        json.dump(config, sink, indent=2)
    spec = importlib.util.spec_from_file_location("snapshot153_host", ROOT / "tools/raid-lab/native_player_host.py")
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    plan = host.validate(config_path)
    with (SANDBOX / "snapshot-readback-plan1.json").open("x", encoding="utf-8") as sink:
        json.dump(plan, sink, indent=2)
    staging = {"schemaVersion": 1, "planSha256": plan["plan_sha256"],
        "sources": {name: {"path": str(path), "sha256": sha(path)} for name, path in paths.items()},
        "captureSha256": actual_input["captureSha256"], "expectedReadbacksUsedOnlyAfterNativeConversion": True,
        "sourceSha256": sha(source_path), "packageDependenciesPreserved": True,
        "scope": "Captured original settings setters+five original snapshot constructors/converters/readbacks only",
        "nativeRunPerformed": False, "catalogInitialized": False, "battleStarted": False}
    with (SANDBOX / "snapshot-readback-staging1.json").open("x", encoding="utf-8") as sink:
        json.dump(staging, sink, indent=2)
    print(json.dumps({"config": str(config_path), "planSha256": plan["plan_sha256"], "launched": False}))


if __name__ == "__main__":
    main()

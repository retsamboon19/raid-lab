"""Freeze captured original team+376B transport readbacks, never install/start it."""
import argparse
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


def main(candidate_index=1):
    if not 1 <= candidate_index <= 8:
        raise ValueError("Bounded fresh fixture candidate index1..8 required")
    suffix = str(candidate_index)
    config_path = SANDBOX / ("sandbox-fixture-readback" + suffix + ".json")
    if config_path.exists():
        raise FileExistsError("Preserve prior fixture candidate")
    previous = SANDBOX / ("snapshot-readback-output1" if candidate_index == 1 else
                          "fixture-readback-output" + str(candidate_index - 1))
    prior = json.loads((previous / "verification.json").read_text())
    if prior["status"] not in ("passed", "failed") or prior.get("exitCode") != 0 or \
            sha(previous / "scene-probe.js") != sha(GAME / "NKAB/dist/scene-probe.js"):
        raise ValueError("Previous completed native source must be archived exactly")
    if sha(HOOK) != HOOK_SHA:
        raise ValueError("Frozen dependency package changed")
    paths = {"driver": HERE / "candidate-modules/headless_driver.js",
             "settingsSource": HERE / "practice_settings.js",
             "settingsInput": HERE / "practice-settings-input.json",
             "reconstructionSource": HERE / "replay-input/reconstruct_snapshots.js",
             "originalInput": HERE / "replay-input/run1/native-replay-input.json",
             "expectedReadbacks": HERE / "replay-input/run1/native-conversion-expected.json",
             "fixtureSource": HERE / "replay-input/prepare_practice_fixture.js",
             "fixtureInput": HERE / "replay-input/run1/native-fixture-input.json",
             "waveSource": HERE / "replay-input/practice_wave_resolver.js",
             "callbackSource": HERE / "practice_host_callbacks.js"}
    settings = json.loads(paths["settingsInput"].read_text())
    actual_input = json.loads(paths["originalInput"].read_text())
    expected = json.loads(paths["expectedReadbacks"].read_text())
    fixture = json.loads(paths["fixtureInput"].read_text())
    capture = actual_input["captureSha256"]
    if len(actual_input["characters"]) != 5 or any(digest != capture for digest in
       (expected["captureSha256"], settings["sourceCaptureSha256"], fixture["captureSha256"])) or \
       fixture["transporterValueSize"] != 376 or len(fixture["fields"]) != 61:
        raise ValueError("Original settings/snapshot/fixture packet binding changed")
    source = paths["driver"].read_text().replace("verified:retval.toInt32()!==0", "verified:(retval.toInt32() & 0xff)!==0")
    marker = '        record({phase:"original_tables_loaded"});'
    if source.count(marker) != 1:
        raise ValueError("Native table completion marker changed")
    source = source.replace(marker, marker + '''
        const pin=value=>{ if (!value || value.isNull()) throw new Error("Missing original retained object");
          roots.push(value.ref(true)); return value; };
        const staticImage=Il2Cpp.domain.assembly("NK.Runtime.StaticData").image;
        const emit=row=>record({phase:"captured_fixture_readback",...row});
        record({phase:"captured_fixture_readback_started",battleStarted:false,
          catalogInitialized:false,transporterInstalled:false});
        initializeCapturedPracticeSettings(runtime,pin,emit);
        const replay=runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,
          globalThis.CAPTURED_REPLAY_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED);
        globalThis.CAPTURED_NATIVE_SNAPSHOT_RECONSTRUCTION=replay;
        if (!replay.passed || replay.snapshots.length!==5 || replay.converted.length!==5)
          throw new Error("Five original snapshot conversions did not pass");
        const callbacks=createPracticeHostCallbacks(runtime,pin,emit);
        const waveLoader=createCapturedPracticeWaveResolver(staticImage,pin,emit);
        globalThis.CAPTURED_NATIVE_FIXTURE_ROOTS={replay,callbacks,waveLoader};
        waveLoader.begin(globalThis.CAPTURED_FIXTURE_INPUT.fixtureInput.wave.tableId);
        const fixturePoll=setInterval(()=>{
          if(finishing){clearInterval(fixturePoll);return;}
          onMain(()=>{
            try {
              if(!waveLoader.poll().ready)return;
              clearInterval(fixturePoll);
              const fixture=prepareCapturedPracticeFixture(runtime,staticImage,pin,emit,
                globalThis.CAPTURED_FIXTURE_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED,
                {replay,resolveNativeOwnerField:callbacks.resolveNativeOwnerField,
                  resolveWaveData:waveLoader.resolve});
              globalThis.CAPTURED_NATIVE_FIXTURE=fixture;
              callbacks.check();
              if(!fixture.passed||!fixture.transporterBox||fixture.fieldChecks.length!==61)
                throw new Error("Original61field fixture readback did not pass");
              record({phase:"captured_fixture_readback_complete",passed:true,
                readback:fixture.readback,fieldChecks:fixture.fieldChecks,
                teamChecks:fixture.teamChecks,callbackBoundary:callbacks.snapshot(),
                transporterExactReplay:fixture.transporterExactReplay,
                callbackBehaviorOriginal:fixture.callbackBehaviorOriginal,
                captureSha256:globalThis.CAPTURED_REPLAY_INPUT.captureSha256,
                battleStarted:false,catalogInitialized:false,transporterInstalled:false});
              finish();
            }catch(error){clearInterval(fixturePoll);fail("captured_fixture_readback_error",error);}
          });
        },100);
        return;''')
    source = source.replace("runMechanicsLifecycleProbe(record,finish,true);",
                           'throw new Error("Fixture readback scope cannot dispatch battle");')
    source = source.replace("__TABLE_ARCHIVE__", json.dumps(str(SANDBOX / "current-tables.zip")))
    source = source.replace("__SCRATCH_PROFILE__", json.dumps(str(SANDBOX / "profile")))
    for name, value in (("PRACTICE_SETTINGS_INPUT", settings), ("CAPTURED_REPLAY_INPUT", actual_input),
                        ("CAPTURED_REPLAY_EXPECTED", expected),
                        ("CAPTURED_FIXTURE_INPUT", {"fixtureInput": fixture, "snapshotInput": actual_input})):
        source += "\nglobalThis." + name + "=" + json.dumps(value, separators=(",", ":")) + ";\n"
    for name in ("settingsSource", "reconstructionSource", "fixtureSource", "waveSource", "callbackSource"):
        source += "\n" + paths[name].read_text()
    sys.path.insert(0, str(ROOT / "event-selector/chainsaw-man/catalog-repair/hook-testing"))
    from build_bundle import parse, DELIMITER
    headers, modules = parse(HOOK.read_bytes())
    dependencies = modules[2:]
    modules[0] = json.dumps({"version": 3, "file": "nmm_030.js", "sources": [], "names": [], "mappings": ""}, separators=(",", ":")).encode()
    modules[1] = source.encode()
    headers[1], headers[2] = f"{len(modules[0])} /src/nmm_030.js.map", f"{len(modules[1])} /src/nmm_030.js"
    for name in ("scene-events.jsonl", "headless-bootstrap.log", "offline-network.log"):
        current, archived = GAME / name, previous / name
        if current.exists():
            if not archived.is_file() or sha(current) != sha(archived):
                raise ValueError("Preserve previous native log before clearing " + name)
            current.unlink()
    (GAME / "NKAB/dist/scene-probe.js").write_bytes("\n".join(headers).encode()+DELIMITER+DELIMITER.join(modules))
    check_headers, check_modules = parse((GAME / "NKAB/dist/scene-probe.js").read_bytes())
    if check_headers != headers or check_modules[2:] != dependencies:
        raise ValueError("Frozen Frida dependencies changed")
    source_path = SANDBOX / ("fixture-readback" + suffix + "-source.js")
    with source_path.open("x", encoding="utf-8") as sink:
        sink.write(source)
    config = json.loads((SANDBOX / "sandbox-table-bootstrap1.json").read_text())
    config["output_dir"] = str(SANDBOX / ("fixture-readback-output" + suffix))
    for item in config["diagnostic_files"].values():
        item["sha256"] = sha(Path(item["path"]))
    with config_path.open("x", encoding="utf-8") as sink:
        json.dump(config, sink, indent=2)
    spec = importlib.util.spec_from_file_location("fixture153_host", ROOT / "tools/raid-lab/native_player_host.py")
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    plan = host.validate(config_path)
    with (SANDBOX / ("fixture-readback-plan" + suffix + ".json")).open("x", encoding="utf-8") as sink:
        json.dump(plan, sink, indent=2)
    staging = {"schemaVersion": 1, "planSha256": plan["plan_sha256"],
        "sources": {name: {"path": str(path), "sha256": sha(path)} for name, path in paths.items()},
        "captureSha256": capture, "expectedReadbacksUsedOnlyAfterNativeConversion": True,
        "sourceSha256": sha(source_path), "packageDependenciesPreserved": True,
        "scope": "Original settings,snapshots,flatteam,asyncwave and61transport field readbacks only; explicit host UI/output callbacks",
        "nativeRunPerformed": False, "catalogInitialized": False, "battleStarted": False,
        "transporterInstalled": False, "originalUiCallbacksReplayed": False}
    with (SANDBOX / ("fixture-readback-staging" + suffix + ".json")).open("x", encoding="utf-8") as sink:
        json.dump(staging, sink, indent=2)
    print(json.dumps({"config": str(config_path), "planSha256": plan["plan_sha256"], "launched": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", type=int, default=1)
    main(parser.parse_args().candidate_index)

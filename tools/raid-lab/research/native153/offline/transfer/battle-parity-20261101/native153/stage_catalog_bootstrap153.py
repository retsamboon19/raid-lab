"""Stage original153 catalog+SpotSetting loading, then quit without combat."""
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
    config_path = SANDBOX / "sandbox-catalog-bootstrap1.json"
    if config_path.exists():
        raise FileExistsError("Preserve catalog staging evidence")
    resources_path = SANDBOX / "catalog153-resources1.json"
    resources = json.loads(resources_path.read_text())
    old_output = SANDBOX / "table-bootstrap-output1"
    old_verification = json.loads((old_output / "verification.json").read_text())
    if old_verification["status"] != "passed" or \
            sha(GAME / "NKAB/dist/scene-probe.js") != sha(old_output / "scene-probe.js"):
        raise ValueError("Previous source bundle must be archived exactly before restaging")
    if sha(HOOK) != HOOK_SHA:
        raise ValueError("Frozen Frida package changed")
    driver_path = HERE / "candidate-modules/headless_driver.js"
    source = driver_path.read_text()
    boolean = "verified:retval.toInt32()!==0"
    if source.count(boolean) != 1:
        raise ValueError("Signature diagnostic bool source changed")
    source = source.replace(boolean, "verified:(retval.toInt32() & 0xff)!==0")
    dispatch = "          runMechanicsLifecycleProbe(record,finish,true);"
    if source.count(dispatch) != 1:
        raise ValueError("Original completion dispatch changed")
    source = source.replace(dispatch, '''          const settingClass=runtime.class("NK.Spot.SpotSetting");
          const load=settingClass.method("Load",0);
          if (Number(load.relativeVirtualAddress)!==0x076098F0)
            throw new Error("Exact153 SpotSetting.Load method changed");
          record({phase:"original153_spotsetting_load_started",battleStarted:false});
          const setting=invokeChecked(load,null);
          if (!setting || setting.isNull() || setting.class.type.name!=="NK.Spot.SpotSetting")
            throw new Error("Original153 SpotSetting.Load returned no original asset");
          roots.push(setting.ref(true));
          record({phase:"original153_spotsetting_loaded",originalAsset:true,battleStarted:false,
            className:setting.class.type.name,
            useAutoModeCamera:setting.field("UseAutoModeCamera").value,
            maxMoveSpeed:setting.field("MaxMoveSpeed").value,
            minMoveSpeed:setting.field("MinMoveSpeed").value});
          finish();''')
    source = source.replace("__TABLE_ARCHIVE__", json.dumps(str(SANDBOX / "current-tables.zip")))
    source = source.replace("__SCRATCH_PROFILE__", json.dumps(str(SANDBOX / "profile")))
    sys.path.insert(0, str(ROOT / "event-selector/chainsaw-man/catalog-repair/hook-testing"))
    from build_bundle import parse, DELIMITER
    headers, modules = parse(HOOK.read_bytes())
    dependencies = modules[2:]
    modules[0] = json.dumps({"version": 3, "file": "nmm_030.js", "sources": [],
                             "names": [], "mappings": ""}, separators=(",", ":")).encode()
    modules[1] = source.encode()
    headers[1], headers[2] = f"{len(modules[0])} /src/nmm_030.js.map", f"{len(modules[1])} /src/nmm_030.js"
    (GAME / "NKAB/dist/scene-probe.js").write_bytes("\n".join(headers).encode()+DELIMITER+DELIMITER.join(modules))
    actual_headers, actual = parse((GAME / "NKAB/dist/scene-probe.js").read_bytes())
    if actual_headers != headers or actual[2:] != dependencies:
        raise ValueError("Frozen dependency package changed")
    source_path = SANDBOX / "catalog-bootstrap1-source.js"
    with source_path.open("x", encoding="utf-8") as sink:
        sink.write(source)
    config = json.loads((SANDBOX / "sandbox-table-bootstrap1.json").read_text())
    config["output_dir"] = str(SANDBOX / "catalog-bootstrap-output1")
    for name, row in config["diagnostic_files"].items():
        row["sha256"] = sha(Path(row["path"]))
    with config_path.open("x", encoding="utf-8") as sink:
        json.dump(config, sink, indent=2)
    host_path = ROOT / "tools/raid-lab/native_player_host.py"
    spec = importlib.util.spec_from_file_location("current153_catalog_host", host_path)
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    plan = host.validate(config_path)
    with (SANDBOX / "catalog-bootstrap-plan1.json").open("x", encoding="utf-8") as sink:
        json.dump(plan, sink, indent=2)
    staged = {"schemaVersion": 1, "planSha256": plan["plan_sha256"], "frozenPackageSha256": HOOK_SHA,
              "resourceReceiptSha256": sha(resources_path), "sourceSha256": sha(source_path),
              "signatureDiagnosticMasksNativeAL": True, "packageDependenciesPreserved": True,
              "scope": "Original153 local patch/catalog initialization and original SpotSetting.Load only",
              "battleStarted": False, "nativeRunPerformed": False,
              "sourceStore": resources["sourceStore"]}
    with (SANDBOX / "catalog-bootstrap-staging1.json").open("x", encoding="utf-8") as sink:
        json.dump(staged, sink, indent=2)
    print(json.dumps({"config": str(config_path), "planSha256": plan["plan_sha256"], "launched": False}))


if __name__ == "__main__":
    main()

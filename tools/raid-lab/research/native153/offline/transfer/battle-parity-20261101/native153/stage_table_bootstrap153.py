"""Stage a current153 original table-loader proof; do not launch it.

This first candidate quits after original InitializeAndLoadAllAsync completes.
It has no battle module, fixture, account input, backend or catalog initialization.
"""
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
CLIENT_SHA = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    if sha(HOOK) != HOOK_SHA or sha(GAME / "GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Current source/client binding changed")
    config_path = SANDBOX / "sandbox-table-bootstrap1.json"
    if config_path.exists():
        raise FileExistsError("Preserve staged bootstrap evidence")
    tables = json.loads((SANDBOX / "current-tables-provenance.json").read_text())
    if sha(SANDBOX / "current-tables.zip") != tables["sha256"]:
        raise ValueError("Current original tables changed")
    driver = HERE / "candidate-modules/headless_driver.js"
    source = driver.read_text()
    marker = '        record({phase:"original_tables_loaded"});'
    if source.count(marker) != 1:
        raise ValueError("Original table completion insertion changed")
    source = source.replace(marker, marker + '\n'
        '        record({phase:"current153_table_bootstrap_complete",scope:"original_table_loader_only",\n'
        '          tablesSha256:' + json.dumps(tables["sha256"]) + ',battleStarted:false,catalogInitialized:false});\n'
        '        finish(); return;')
    source = source.replace('runMechanicsLifecycleProbe(record,finish,true);',
        'throw new Error("Table-only proof must never reach a battle dispatcher");')
    source = source.replace("__TABLE_ARCHIVE__", json.dumps(str(SANDBOX / "current-tables.zip")))
    source = source.replace("__SCRATCH_PROFILE__", json.dumps(str(SANDBOX / "profile")))
    parser_dir = ROOT / "event-selector/chainsaw-man/catalog-repair/hook-testing"
    sys.path.insert(0, str(parser_dir))
    from build_bundle import parse, DELIMITER
    headers, modules = parse(HOOK.read_bytes())
    if not headers[1].endswith(" /src/nmm_030.js.map") or not headers[2].endswith(" /src/nmm_030.js"):
        raise ValueError("Frozen Frida module ordering changed")
    original_dependencies = modules[2:]
    modules[0] = json.dumps({"version": 3, "file": "nmm_030.js", "sources": [],
                             "names": [], "mappings": ""}, separators=(",", ":")).encode()
    modules[1] = source.encode()
    headers[1] = f"{len(modules[0])} /src/nmm_030.js.map"
    headers[2] = f"{len(modules[1])} /src/nmm_030.js"
    destination = GAME / "NKAB/dist/scene-probe.js"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as sink:
        sink.write("\n".join(headers).encode() + DELIMITER + DELIMITER.join(modules))
    rebuilt_headers, rebuilt_modules = parse(destination.read_bytes())
    if rebuilt_headers != headers or rebuilt_modules[2:] != original_dependencies or rebuilt_modules[:2] != modules[:2]:
        raise ValueError("Frida source/dependency preservation failed")
    gadget_config = GAME / "frida-gadget.config"
    with gadget_config.open("x", encoding="utf-8") as sink:
        json.dump({"interaction": {"type": "script", "path": "NKAB/dist/scene-probe.js"}}, sink)
    (SANDBOX / "table-bootstrap1-source.js").write_text(source, encoding="utf-8")
    bootstrap = {"schema_version": 1, "mode": "unity_player_bootstrap", "sandbox_root": str(SANDBOX),
                 "private_desktop_guard": True, "artifacts": {"nikkeBase.dll": sha(GAME / "nikkeBase.dll")},
                 "source_sha256": sha(ROOT / "tools/raid-lab/native-player/HeadlessUnityEntry.cpp"),
                 "native_tested": False, "scope": "Freshly built reviewed private bootstrap source; runtime proof pending"}
    bootstrap_path = SANDBOX / "bootstrap-receipt.json"
    with bootstrap_path.open("x", encoding="utf-8") as sink:
        json.dump(bootstrap, sink, indent=2)
    config = {"schema_version": 1, "sandbox_root": str(SANDBOX), "game_executable": str(GAME / "nikke.exe"),
              "working_directory": str(GAME), "scratch_root": str(SANDBOX / "profile"),
              "output_dir": str(SANDBOX / "table-bootstrap-output1"), "max_seconds": 60,
              "args": ["-batchmode", "-nographics"],
              "expected_files": {name: {"path": str(GAME / name), "sha256": sha(GAME / name)} for name in
                  ("nikke.exe", "UnityPlayer.dll", "GameAssembly.dll", "nikkeBase.dll", "OfflineNetwork.dll")},
              "diagnostic_files": {name: {"path": str(GAME / name), "sha256": sha(GAME / name)} for name in
                  ("NKAB/dist/scene-probe.js", "frida-gadget.config", "d3d11.dll", "frida-gadget.dll")},
              "bootstrap_receipt": str(bootstrap_path), "network_receipt": str(SANDBOX / "network-receipt.json")}
    with config_path.open("x", encoding="utf-8") as sink:
        json.dump(config, sink, indent=2)
    host_path = ROOT / "tools/raid-lab/native_player_host.py"
    spec = importlib.util.spec_from_file_location("current153_host_validation", host_path)
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    plan = host.validate(config_path)
    with (SANDBOX / "table-bootstrap-plan1.json").open("x", encoding="utf-8") as sink:
        json.dump(plan, sink, indent=2)
    receipt = {"schemaVersion": 1, "planSha256": plan["plan_sha256"], "sourceDriverSha256": sha(driver),
               "stagedDriverSha256": sha(SANDBOX / "table-bootstrap1-source.js"),
               "frozenPackageSha256": HOOK_SHA, "packageDependenciesPreserved": True,
               "productionHookModuleRetained": False, "tableArchiveSha256": tables["sha256"],
               "tablesLoaded": False, "catalogInitialized": False, "battleStarted": False,
               "gameLaunched": False, "integrationReadyReceiptCreated": False}
    with (SANDBOX / "table-bootstrap-staging1.json").open("x", encoding="utf-8") as sink:
        json.dump(receipt, sink, indent=2)
    print(json.dumps({"config": str(config_path), "planSha256": plan["plan_sha256"],
                      "hostDryRunPassed": True, "gameLaunched": False}))


if __name__ == "__main__":
    main()

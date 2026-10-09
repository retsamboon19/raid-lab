"""Prepare source-bound mechanical asset manifests for current Intercept profiles.

Preparation reads the installed client/catalog/chunk store and writes only a new
research JSON. It never stages a player, launches Unity, or changes game files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import zstandard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIVATE = ROOT / "tools/raid-lab/private"
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
ARCHIVE = PRIVATE / "native-current-tables-2df7134a.zip"
REGISTRY = HERE / "mechanics-encounters-current.json"
COMMON = HERE / "mechanics-geometry-source-v2.json"
OUTPUT_DIR = HERE / "profile-assets"
CLIENT_SHA = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"
ARCHIVE_SHA = "42611495f81734528e8d9f3b4286ed2f8531ad0d75be087a1fb8ef39f9c32367"
TABLES = ("InterceptSpecialTable.mpk", "InterceptAnomalousTable.mpk",
          "WaveDataTable.wave_Intercept_001.mpk", "MonsterTable.mpk",
          "MonsterModelTable.mpk", "QuickTimeEventTable.mpk")
PRESENTATION_ROLES = ("ui_canvas_control", "overlay_canvas", "instant_overlay_canvas",
    "camera1_canvas", "camera2_canvas", "popup_canvas", "always_canvas",
    "character_map", "spot_camera", "auto_camera", "ui_aim", "aim_ui_ref",
    "prefab_root", "monster_controller", "summon_controller", "qte_controller")

sys.path.insert(0, str(HERE))
from build_logged_bundle_evidence import database, verify_bundle  # noqa: E402
from mechanics_encounter_assets import selected_entry  # noqa: E402
from mechanics_geometry_source import extract_objects  # noqa: E402

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def row_sha(row: dict) -> str:
    return digest(json.dumps(row, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8"))


def unique(rows: list[dict], **fields: object) -> dict:
    found = [row for row in rows if all(row.get(key) == value for key, value in fields.items())]
    if len(found) != 1:
        raise ValueError(f"Expected exactly one current table row {fields}, got {len(found)}")
    return found[0]


def decode_current() -> tuple[dict[str, list[dict]], dict[str, str]]:
    if sha(ARCHIVE) != ARCHIVE_SHA:
        raise ValueError("Current MPK archive changed")
    with zipfile.ZipFile(ARCHIVE) as archive:
        raw = {name: archive.read(name) for name in TABLES}
    with tempfile.TemporaryDirectory(dir=PRIVATE) as temporary:
        temp = Path(temporary).resolve()
        if not temp.is_relative_to(PRIVATE.resolve()):
            raise ValueError("Temporary decode escaped research directory")
        with zipfile.ZipFile(temp / "selected.zip", "w") as out:
            for name, data in raw.items():
                out.writestr(name, data)
        reader = ROOT / "tools/raid-lab/offline-reader/bin/Debug/net10.0/OfflineReader.exe"
        subprocess.run([str(reader), str(temp / "selected.zip"), str(temp / "decoded")],
                       check=True, capture_output=True, text=True)
        decoded = temp / "decoded"
        status = json.loads((decoded / "manifest.json").read_text(encoding="utf-8"))
        if status["errors"]:
            raise ValueError(f"Current selected MPK decode failed: {status['errors']}")
        tables = {
            "special": json.loads((decoded / "InterceptSpecialTable.mpk.json").read_text(encoding="utf-8")),
            "anomaly": json.loads((decoded / "InterceptAnomalousTable.mpk.json").read_text(encoding="utf-8")),
            "waves": json.loads((decoded / "InterceptWaves.json").read_text(encoding="utf-8")),
            "monsters": json.loads((decoded / "MonsterTable.mpk.json").read_text(encoding="utf-8")),
            "models": json.loads((decoded / "MonsterModelTable.mpk.json").read_text(encoding="utf-8")),
            "qte": json.loads((decoded / "QuickTimeEventTable.mpk.json").read_text(encoding="utf-8")),
        }
    return tables, {name: digest(data) for name, data in raw.items()}


def source_rows(profile: dict, tables: dict[str, list[dict]]) -> tuple[dict, dict, list[tuple[dict, dict]], list[dict]]:
    if profile.get("mode") not in ("special", "anomaly"):
        raise ValueError("Only registered current Intercept modes are supported")
    row = unique(tables[profile["mode"]], **profile["tableKey"])
    wave = unique(tables["waves"], StageId=profile["wave"]["stageId"])
    if row_sha(row) != profile["tableRowSha256"] or row_sha(wave) != profile["wave"]["sourceRowSha256"]:
        raise ValueError("Registry/table or wave content differs")
    if row != profile["sourceTableRow"] or profile["tableKey"] != {"Group": 1, "Id": row["Id"]}:
        raise ValueError("Registry Intercept row identity differs")
    expected_encounter = {"timeLimit": wave["BattleTime"], "waveId": row["SpotId"],
                          "monsterStageLv": row["MonsterStageLv"],
                          "dynamicObjectLv": row["DynamicObjectStageLv"],
                          "raidLvChangeGroup": row["MonsterStageLvChangeGroup"]}
    if any(profile["encounter"].get(key) != value for key, value in expected_encounter.items()):
        raise ValueError("Registry encounter transport differs from current tables")
    if (row.get("SpotType") != "WaveData" or row.get("SpotId") != wave["StageId"] or
            wave.get("SpotMod") != "Intercept" or wave.get("GroupId") != "wave_Intercept_001" or
            wave.get("BackgroundName") != profile["wave"]["backgroundKey"] or
            wave.get("BattleTime") != profile["wave"]["battleTimeSeconds"] or
            wave.get("TargetList") != profile["wave"]["targetMonsterIds"]):
        raise ValueError("Registered Intercept routing differs from current tables")
    paths = [item["WavePath"] for item in wave["WaveData"] if item.get("WavePath")]
    if not wave.get("PointData") or not wave.get("PointDataFly") or not paths or paths != profile["wave"]["wavePaths"]:
        raise ValueError("Current point/wave paths differ or are absent")
    if len(profile["targets"]) != len(wave["TargetList"]) or [bound["monsterId"] for bound in profile["targets"]] != wave["TargetList"]:
        raise ValueError("Registered target mapping differs from current wave")
    targets = []
    for bound in profile["targets"]:
        monster = unique(tables["monsters"], Id=bound["monsterId"])
        model = unique(tables["models"], Id=monster["MonsterModelId"])
        if (row_sha(monster) != bound["monsterRowSha256"] or
                row_sha(model) != bound["modelRowSha256"] or
                model["MonPrefab"] != bound["monsterPrefab"] or
                monster["SpotAi"] != bound["spotAi"] or
                model["Id"] != bound["modelId"] or
                model.get("ResourceId") != bound["resourceId"]):
            raise ValueError("Registered target monster/model differs")
        targets.append((monster, model))
    qte = [item for item in tables["qte"] if any(monster["Id"] in item.get("MonsterId", [])
                                                   for monster, _ in targets)]
    if any(not item.get("QtePrefab") for item in qte):
        raise ValueError("Linked QTE row has no prefab key")
    return row, wave, targets, qte


def decode_body(verified: dict, bundle: str, source_store: Path) -> bytes:
    if bundle not in verified:
        raise ValueError(f"Source bundle lacks verified patch bytes: {bundle}")
    decoder = zstandard.ZstdDecompressor()
    output = bytearray()
    with source_store.open("rb") as stream:
        for chunk in verified[bundle]["chunks"]:
            stream.seek(chunk["store_offset"])
            packed = stream.read(chunk["compressed_bytes"])
            if digest(packed) != chunk["compressed_sha256"]:
                raise ValueError("Changed installed source chunk")
            output.extend(decoder.decompress(packed))
    data = bytes(output)
    if not data.startswith(b"UnityFS") or digest(data) != verified[bundle]["verified_decoded"]["decodedSha256"]:
        raise ValueError("Decoded source UnityFS body mismatch")
    return data


def select_assets(catalog, wave: dict, targets: list[tuple[dict, dict]],
                  qte: list[dict], quality: str) -> dict[str, dict]:
    if quality not in ("hd", "sd"):
        raise ValueError("Quality must be hd or sd")
    background = wave["BackgroundName"]
    entries = {
        f"profile_background_{quality}": selected_entry(
            catalog, background, quality=1 if quality == "hd" else 2,
            main_contains=f"spotbackground({quality})_assets_{background}_"),
        "ground_points": selected_entry(catalog, wave["PointData"], quality=0),
        "fly_points": selected_entry(catalog, wave["PointDataFly"], quality=0),
    }
    for i, path in enumerate(sorted({item["WavePath"] for item in wave["WaveData"] if item.get("WavePath")})):
        entries[f"wave_path_{i}"] = selected_entry(catalog, path, quality=0)
    for i, (monster, model) in enumerate(targets):
        prefab = model["MonPrefab"]
        entries[f"monster_{i}_{quality}"] = selected_entry(
            catalog, f"SpotMonster/{prefab}",
            main_contains=f"spotmonster({quality})_assets_spotmonster/{prefab}_")
        map_key = f"SpotMonsterMap/{prefab}_map"
        entries[f"monster_map_{i}"] = selected_entry(catalog, map_key, quality=0)
        entries[f"behavior_tree_{i}"] = selected_entry(
            catalog, f"ExternalBehavior/spot/{monster['SpotAi']}", quality=0)
    for i, prefab in enumerate(sorted({item["QtePrefab"] for item in qte})):
        entries[f"qte_prefab_{i}"] = selected_entry(catalog, prefab, quality=0)
    required_types = {"profile_background": "UnityEngine.GameObject",
        "ground_points": "UnityEngine.TextAsset", "fly_points": "UnityEngine.TextAsset",
        "wave_path": "UnityEngine.TextAsset", "monster_": "UnityEngine.GameObject",
        "monster_map": "UnityEngine.GameObject",
        "behavior_tree": "BehaviorDesigner.Runtime.ExternalBehaviorTree",
        "qte_prefab": "UnityEngine.GameObject"}
    for role, entry in entries.items():
        expected = next((type_name for prefix, type_name in required_types.items()
                         if role.startswith(prefix)), None)
        if expected is None or entry["assetType"] != expected:
            raise ValueError(f"Wrong asset type for {role}: {entry['assetType']}")
    return entries


def prepare(product_id: str, quality: str, output: Path) -> None:
    output = output.resolve()
    if output.exists() or not output.is_relative_to(OUTPUT_DIR.resolve()):
        raise ValueError("Output must be a new file inside the profile-assets directory")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client changed")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if (registry.get("installedClientSha256") != CLIENT_SHA or
            registry.get("scope") != "current_intercept_special_and_anomaly_only" or
            len(registry.get("profiles", [])) != 10):
        raise ValueError("Current Intercept registry identity differs")
    profiles = [item for item in registry["profiles"] if item.get("productId") == product_id]
    if len(profiles) != 1:
        raise ValueError("Unknown or ambiguous current Intercept profile")
    profile = profiles[0]
    tables, table_shas = decode_current()
    row, wave, targets, qte = source_rows(profile, tables)
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    entries = select_assets(catalog, wave, targets, qte, quality)
    bundle_names = sorted({name for entry in entries.values() for name in entry["bundles"]})
    source_store = CORE / "chunk/store.cdb"
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    verified, builtins, unavailable = {}, {}, {}
    decoder = zstandard.ZstdDecompressor()
    with source_store.open("rb") as stream:
        for name in bundle_names:
            try:
                item = verify_bundle(patch, index, name, source_store, stream, decoder)
            except (OSError, ValueError) as exc:
                unavailable[name] = str(exc)
                continue
            if item["source"] == "patch_chunk_store":
                verified[name] = item
            else:
                builtins[name] = item
    background_role = f"profile_background_{quality}"
    background_entry = entries[background_role]
    main_prefix = f"spotbackground({quality})_assets_{wave['BackgroundName']}_"
    main = [name for name in background_entry["bundles"] if name.startswith(main_prefix)]
    if len(main) != 1:
        raise ValueError("Background main bundle ambiguous")
    geometry = None
    if main[0] in verified:
        payload = decode_body(verified, main[0], source_store)
        geometry = extract_objects(payload, background_role)
        focus = {"camera_position", "aim_position", "character_position", "hide_position",
                 "cover", "cover_1", "cover_2", "cover_3", "cover_4", "cover_5",
                 wave["BackgroundName"].lower()}
        geometry["game_objects"] = [item for item in geometry["game_objects"]
                                    if item["name"].lower() in focus]
        geometry["components"] = [item for item in geometry["components"]
                                  if item["type"] in ("SpotSingleMap", "CinemachineVirtualCamera", "Camera")]
        if not any(item["type"] == "SpotSingleMap" for item in geometry["components"]):
            raise ValueError("Current background lacks SpotSingleMap geometry")
    common = json.loads(COMMON.read_text(encoding="utf-8"))
    if common["installed_client_sha256"] != CLIENT_SHA:
        raise ValueError("Common mechanical presentation source differs")
    bundles = dict(common["bundles"])
    if geometry is not None:
        bundles[background_role] = {"catalog_key": wave["BackgroundName"],
            "catalog_entry": background_entry, "bundle_name": main[0],
            "decoded_bytes": len(payload), "decoded_sha256": digest(payload), **geometry}
    source_evidence = HERE / "kraken-resource-staging-evidence.json"
    bootstrap = json.loads(source_evidence.read_text(encoding="utf-8"))["core_bootstrap_files"]
    result = {"schema_version": 1, "status": "static_catalog_mapping_only",
        "geometry_status": "serialized_source_geometry_only" if geometry else "source_bundle_unavailable",
        "installed_client_sha256": CLIENT_SHA,
        "profile": {"id": product_id, "mode": profile["mode"],
                    "intercept_group": 1, "intercept_id": row["Id"],
                    "wave_id": wave["StageId"], "target_monster_ids": wave["TargetList"],
                    "background_role": background_role, "quality": quality,
                    "spot_mod": wave["SpotMod"]},
        "source": {"current_registry_path": str(REGISTRY), "current_registry_sha256": sha(REGISTRY),
                   "current_table_archive_path": str(ARCHIVE),
                   "current_table_archive_sha256": sha(ARCHIVE),
                   "current_table_entry_sha256": table_shas,
                   "common_geometry_path": str(COMMON), "common_geometry_sha256": sha(COMMON),
                   "patch_catalog_sha256": sha(patch_path),
                   "addressables_catalog_sha256": sha(raw_path),
                   "chunk_index_sha256": sha(index_path)},
        "current_rows": {"intercept": {"id": row["Id"], "group": row["Group"],
                        "sha256": row_sha(row)},
                         "wave": {k: wave.get(k) for k in ("StageId", "GroupId", "SpotMod",
                                    "BattleTime", "PointData", "PointDataFly", "BackgroundName", "Theme", "TargetList")},
                         "wave_sha256": row_sha(wave),
                         "targets": [{"monster_id": m["Id"], "monster_model_id": model["Id"],
                                      "monster_prefab": model["MonPrefab"], "spot_ai": m["SpotAi"],
                                      "monster_row_sha256": row_sha(m),
                                      "model_row_sha256": row_sha(model)} for m, model in targets],
                         "monster_linked_qte": [{"id": item["Id"], "prefab": item["QtePrefab"],
                                                  "groups": item["GroupId"], "row_sha256": row_sha(item)}
                                                 for item in qte]},
        "asset_entries": entries, "bundles": bundles,
        "common_mechanical_presentations": {"roles": PRESENTATION_ROLES,
            "geometry_source_path": str(COMMON), "geometry_source_sha256": sha(COMMON),
            "runtime_source_path": str(HERE / "mechanics_geometry_runtime.js"),
            "runtime_source_sha256": sha(HERE / "mechanics_geometry_runtime.js"),
            "normal_intercept_prefab_evidence_sha256": sha(HERE / "normal-intercept-prefab-evidence.json")},
        "client_sha256": CLIENT_SHA, "installed_patch_root": str(CORE.parent),
        "sandbox_patch_root_suffix": "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch",
        "core_bootstrap_files": bootstrap,
        "core_chunk_store": {"path": str(source_store.relative_to(ROOT)).replace("\\", "/"),
                             "logical_bytes": source_store.stat().st_size, "copied": False},
        "catalog_sha256": sha(patch_path), "index_sha256": sha(index_path),
        "bundle_scope": sorted(verified), "verified_bundles": verified,
        "built_in_bundles": builtins, "unavailable_bundles": unavailable,
        "ready_for_chunk_staging": not unavailable and geometry is not None,
        "limits": ["Preparation did not stage resources or run a native player.",
                   "Monster-linked QTE rows are candidates, not proof their mode tree executes them.",
                   "Serialized map transforms are not live world/screen coordinates.",
                   "Cosmetic asset completion is outside this mechanical closure."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "profile": product_id, "quality": quality,
                      "source_bundles": len(bundle_names), "verified_patch": len(verified),
                      "builtins": len(builtins), "unavailable": unavailable,
                      "ready_for_chunk_staging": result["ready_for_chunk_staging"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_id", help="one exact ID in the ten-profile current Intercept registry")
    parser.add_argument("--quality", choices=("hd", "sd"), default="hd")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or OUTPUT_DIR / f"{args.profile_id}-{args.quality}-geometry-source.json"
    prepare(args.profile_id, args.quality, output)


if __name__ == "__main__":
    main()

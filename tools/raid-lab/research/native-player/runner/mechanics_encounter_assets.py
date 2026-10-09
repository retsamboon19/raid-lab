"""Bind Mirror Container's original mechanical assets to the installed source.

``prepare`` is read-only apart from its new JSON output. ``stage`` requires an
explicit expected scratch-receipt hash and is intended only after the private
player has exited. It delegates sparse chunk writes to stage_resource_chunks.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import UnityPy
import zstandard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIVATE = ROOT / "tools/raid-lab/private"
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
ARCHIVE = PRIVATE / "native-current-tables-2df7134a.zip"
COMMON = HERE / "mechanics-geometry-source-v2.json"
OUTPUT = HERE / "mirror-geometry-source.json"
SANDBOX = PRIVATE / "native-player-20261008a"
CHUNK_RECEIPT = SANDBOX / "resource-chunks.json"
STAGE_RECEIPT = SANDBOX / "mirror-asset-staging-receipt.json"
OBSERVED_EFFECT = "effect-spot-monster_library_assets_fx_m_blue_lastdead_c61458257a4bf148468465f92b158bdf.bundle"
OBSERVED_EFFECT_HASH = "43015207e502d1ba8b882ddd58ad6ff9"
EFFECT_SOURCE = HERE / "mirror-dynamic-effect-source.json"
EFFECT_STAGE_RECEIPT = SANDBOX / "mirror-dynamic-effect-staging-receipt.json"
CLIENT_SHA = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"
WAVE_ID = 6302006
MONSTER_ID = 4510010123

sys.path.insert(0, str(HERE))
from build_logged_bundle_evidence import database, verify_bundle  # noqa: E402
from mechanics_geometry_source import extract_objects  # noqa: E402

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index  # noqa: E402


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def selected_entry(catalog, key: str, *, quality: int | None = None,
                   main_contains: str | None = None) -> dict:
    rows = catalog.execute(
        """select e.rowid,e.quality_texture,e.dependency_key_rowid,
                  i.internal_id,t.class_name
           from keys k join key_entries ke on ke.key_rowid=k.rowid
           join entries e on e.rowid=ke.entry_rowid
           join internal_ids i on i.rowid=e.internal_id_rowid
           join types t on t.rowid=e.type_rowid where k.key=?""", (key,)).fetchall()
    found = []
    for row_id, q, dependency, internal, asset_type in rows:
        todo = [dependency] if dependency else []
        seen = set()
        bundles = {internal} if internal.endswith(".bundle") else set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            for child, name in catalog.execute(
                """select e.dependency_key_rowid,i.internal_id from key_entries ke
                   join entries e on e.rowid=ke.entry_rowid
                   join internal_ids i on i.rowid=e.internal_id_rowid
                   where ke.key_rowid=?""", (node,)):
                if child:
                    todo.append(child)
                if name.endswith(".bundle"):
                    bundles.add(name)
        if (quality is None or q == quality) and (
                main_contains is None or any(main_contains in name for name in bundles)):
            found.append({"key": key, "rowId": row_id, "quality": q,
                          "assetType": asset_type, "internalId": internal,
                          "bundles": sorted(bundles)})
    if len(found) != 1 or not found[0]["bundles"]:
        raise ValueError(f"Expected one exact catalog entry for {key}, got {len(found)}")
    return found[0]


def current_wave() -> tuple[dict, dict, dict, list[dict], dict[str, str]]:
    with zipfile.ZipFile(ARCHIVE) as archive:
        entries = {name: archive.read(name) for name in (
            "WaveDataTable.wave_Intercept_001.mpk", "MonsterTable.mpk",
            "MonsterModelTable.mpk", "QuickTimeEventTable.mpk")}
    with tempfile.TemporaryDirectory(dir=PRIVATE) as temporary:
        temp = Path(temporary).resolve()
        if not temp.is_relative_to(PRIVATE.resolve()):
            raise ValueError("Temporary decode escaped private research directory")
        with zipfile.ZipFile(temp / "input.zip", "w") as archive:
            for name, body in entries.items():
                archive.writestr(name, body)
        reader = ROOT / "tools/raid-lab/offline-reader/bin/Debug/net10.0/OfflineReader.exe"
        subprocess.run([str(reader), str(temp / "input.zip"), str(temp / "out")],
                       check=True, capture_output=True, text=True)
        rows = json.loads((temp / "out/InterceptWaves.json").read_text(encoding="utf-8"))
        monsters = json.loads((temp / "out/MonsterTable.mpk.json").read_text(encoding="utf-8"))
        models = json.loads((temp / "out/MonsterModelTable.mpk.json").read_text(encoding="utf-8"))
        qte_rows = json.loads((temp / "out/QuickTimeEventTable.mpk.json").read_text(encoding="utf-8"))
    wave = next((row for row in rows if row["StageId"] == WAVE_ID), None)
    expected = {"SpotMod": "Intercept", "BackgroundName": "sbg_cityforestcrystalxba001_001",
                "PointData": "point_grd_mirrorcontainer_001",
                "PointDataFly": "point_fly_mirrorcontainer_001"}
    if not wave or any(wave.get(k) != v for k, v in expected.items()) or wave.get("TargetList") != [MONSTER_ID]:
        raise ValueError("Current Mirror wave identity differs from the selected encounter")
    if not wave.get("WaveData") or wave["WaveData"][0].get("WavePath") != "b_fly_mirrorcontainer_01":
        raise ValueError("Current Mirror spawn path differs")
    monster = next((row for row in monsters if row["Id"] == MONSTER_ID), None)
    if monster is None or monster.get("SpotAi") != "bt_xba001_psid_intercept":
        raise ValueError("Current Mirror monster/behavior tree identity differs")
    model = next((row for row in models if row["Id"] == monster["MonsterModelId"]), None)
    if model is None or model.get("MonPrefab") != "xba001_psid_intercept":
        raise ValueError("Current Mirror monster prefab identity differs")
    selected_qte = [row for row in qte_rows if row["Id"] in (10159, 10160, 10161, 10162)]
    if len(selected_qte) != 4 or any(MONSTER_ID not in row["MonsterId"] or
                                    row["QtePrefab"] != "QTEPrefab_MirrorContainer"
                                    for row in selected_qte):
        raise ValueError("Current Mirror QTE prefab identity differs")
    return wave, monster, model, selected_qte, {name: digest(body) for name, body in entries.items()}


def decoded_bundle(entry: dict, verified: dict, source: Path) -> bytes:
    name = next((name for name in entry["bundles"] if "spotbackground(hd)_assets_sbg_cityforestcrystalxba001_001" in name), None)
    if name is None or name not in verified:
        raise ValueError("Exact Mirror HD background bundle is not source-verified")
    decoder = zstandard.ZstdDecompressor()
    data = bytearray()
    with source.open("rb") as stream:
        for chunk in verified[name]["chunks"]:
            stream.seek(chunk["store_offset"])
            packed = stream.read(chunk["compressed_bytes"])
            if digest(packed) != chunk["compressed_sha256"]:
                raise ValueError("Changed installed Mirror background chunk")
            data.extend(decoder.decompress(packed))
    result = bytes(data)
    if digest(result) != verified[name]["verified_decoded"]["decodedSha256"] or not result.startswith(b"UnityFS"):
        raise ValueError("Mirror background decoded body mismatch")
    return result


def prepare(output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite source evidence: {output}")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client changed")
    wave, monster, model, qte_rows, table_shas = current_wave()
    common = json.loads(COMMON.read_text(encoding="utf-8"))
    if common["installed_client_sha256"] != CLIENT_SHA:
        raise ValueError("Common geometry source client mismatch")
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source_store = CORE / "chunk/store.cdb"
    roles = {
        "mirror_background_hd": (wave["BackgroundName"], 1, "spotbackground(hd)_assets_sbg_cityforestcrystalxba001_001"),
        "mirror_monster_hd": ("SpotMonster/xba001_psid_intercept", None, "spotmonster(hd)_assets_spotmonster/xba001_psid_intercept"),
        "mirror_monster_map": ("SpotMonsterMap/xba001_psid_intercept_map", 0, "spotmonstermap_assets_spotmonstermap/xba001_psid_intercept_map"),
        "mirror_ground_points": (wave["PointData"], 0, None),
        "mirror_fly_points": (wave["PointDataFly"], 0, None),
        "mirror_wave_path": (wave["WaveData"][0]["WavePath"], 0, None),
        "mirror_behavior_tree": ("ExternalBehavior/spot/bt_xba001_psid_intercept", 0, None),
        "mirror_qte_prefab": ("QTEPrefab_MirrorContainer", 0, None),
    }
    entries = {role: selected_entry(catalog, key, quality=quality, main_contains=main)
               for role, (key, quality, main) in roles.items()}
    # Trial 125 proved this original on-init request is dynamic: it is absent
    # from the static Addressables dependency closure of the monster prefab.
    bundle_names = sorted({name for entry in entries.values() for name in entry["bundles"]}
                          | {OBSERVED_EFFECT})
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
    background = entries["mirror_background_hd"]
    if any(name not in verified and name not in builtins for name in background["bundles"]):
        raise ValueError("Mirror HD background closure incomplete: " +
                         json.dumps({k: v for k, v in unavailable.items() if k in background["bundles"]}))
    payload = decoded_bundle(background, verified, source_store)
    geometry = extract_objects(payload, "mirror_background_hd")
    focus_names = {"camera_position", "aim_position", "character_position",
                   "hide_position", "cover", "cover_1", "cover_2", "cover_3",
                   "cover_4", "cover_5", wave["BackgroundName"]}
    geometry["game_objects"] = [obj for obj in geometry["game_objects"]
                                if obj["name"].lower() in focus_names]
    geometry["components"] = [c for c in geometry["components"] if c["type"] in
                              ("SpotSingleMap", "CinemachineVirtualCamera", "Camera")]
    if not any(c["type"] == "SpotSingleMap" for c in geometry["components"]):
        raise ValueError("Mirror HD background lacks source-bound SpotSingleMap")
    common_bundles = common["bundles"]
    if "kraken_background_hd" not in common_bundles:
        raise ValueError("Common geometry source lacks retained Kraken role")
    bundles = dict(common_bundles)
    hd_name = next(name for name in background["bundles"] if
                   "spotbackground(hd)_assets_sbg_cityforestcrystalxba001_001" in name)
    bundles["mirror_background_hd"] = {
        "catalog_key": background["key"], "catalog_entry": background,
        "bundle_name": hd_name, "decoded_bytes": len(payload),
        "decoded_sha256": digest(payload), **geometry}
    result = {
        "schema_version": 1, "status": "static_catalog_mapping_only",
        "geometry_status": "serialized_source_geometry_only",
        "installed_client_sha256": CLIENT_SHA,
        "profile": {"id": "anomaly-mirror-container", "intercept_group": 1,
                    "intercept_id": 1, "wave_id": WAVE_ID,
                    "monster_id": MONSTER_ID, "background_role": "mirror_background_hd",
                    "spot_mod": wave["SpotMod"]},
        "source": {"patch_catalog_sha256": sha(patch_path),
                   "addressables_catalog_sha256": sha(raw_path),
                   "chunk_index_sha256": sha(index_path),
                   "current_table_archive_path": str(ARCHIVE),
                   "current_table_archive_sha256": sha(ARCHIVE),
                   "current_table_entry_sha256": table_shas,
                   "common_geometry_path": str(COMMON),
                   "common_geometry_sha256": sha(COMMON)},
        "wave_current_row": {k: wave.get(k) for k in
                             ("StageId", "GroupId", "SpotMod", "BattleTime",
                              "PointData", "PointDataFly", "BackgroundName", "Theme", "TargetList")},
        "monster_current_row": {k: monster.get(k) for k in
                                ("Id", "MonsterModelId", "SpotAi", "ElementId")},
        "model_current_row": {k: model.get(k) for k in
                              ("Id", "MonPrefab", "ResourceId")},
        "qte_current_rows": [{k: row.get(k) for k in
                              ("Id", "MonsterId", "QtePrefab", "GroupId", "ElementId")}
                             for row in sorted(qte_rows, key=lambda row: row["Id"])],
        "asset_entries": entries, "bundles": bundles,
        "runtime_observed_bundles": [{"name": OBSERVED_EFFECT, "native_trial": 125,
                                      "source": "original_management_on_init runtime load"}],
        "client_sha256": CLIENT_SHA,
        "installed_patch_root": str(CORE.parent),
        "sandbox_patch_root_suffix": "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch",
        "core_bootstrap_files": json.loads((HERE / "kraken-resource-staging-evidence.json").read_text(encoding="utf-8"))["core_bootstrap_files"],
        "core_chunk_store": {"path": str(source_store.relative_to(ROOT)).replace("\\", "/"),
                             "logical_bytes": source_store.stat().st_size, "copied": False},
        "catalog_sha256": sha(patch_path), "index_sha256": sha(index_path),
        "bundle_scope": sorted(verified), "verified_bundles": verified,
        "built_in_bundles": builtins, "unavailable_bundles": unavailable,
        "ready_for_chunk_staging": not unavailable,
        "limits": ["No native player or Unity scene was run by preparation.",
                   "Serialized transforms are not final live world/screen coordinates.",
                   "Current Mirror behavior-tree bundle is source-verified but not decoded into tactical node parity here.",
                   "Common presentation roles are inherited byte-for-byte from the retained v2 geometry source."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "bundles": len(bundle_names), "verified_patch": len(verified),
                      "builtins": len(builtins), "unavailable": unavailable,
                      "ready_for_chunk_staging": result["ready_for_chunk_staging"]}))


def stage(source_path: Path, expected_before: str) -> None:
    source_path = source_path.resolve(strict=True)
    if source_path != OUTPUT.resolve() or not CHUNK_RECEIPT.resolve().is_relative_to(SANDBOX.resolve()):
        raise ValueError("Stage paths escaped the bounded Mirror/private-player scope")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("profile", {}).get("id") != "anomaly-mirror-container" or not source.get("ready_for_chunk_staging"):
        raise ValueError("Mirror source evidence is incomplete")
    if OBSERVED_EFFECT not in source.get("verified_bundles", {}):
        raise ValueError("Mirror source omits the trial-125 runtime effect; use the observed-effect repair evidence")
    if STAGE_RECEIPT.exists():
        raise ValueError("Refusing to overwrite existing Mirror stage receipt")
    before = sha(CHUNK_RECEIPT)
    if before != expected_before.lower():
        raise ValueError("Scratch resource receipt changed since staging handoff")
    command = [sys.executable, str(HERE / "stage_resource_chunks.py"),
               "--evidence", str(source_path)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    after = sha(CHUNK_RECEIPT)
    receipt = {"schema_version": 1, "status": "source_verified_sparse_chunks_staged",
               "profile": source["profile"], "source_path": str(source_path),
               "source_sha256": sha(source_path), "before_resource_receipt_sha256": before,
               "after_resource_receipt_sha256": after,
               "resource_receipt_path": str(CHUNK_RECEIPT),
               "staging_command": command, "staging_result": completed.stdout.strip(),
               "original_client_sha256": CLIENT_SHA,
               "limit": "Source staging only; original Mirror encounter has not been run or tactically validated."}
    STAGE_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage_receipt": str(STAGE_RECEIPT), "sha256": sha(STAGE_RECEIPT)}))


def repair_observed_effect(expected_before: str) -> None:
    """Stage the exact trial-125 dynamic load missing from static prefab closure."""
    if EFFECT_SOURCE.exists() or EFFECT_STAGE_RECEIPT.exists():
        raise ValueError("Refusing to overwrite observed-effect source or stage evidence")
    before = sha(CHUNK_RECEIPT)
    if before != expected_before.lower():
        raise ValueError("Scratch resource receipt changed since effect repair handoff")
    mirror = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if (mirror.get("profile", {}).get("id") != "anomaly-mirror-container" or
            not mirror.get("ready_for_chunk_staging") or
            OBSERVED_EFFECT in mirror.get("verified_bundles", {}) or
            OBSERVED_EFFECT in mirror.get("built_in_bundles", {})):
        raise ValueError("Original Mirror source closure differs from trial-125 diagnosis")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client differs from observed native trial")
    patch_path = CORE / "catalog.ndb"
    if sha(patch_path) != mirror["catalog_sha256"]:
        raise ValueError("Installed patch catalog differs from Mirror source")
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    if sha(raw_path) != mirror["source"]["addressables_catalog_sha256"]:
        raise ValueError("Installed Addressables catalog differs from Mirror source")
    catalog = database(raw_path)
    count = catalog.execute("select count(*) from internal_ids where internal_id=?",
                            (OBSERVED_EFFECT,)).fetchone()[0]
    if count != 1:
        raise ValueError(f"Observed runtime bundle has {count} installed catalog identities")
    index_path = CORE / "chunk/store.cdb.idx"
    if sha(index_path) != mirror["index_sha256"]:
        raise ValueError("Installed index differs from Mirror source")
    source_store = CORE / "chunk/store.cdb"
    with source_store.open("rb") as stream:
        verified = verify_bundle(patch, decode_index(index_path.read_bytes()),
                                 OBSERVED_EFFECT, source_store, stream,
                                 zstandard.ZstdDecompressor())
    first = verified["chunks"][0]
    if (verified["source"] != "patch_chunk_store" or
            first["hash"] != OBSERVED_EFFECT_HASH or first["store_offset"] != 581070014 or
            first["compressed_bytes"] != 7679 or first["decoded_bytes"] != 99403):
        raise ValueError("Observed trial-125 chunk no longer maps to verified installed source")
    evidence = {"schema_version": 1, "status": "static_catalog_mapping_only",
                "profile": mirror["profile"], "installed_client_sha256": CLIENT_SHA,
                "source_mirror_path": str(OUTPUT), "source_mirror_sha256": sha(OUTPUT),
                "observed_trial": 125, "observed_missing_bundle": OBSERVED_EFFECT,
                "catalog_sha256": mirror["catalog_sha256"],
                "index_sha256": mirror["index_sha256"],
                "sandbox_patch_root_suffix": mirror["sandbox_patch_root_suffix"],
                "core_chunk_store": mirror["core_chunk_store"],
                "core_bootstrap_files": mirror["core_bootstrap_files"],
                "bundle_scope": [OBSERVED_EFFECT],
                "verified_bundles": {OBSERVED_EFFECT: verified},
                "limit": "One original runtime-requested bundle; no native outcome claimed."}
    EFFECT_SOURCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    command = [sys.executable, str(HERE / "stage_resource_chunks.py"),
               "--evidence", str(EFFECT_SOURCE)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    receipt = json.loads(CHUNK_RECEIPT.read_text(encoding="utf-8"))
    if OBSERVED_EFFECT not in receipt["bundles"]:
        raise ValueError("Updated scratch receipt lacks observed bundle")
    expected_hashes = [item["hash"] for item in verified["chunks"]]
    if receipt["bundles"][OBSERVED_EFFECT] != expected_hashes:
        raise ValueError("Updated scratch receipt has different observed-bundle chunks")
    staged_path = SANDBOX / mirror["sandbox_patch_root_suffix"] / "core/chunk/store.cdb"
    original_path = CORE / "chunk/store.cdb"
    with staged_path.open("rb") as staged, original_path.open("rb") as original:
        for item in verified["chunks"]:
            original.seek(item["store_offset"])
            staged.seek(item["store_offset"])
            if staged.read(item["compressed_bytes"]) != original.read(item["compressed_bytes"]):
                raise ValueError(f"Observed bundle chunk differs in scratch: {item['hash']}")
    report = {"schema_version": 1, "status": "observed_dynamic_bundle_source_staged",
              "observed_trial": 125, "bundle": OBSERVED_EFFECT,
              "first_chunk_hash": OBSERVED_EFFECT_HASH,
              "source_evidence_path": str(EFFECT_SOURCE),
              "source_evidence_sha256": sha(EFFECT_SOURCE),
              "before_resource_receipt_sha256": before,
              "after_resource_receipt_sha256": sha(CHUNK_RECEIPT),
              "source_bundle_decoded_sha256": verified["verified_decoded"]["decodedSha256"],
              "chunk_count": len(verified["chunks"]), "staging_command": command,
              "staging_result": completed.stdout.strip(),
              "limit": "Chunk repair only; no native battle rerun or result validation."}
    EFFECT_STAGE_RECEIPT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage_receipt": str(EFFECT_STAGE_RECEIPT),
                      "sha256": sha(EFFECT_STAGE_RECEIPT), "chunks": len(verified["chunks"])}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--output", type=Path, default=OUTPUT)
    stage_parser = sub.add_parser("stage")
    stage_parser.add_argument("--source", type=Path, default=OUTPUT)
    stage_parser.add_argument("--expected-before-receipt-sha256", required=True)
    effect_parser = sub.add_parser("repair-observed-effect")
    effect_parser.add_argument("--expected-before-receipt-sha256", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output)
    elif args.command == "stage":
        stage(args.source, args.expected_before_receipt_sha256)
    else:
        repair_observed_effect(args.expected_before_receipt_sha256)


if __name__ == "__main__":
    main()

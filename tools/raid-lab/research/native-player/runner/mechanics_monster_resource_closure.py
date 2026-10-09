"""Bind a current Intercept monster's original SpotEffect/SpotSkill resource graph.

Only exact current MonsterTable skill IDs and serialized AssetReference GUIDs are
followed. The output is a stage_resource_chunks.py source evidence document;
this preparation never changes the private player or installed game.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import UnityPy
import zstandard

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mechanics_profile_assets import (ARCHIVE, CLIENT_SHA, CORE, REGISTRY, ROOT,
                                     database, decode_body, decode_current, sha,
                                     source_rows, verify_bundle)
from mechanics_encounter_assets import selected_entry

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index

MIRROR_SOURCE = HERE / "mirror-geometry-source.json"
MIRROR_OBSERVED = HERE / "mirror-dynamic-effect-source.json"
MIRROR_OUTPUT = HERE / "mirror-monster-mechanical-resource-closure.json"
SANDBOX = ROOT / "tools/raid-lab/private/native-player-20261008a"
RESOURCE_RECEIPT = SANDBOX / "resource-chunks.json"
MIRROR_STAGE_RECEIPT = SANDBOX / "mirror-monster-resource-closure-staging-receipt.json"
MIRROR_DEFAULT_OUTPUT = HERE / "mirror-default-spotskill-source.json"
MIRROR_DEFAULT_STAGE_RECEIPT = SANDBOX / "mirror-default-spotskill-staging-receipt.json"
GUID = re.compile(r"[0-9a-f]{32}\Z")
FAILED_BUNDLE = re.compile(r"key='([^']+\.bundle)'", re.IGNORECASE)


def catalog_key_exists(catalog, key: str) -> bool:
    count = catalog.execute("select count(*) from keys where key=?", (key,)).fetchone()[0]
    if count > 1:
        raise ValueError(f"Ambiguous original catalog key: {key}")
    return count == 1


def asset_refs(value, path: str = "") -> list[dict]:
    found = []
    if isinstance(value, dict):
        if "m_AssetGUID" in value:
            guid = value["m_AssetGUID"]
            if guid:
                if not isinstance(guid, str) or not GUID.fullmatch(guid):
                    raise ValueError(f"Malformed original AssetReference GUID at {path}")
                found.append({"field": path, "guid": guid,
                              "subobject": value.get("m_SubObjectName", ""),
                              "subobject_type": value.get("m_SubObjectType", "")})
        for key, child in value.items():
            found.extend(asset_refs(child, f"{path}.{key}" if path else key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(asset_refs(child, f"{path}[{index}]"))
    return found


def serialized_data(verified: dict, bundle: str, expected_name: str,
                    expected_class: str, internal_id: str) -> dict:
    payload = decode_body(verified, bundle, CORE / "chunk/store.cdb")
    env = UnityPy.load(io.BytesIO(payload))
    objects = {obj.path_id: obj for obj in env.objects}
    # The installed Addressables location uses the bundle container key,
    # identical to the catalog internalId. A serialized m_Name may differ
    # (Ultra SpotSkill/510631 contains m_Name 510611); it is not the lookup key.
    if not GUID.fullmatch(internal_id) or internal_id not in env.container:
        raise ValueError(f"Original catalog internalId absent from bundle: {internal_id}")
    obj = env.container[internal_id]
    if obj.type.name != "MonoBehaviour":
        raise ValueError(f"Original catalog target is not MonoBehaviour: {internal_id}")
    data = obj.read_typetree()
    script_ptr = data.get("m_Script", {})
    if script_ptr.get("m_FileID") != 0 or script_ptr.get("m_PathID") not in objects:
        raise ValueError(f"Unresolved MonoScript in {bundle}")
    script = objects[script_ptr["m_PathID"]].read_typetree()
    if script.get("m_ClassName") != expected_class or not isinstance(data.get("m_Name"), str):
        raise ValueError(f"Unexpected original class/name at catalog target: {internal_id}")
    return {"asset_name": expected_name, "serialized_name": data["m_Name"],
            "name_matches_key": data["m_Name"] == expected_name,
            "catalog_internal_id": internal_id, "class": expected_class,
            "bundle": bundle, "decoded_sha256": hashlib.sha256(payload).hexdigest(),
            "asset_references": asset_refs(data)}


def build(profile_id: str, output: Path) -> None:
    output = output.resolve()
    if output.exists() or not output.is_relative_to(HERE.resolve()):
        raise ValueError("Output must be a new native-player research JSON")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client changed")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    profiles = [row for row in registry["profiles"] if row["productId"] == profile_id]
    if len(profiles) != 1:
        raise ValueError("Expected exactly one current Intercept profile")
    profile = profiles[0]
    tables, table_entry_shas = decode_current()
    _, wave, targets, _ = source_rows(profile, tables)
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source_store = CORE / "chunk/store.cdb"
    scriptable_entries = {}
    missing_spot_effect_keys = []
    missing_skill_keys = []
    for monster, _ in targets:
        spot_key = f"ScriptableData/Effect/Monster/SpotEffect/{monster['Id']}"
        if not catalog_key_exists(catalog, spot_key):
            if profile_id == "anomaly-mirror-container":
                raise ValueError(f"Observed original SpotEffect load has no catalog key: {spot_key}")
            missing_spot_effect_keys.append({"monster_id": monster["Id"], "absent_key": spot_key})
        else:
            spot = selected_entry(catalog, spot_key, quality=0)
            if spot["assetType"] != "NK.Spot.ScriptableData.Effect.MonsterIndividualEffectData":
                raise ValueError(f"Wrong original SpotEffect asset type: {spot_key}")
            scriptable_entries[spot_key] = spot
        for skill in monster.get("SkillData", []):
            skill_id = skill["SkillId"]
            key = f"ScriptableData/Effect/Monster/SpotSkill/{skill_id}"
            if not catalog_key_exists(catalog, key):
                missing_skill_keys.append({"monster_id": monster["Id"],
                                           "skill_id": skill_id, "absent_key": key})
                continue
            entry = selected_entry(catalog, key, quality=0)
            if entry["assetType"] != "NK.Spot.ScriptableData.Effect.MonsterSkillEffectData":
                raise ValueError(f"Wrong original SpotSkill asset type: {key}")
            scriptable_entries[key] = entry
    verified, builtins = {}, {}
    def verify_names(names):
        with source_store.open("rb") as stream:
            for name in sorted(names):
                if name in verified or name in builtins:
                    continue
                row = verify_bundle(patch, index, name, source_store, stream,
                                    zstandard.ZstdDecompressor())
                (verified if row["source"] == "patch_chunk_store" else builtins)[name] = row
    verify_names({name for entry in scriptable_entries.values() for name in entry["bundles"]})
    serialized = []
    for key, entry in sorted(scriptable_entries.items()):
        primary = [name for name in entry["bundles"] if name.startswith("scriptabledata_assets_")]
        if len(primary) != 1 or primary[0] not in verified:
            raise ValueError(f"Original serialized data bundle ambiguous/unavailable: {key}")
        expected_class = ("MonsterIndividualEffectData" if "/SpotEffect/" in key
                          else "MonsterSkillEffectData")
        record = serialized_data(verified, primary[0], key.rsplit("/", 1)[1],
                                 expected_class, entry["internalId"])
        record["catalog_key"] = key
        serialized.append(record)
    referenced_entries = {}
    for record in serialized:
        for reference in record["asset_references"]:
            guid = reference["guid"]
            if guid not in referenced_entries:
                entry = selected_entry(catalog, guid, quality=0)
                if entry["assetType"] == "UnityEngine.ResourceManagement.ResourceProviders.IAssetBundleResource":
                    raise ValueError(f"Serialized GUID resolves to bundle instead of asset: {guid}")
                referenced_entries[guid] = entry
    verify_names({name for entry in referenced_entries.values() for name in entry["bundles"]})
    mirror_binding = None
    if profile_id == "anomaly-mirror-container":
        mirror = json.loads(MIRROR_SOURCE.read_text(encoding="utf-8"))
        observed = json.loads(MIRROR_OBSERVED.read_text(encoding="utf-8"))
        if (mirror["profile"]["monster_id"] != targets[0][0]["Id"] or
                observed["source_mirror_sha256"] != sha(MIRROR_SOURCE)):
            raise ValueError("Mirror original source/observed runtime load differs")
        observed_names = list(observed["verified_bundles"])
        verify_names(observed_names)
        mirror_binding = {"geometry_source_sha256": sha(MIRROR_SOURCE),
                          "observed_effect_source_sha256": sha(MIRROR_OBSERVED),
                          "observed_runtime_bundles": observed_names}
        base = mirror
    else:
        base = json.loads((HERE / "kraken-resource-staging-evidence.json").read_text(encoding="utf-8"))
    result = {"schema_version": 1, "status": "static_catalog_mapping_only",
              "scope": "current MonsterTable SpotEffect and SpotSkill serialized AssetReference closure",
              "profile": {"id": profile_id, "wave_id": wave["StageId"],
                          "monster_ids": [monster["Id"] for monster, _ in targets]},
              "source": {"client_sha256": CLIENT_SHA, "registry_sha256": sha(REGISTRY),
                         "archive_sha256": sha(ARCHIVE), "archive_entry_sha256": table_entry_shas,
                         "patch_catalog_sha256": sha(patch_path),
                         "addressables_catalog_sha256": sha(raw_path),
                         "chunk_index_sha256": sha(index_path),
                         "mirror_binding": mirror_binding},
              "scriptable_entries": scriptable_entries,
              "serialized_source": serialized,
              "referenced_entries": referenced_entries,
              "missing_spot_effect_keys": missing_spot_effect_keys,
              "missing_spot_skill_keys": missing_skill_keys,
              "client_sha256": CLIENT_SHA,
              "catalog_sha256": sha(patch_path), "index_sha256": sha(index_path),
              "sandbox_patch_root_suffix": base["sandbox_patch_root_suffix"],
              "core_chunk_store": base["core_chunk_store"],
              "core_bootstrap_files": base["core_bootstrap_files"],
              "bundle_scope": sorted(verified), "verified_bundles": verified,
              "built_in_bundles": builtins,
              "limits": ["Only exact installed monster/skill IDs and nonempty serialized GUID refs are followed.",
                         "Absent SpotEffect/SpotSkill keys are recorded; no asset is inferred for them.",
                         "Addressables dependency closure is verified, but unobserved runtime string loads may remain.",
                         "This does not run or validate native combat."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "spot_effects": len(targets) - len(missing_spot_effect_keys),
                      "spot_skills": len(scriptable_entries) - len(targets) + len(missing_spot_effect_keys),
                      "guid_assets": len(referenced_entries),
                      "patch_bundles": len(verified), "builtins": len(builtins),
                      "absent_optional_spot_effect_keys": len(missing_spot_effect_keys),
                      "absent_optional_skill_keys": len(missing_skill_keys)}))


def stage_mirror(expected_before: str) -> None:
    if MIRROR_STAGE_RECEIPT.exists():
        raise ValueError("Refusing to overwrite Mirror monster-closure staging receipt")
    evidence = json.loads(MIRROR_OUTPUT.read_text(encoding="utf-8"))
    if (evidence.get("profile", {}).get("id") != "anomaly-mirror-container" or
            evidence["source"]["mirror_binding"]["geometry_source_sha256"] != sha(MIRROR_SOURCE) or
            evidence["source"]["mirror_binding"]["observed_effect_source_sha256"] != sha(MIRROR_OBSERVED) or
            evidence["source"]["registry_sha256"] != sha(REGISTRY)):
        raise ValueError("Mirror monster closure is stale or from a different profile")
    before = sha(RESOURCE_RECEIPT)
    if before != expected_before.lower():
        raise ValueError("Scratch receipt differs from exact staging handoff")
    command = [sys.executable, str(HERE / "stage_resource_chunks.py"),
               "--evidence", str(MIRROR_OUTPUT)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    receipt = json.loads(RESOURCE_RECEIPT.read_text(encoding="utf-8"))
    for name, bundle in evidence["verified_bundles"].items():
        if receipt["bundles"].get(name) != [item["hash"] for item in bundle["chunks"]]:
            raise ValueError(f"Staged receipt omitted a source-bound bundle: {name}")
    report = {"schema_version": 1, "status": "source_bound_monster_closure_staged",
              "profile_id": "anomaly-mirror-container",
              "source_evidence_path": str(MIRROR_OUTPUT),
              "source_evidence_sha256": sha(MIRROR_OUTPUT),
              "before_resource_receipt_sha256": before,
              "after_resource_receipt_sha256": sha(RESOURCE_RECEIPT),
              "patch_bundles": len(evidence["verified_bundles"]),
              "builtin_bundles": len(evidence["built_in_bundles"]),
              "previous_receipt": receipt["previous_receipt"],
              "staging_command": command, "staging_result": completed.stdout.strip(),
              "limit": "Original source closure staging only; no native combat validated."}
    MIRROR_STAGE_RECEIPT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage_receipt": str(MIRROR_STAGE_RECEIPT),
                      "sha256": sha(MIRROR_STAGE_RECEIPT),
                      "resource_receipt_sha256": sha(RESOURCE_RECEIPT)}))


def observed_failed_bundles(verification: Path) -> list[str]:
    """Only exact failed scriptable bundles observed by the native trial."""
    report = json.loads(verification.read_text(encoding="utf-8"))
    found = set()
    for item in report.get("errors", []):
        for name in FAILED_BUNDLE.findall(item.get("error", item.get("detail", ""))):
            if name.startswith("scriptabledata_assets_scriptabledata/effect/monster/spotskill/default_"):
                found.add(name)
    if not found:
        raise ValueError("No native-observed default SpotSkill failure in verification")
    return sorted(found)


def build_observed_defaults(profile_id: str, verification: Path, output: Path,
                            base_evidence: Path = MIRROR_OUTPUT) -> None:
    """Bind runtime-requested default SpotSkills and their serialized GUID closure.

    The original loader can request string fallbacks absent from MonsterTable's
    numeric SkillId list. The native verification, not a guessed weapon family,
    defines which exact keys may enter this supplemental source manifest.
    """
    output = output.resolve()
    if output.exists() or not output.is_relative_to(HERE.resolve()):
        raise ValueError("Output must be a new native-player research JSON")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client changed")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    profiles = [row for row in registry["profiles"] if row["productId"] == profile_id]
    if len(profiles) != 1:
        raise ValueError("Expected exactly one current Intercept profile")
    tables, table_entry_shas = decode_current()
    _, wave, targets, _ = source_rows(profiles[0], tables)
    observed_names = observed_failed_bundles(verification)
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source_store = CORE / "chunk/store.cdb"
    entries = {}
    for name in observed_names:
        matches = []
        # Enumerate only default SpotSkill keys; every selected entry must
        # resolve to exactly one observed bundle and the original asset type.
        for (key,) in catalog.execute(
                "select key from keys where key like 'ScriptableData/Effect/Monster/SpotSkill/Default_%'"):
            entry = selected_entry(catalog, key, quality=0)
            if name in entry["bundles"]:
                matches.append((key, entry))
        if len(matches) != 1:
            raise ValueError(f"Observed bundle has {len(matches)} default catalog keys: {name}")
        key, entry = matches[0]
        if entry["assetType"] != "NK.Spot.ScriptableData.Effect.MonsterSkillEffectData":
            raise ValueError(f"Wrong default SpotSkill type: {key}")
        entries[key] = entry
    verified, builtins = {}, {}
    def verify_names(names):
        with source_store.open("rb") as stream:
            for name in sorted(names):
                if name in verified or name in builtins:
                    continue
                row = verify_bundle(patch, index, name, source_store, stream,
                                    zstandard.ZstdDecompressor())
                (verified if row["source"] == "patch_chunk_store" else builtins)[name] = row
    verify_names({name for entry in entries.values() for name in entry["bundles"]})
    serialized = []
    for key, entry in sorted(entries.items()):
        primary = [name for name in entry["bundles"] if name.startswith(
            "scriptabledata_assets_scriptabledata/effect/monster/spotskill/default_")]
        if len(primary) != 1 or primary[0] not in verified:
            raise ValueError(f"Original default SpotSkill bundle unavailable: {key}")
        record = serialized_data(verified, primary[0], key.rsplit("/", 1)[1],
                                 "MonsterSkillEffectData", entry["internalId"])
        record["catalog_key"] = key
        serialized.append(record)
    referenced_entries = {}
    absent_reference_guids = []
    for record in serialized:
        for reference in record["asset_references"]:
            guid = reference["guid"]
            if not catalog_key_exists(catalog, guid):
                absent_reference_guids.append({"catalog_key": record["catalog_key"], **reference})
            elif guid not in referenced_entries:
                referenced_entries[guid] = selected_entry(catalog, guid, quality=0)
    verify_names({name for entry in referenced_entries.values() for name in entry["bundles"]})
    base = json.loads(base_evidence.read_text(encoding="utf-8"))
    if profile_id != base["profile"]["id"] or base["source"]["registry_sha256"] != sha(REGISTRY):
        raise ValueError("Supplement must match current staged profile closure")
    result = {"schema_version": 1, "status": "static_catalog_mapping_only",
              "scope": "native-observed default SpotSkill keys and serialized AssetReference closure",
              "profile": {"id": profile_id, "wave_id": wave["StageId"],
                          "monster_ids": [monster["Id"] for monster, _ in targets]},
              "source": {"client_sha256": CLIENT_SHA, "registry_sha256": sha(REGISTRY),
                         "archive_sha256": sha(ARCHIVE), "archive_entry_sha256": table_entry_shas,
                         "patch_catalog_sha256": sha(patch_path),
                         "addressables_catalog_sha256": sha(raw_path),
                         "chunk_index_sha256": sha(index_path),
                         "prior_monster_closure_sha256": sha(base_evidence),
                         "native_verification_path": str(verification),
                         "native_verification_sha256": sha(verification),
                         "loader_rvas": {"MonsterSkillEffectData.GetFullPath(string,AttackType)": "0x061B4830",
                                         "MonsterEffector.GetData.MoveNext": "0x062E67D0"}},
              "observed_failed_bundles": observed_names,
              "scriptable_entries": entries, "serialized_source": serialized,
              "referenced_entries": referenced_entries,
              "absent_reference_guids": absent_reference_guids,
              "client_sha256": CLIENT_SHA,
              "catalog_sha256": sha(patch_path), "index_sha256": sha(index_path),
              "sandbox_patch_root_suffix": base["sandbox_patch_root_suffix"],
              "core_chunk_store": base["core_chunk_store"],
              "core_bootstrap_files": base["core_bootstrap_files"],
              "bundle_scope": sorted(verified), "verified_bundles": verified,
              "built_in_bundles": builtins,
              "limits": ["Only default keys that failed in the bound native trial are selected.",
                         "The exact caller selecting RLD from Mirror weapon rows remains unresolved.",
                         "Some serialized AssetReference GUIDs have no installed catalog key and are recorded unresolved.",
                         "Other unobserved string fallbacks may remain; no native rerun is claimed."]}
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "keys": sorted(entries), "guid_assets": len(referenced_entries),
                      "absent_guid_references": len(absent_reference_guids),
                      "patch_bundles": len(verified), "builtins": len(builtins)}))


def stage_observed_defaults(profile_id: str, output: Path, expected_before: str) -> None:
    if MIRROR_DEFAULT_STAGE_RECEIPT.exists():
        raise ValueError("Refusing to overwrite default SpotSkill stage receipt")
    evidence = json.loads(output.read_text(encoding="utf-8"))
    if (evidence["profile"]["id"] != profile_id or
            evidence["source"]["prior_monster_closure_sha256"] != sha(MIRROR_OUTPUT) or
            evidence["source"]["native_verification_sha256"] != sha(
                Path(evidence["source"]["native_verification_path"])) or
            evidence["source"]["registry_sha256"] != sha(REGISTRY)):
        raise ValueError("Default SpotSkill evidence is stale")
    before = sha(RESOURCE_RECEIPT)
    if before != expected_before.lower():
        raise ValueError("Scratch receipt differs from exact staging handoff")
    command = [sys.executable, str(HERE / "stage_resource_chunks.py"),
               "--evidence", str(output)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    receipt = json.loads(RESOURCE_RECEIPT.read_text(encoding="utf-8"))
    for name, bundle in evidence["verified_bundles"].items():
        if receipt["bundles"].get(name) != [item["hash"] for item in bundle["chunks"]]:
            raise ValueError(f"Staged receipt omitted source-bound bundle: {name}")
    report = {"schema_version": 1, "status": "source_bound_observed_defaults_staged",
              "profile_id": profile_id, "source_evidence_path": str(output),
              "source_evidence_sha256": sha(output),
              "before_resource_receipt_sha256": before,
              "after_resource_receipt_sha256": sha(RESOURCE_RECEIPT),
              "patch_bundles": len(evidence["verified_bundles"]),
              "builtin_bundles": len(evidence["built_in_bundles"]),
              "previous_receipt": receipt["previous_receipt"],
              "staging_command": command, "staging_result": completed.stdout.strip(),
              "limit": "Source-bound staging only; subsequent native combat remains unverified."}
    MIRROR_DEFAULT_STAGE_RECEIPT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage_receipt": str(MIRROR_DEFAULT_STAGE_RECEIPT),
                      "sha256": sha(MIRROR_DEFAULT_STAGE_RECEIPT),
                      "resource_receipt_sha256": sha(RESOURCE_RECEIPT)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_id", help="exact current Intercept registry profile")
    parser.add_argument("--output", type=Path, default=MIRROR_OUTPUT)
    parser.add_argument("--stage-mirror", action="store_true")
    parser.add_argument("--observed-defaults", type=Path)
    parser.add_argument("--base-closure-evidence", type=Path, default=MIRROR_OUTPUT)
    parser.add_argument("--stage-observed-defaults", action="store_true")
    parser.add_argument("--expected-before-receipt-sha256")
    args = parser.parse_args()
    if args.stage_observed_defaults:
        if args.profile_id != "anomaly-mirror-container" or not args.expected_before_receipt_sha256:
            raise ValueError("Stage requires exact Mirror profile and prior receipt SHA")
        stage_observed_defaults(args.profile_id, args.output, args.expected_before_receipt_sha256)
    elif args.observed_defaults:
        build_observed_defaults(args.profile_id, args.observed_defaults, args.output,
                                args.base_closure_evidence)
    elif args.stage_mirror:
        if args.profile_id != "anomaly-mirror-container" or not args.expected_before_receipt_sha256:
            raise ValueError("Stage requires exact Mirror profile and prior receipt SHA")
        stage_mirror(args.expected_before_receipt_sha256)
    else:
        build(args.profile_id, args.output)


if __name__ == "__main__":
    main()

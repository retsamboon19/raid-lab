"""Exact installed-table registry for current Special/Anomaly Intercept.

Generation uses the repository's MemoryPack OfflineReader. Loading regenerates
the small registry from the bound source bytes and rejects any changed registry,
client, decoder, enum evidence, archive, or selected table entry. This is an
identity/transport input contract, not a validation of battle mechanics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REGISTRY = HERE / "mechanics-encounters-current.json"
ARCHIVE = ROOT / "tools/raid-lab/private/native-current-tables-2df7134a.zip"
CLIENT = ROOT / "NIKKE/NIKKE/game/GameAssembly.dll"
TYPE_FACTS = ROOT / "client-decompiled/metadata/installed-2df7134a/type-facts/type-facts.jsonl"
READER = ROOT / "tools/raid-lab/offline-reader/bin/Debug/net10.0/OfflineReader.exe"
READER_SOURCE = ROOT / "tools/raid-lab/offline-reader/Program.cs"
CLIENT_SHA256 = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"
ARCHIVE_SHA256 = "42611495f81734528e8d9f3b4286ed2f8531ad0d75be087a1fb8ef39f9c32367"
ENTRY_NAMES = (
    "InterceptSpecialTable.mpk", "InterceptAnomalousTable.mpk",
    "WaveDataTable.wave_Intercept_001.mpk", "MonsterTable.mpk",
    "MonsterModelTable.mpk",
)
# Product selector identity, current Group 1 row IDs and exact current wave IDs.
# Group 2 legacy rows deliberately cannot match these identities.
SELECTOR = (
    ("special-alteisen", "special", 1, 6302001),
    ("special-gravedigger", "special", 2, 6302002),
    ("special-blacksmith", "special", 3, 6302003),
    ("special-chatterbox", "special", 4, 6302004),
    ("special-modernia", "special", 5, 6302005),
    ("anomaly-mirror-container", "anomaly", 1, 6302006),
    ("anomaly-indivilia", "anomaly", 2, 6302007),
    ("anomaly-ultra", "anomaly", 3, 6302008),
    ("anomaly-kraken", "anomaly", 4, 6302009),
    ("anomaly-harvester", "anomaly", 5, 6302010),
)
ENCOUNTER_FIELDS = frozenset(("managementType", "processType", "timeLimit",
    "waveId", "monsterStageLv", "dynamicObjectLv", "raidLvChangeGroup",
    "isAuto", "tddProcess"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique(rows: list[dict], **keys: object) -> dict:
    found = [row for row in rows if all(row.get(key) == value for key, value in keys.items())]
    if len(found) != 1:
        raise ValueError(f"Expected one source row for {keys}, got {len(found)}")
    return found[0]


def _enums() -> dict:
    wanted = {
        "NK.Spot.Common.CommonEnum.ManagementType": ("SinglePlay", 0),
        "NK.StaticData.SpotModType": ("Intercept", 7),
    }
    found = {}
    with TYPE_FACTS.open(encoding="utf-8") as source:
        for line in source:
            if not any('"class": "' + name + '"' in line for name in wanted):
                continue
            row = json.loads(line)
            name = row["class"]
            if name in found or row.get("enum_status") != "read" or not row.get("is_enum"):
                raise ValueError(f"Invalid installed enum evidence: {name}")
            literal, value = wanted[name]
            matches = [x for x in row["enum_literals"] if x["name"] == literal]
            if len(matches) != 1 or matches[0].get("status") != "read" or matches[0]["value"] != value:
                raise ValueError(f"Installed enum value mismatch: {name}.{literal}")
            found[name] = {"assembly": row["assembly"], "class": name,
                "literal": literal, "value": value, "classId": row["class_id"]}
    if set(found) != set(wanted):
        raise ValueError("Missing installed management/process enum evidence")
    return found


def _decode() -> dict[str, list[dict]]:
    with tempfile.TemporaryDirectory(prefix="native-encounters-") as directory:
        result = subprocess.run([str(READER), str(ARCHIVE), directory],
            capture_output=True, text=True, timeout=45, check=False)
        if result.returncode:
            raise ValueError(f"MemoryPack decoder failed: {result.stderr[-800:]}")
        output = Path(directory)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("errors"):
            # Other unrelated schemas may be unavailable. Selected tables must
            # still decode; retain errors only if they concern these inputs.
            errors = [x for x in manifest["errors"] if any(n in x for n in ENTRY_NAMES)]
            if errors:
                raise ValueError(f"Selected MemoryPack decode errors: {errors}")
        names = {
            "special": "InterceptSpecialTable.mpk.json",
            "anomaly": "InterceptAnomalousTable.mpk.json",
            "waves": "InterceptWaves.json",
            "monsters": "MonsterTable.mpk.json",
            "models": "MonsterModelTable.mpk.json",
        }
        return {key: json.loads((output / name).read_text(encoding="utf-8"))
                for key, name in names.items()}


def build_registry() -> dict:
    if _file_sha(CLIENT) != CLIENT_SHA256 or _file_sha(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError("Installed client or current table archive bytes changed")
    with zipfile.ZipFile(ARCHIVE) as archive:
        entries = {}
        for name in ENTRY_NAMES:
            matching = [item for item in archive.infolist() if item.filename == name]
            if len(matching) != 1:
                raise ValueError(f"Missing or duplicate archive entry: {name}")
            entries[name] = _sha(archive.read(name))
    enums = _enums()
    tables = _decode()
    profiles = []
    for product_id, mode, row_id, wave_id in SELECTOR:
        row = _unique(tables[mode], Group=1, Id=row_id)
        if row.get("SpotType") != "WaveData" or row.get("SpotId") != wave_id:
            raise ValueError(f"Selector/table mismatch for {product_id}")
        wave = _unique(tables["waves"], StageId=wave_id)
        if wave.get("SpotMod") != "Intercept" or wave.get("GroupId") != "wave_Intercept_001":
            raise ValueError(f"Non-Intercept wave for {product_id}")
        if type(wave.get("BattleTime")) is not int or wave["BattleTime"] <= 0:
            raise ValueError(f"Invalid battle time for {product_id}")
        target_ids = wave.get("TargetList")
        if not isinstance(target_ids, list) or not target_ids or any(type(x) is not int for x in target_ids):
            raise ValueError(f"Missing target monster for {product_id}")
        targets = []
        for monster_id in target_ids:
            monster = _unique(tables["monsters"], Id=monster_id)
            model = _unique(tables["models"], Id=monster["MonsterModelId"])
            if not model.get("MonPrefab"):
                raise ValueError(f"Missing model prefab for {product_id}/{monster_id}")
            targets.append({"monsterId": monster_id, "modelId": model["Id"],
                "monsterPrefab": model["MonPrefab"], "resourceId": model["ResourceId"],
                "spotAi": monster["SpotAi"], "monsterRowSha256": _sha(_canonical(monster)),
                "modelRowSha256": _sha(_canonical(model))})
        encounter = {"managementType": 0, "processType": 7,
            "timeLimit": wave["BattleTime"], "waveId": wave_id,
            "monsterStageLv": row["MonsterStageLv"],
            "dynamicObjectLv": row["DynamicObjectStageLv"],
            "raidLvChangeGroup": row["MonsterStageLvChangeGroup"],
            "isAuto": True, "tddProcess": False}
        wave_paths = [part["WavePath"] for part in wave["WaveData"] if part.get("WavePath")]
        profiles.append({"productId": product_id, "mode": mode, "tableEntry":
            "InterceptSpecialTable.mpk" if mode == "special" else "InterceptAnomalousTable.mpk",
            "tableKey": {"Group": 1, "Id": row_id}, "tableRowSha256": _sha(_canonical(row)),
            "sourceTableRow": row, "encounter": encounter,
            "encounterProvenance": {"managementType": "installed enum SinglePlay",
                "processType": "installed enum Intercept", "isAuto": "current diagnostic fixture policy",
                "tddProcess": "current diagnostic fixture policy",
                "timeLimit": "WaveDataTable.BattleTime", "waveId": "Intercept table SpotId",
                "monsterStageLv": "Intercept table MonsterStageLv",
                "dynamicObjectLv": "Intercept table DynamicObjectStageLv",
                "raidLvChangeGroup": "Intercept table MonsterStageLvChangeGroup"},
            "wave": {"stageId": wave_id, "groupId": wave["GroupId"],
                "backgroundKey": wave["BackgroundName"], "battleTimeSeconds": wave["BattleTime"],
                "wavePaths": wave_paths, "targetMonsterIds": target_ids,
                "sourceRowSha256": _sha(_canonical(wave))}, "targets": targets,
            "unimplementedNativeInputs": {key: row[key] for key in
                ("CoverStageLv", "AutoChargeId", "DummySpotId", "SpotType", "TicketCount")
                if key in row},
            "status": "table_identity_only_no_native_battle_validation"})
    return {"schemaVersion": 1, "scope": "current_intercept_special_and_anomaly_only",
        "installedClientSha256": CLIENT_SHA256,
        "source": {"clientPath": str(CLIENT.relative_to(ROOT)).replace("\\", "/"),
            "tableArchivePath": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "tableArchiveSha256": ARCHIVE_SHA256, "archiveEntriesSha256": entries,
            "typeFactsPath": str(TYPE_FACTS.relative_to(ROOT)).replace("\\", "/"),
            "typeFactsSha256": _file_sha(TYPE_FACTS),
            "decoderSourceSha256": _file_sha(READER_SOURCE),
            "decoderBinarySha256": _file_sha(READER)},
        "nativeEnums": enums, "profiles": profiles,
        "limits": ["Only ten current Group 1 Intercept selector rows are registered.",
            "RandomSeed remains caller-supplied and is range-checked; other encounter fields require exact profile match.",
            "CoverStageLv, AutoChargeId and other source table fields are recorded but not yet mapped into the native fixture.",
            "Table identity does not establish resource closure, successful battle initialization, tactical coverage or numerical accuracy."]}


def load_registry(path: Path = REGISTRY) -> dict:
    """Fail closed by comparing the complete file with freshly decoded source."""
    supplied = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = build_registry()
    if supplied != expected or _canonical(supplied) != _canonical(expected):
        raise ValueError("Encounter registry schema/content differs from bound source bytes")
    return supplied


def match_profile(registry: dict, product_id: str, encounter: dict) -> dict:
    """Match one known selector profile; no arbitrary transport field fallback."""
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(SELECTOR):
        raise ValueError("Unverified encounter registry")
    found = [p for p in profiles if p.get("productId") == product_id]
    if len(found) != 1:
        raise ValueError(f"Unsupported current Intercept profile: {product_id}")
    required = found[0]["encounter"]
    if not isinstance(encounter, dict) or set(encounter) != ENCOUNTER_FIELDS | {"randomSeed"}:
        raise ValueError("Encounter requires exact native transport fields and randomSeed")
    for key, value in required.items():
        if type(encounter[key]) is not type(value) or encounter[key] != value:
            raise ValueError(f"Encounter {key} differs from source-bound {product_id}")
    seed = encounter["randomSeed"]
    if type(seed) is not int or not 1 <= seed <= 2**31 - 1:
        raise ValueError("randomSeed must be a positive signed 32-bit integer")
    return found[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "verify"))
    parser.add_argument("--output", type=Path, default=REGISTRY)
    args = parser.parse_args()
    if args.action == "generate":
        registry = build_registry()
        args.output.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        registry = load_registry(args.output)
    print(json.dumps({"action": args.action, "profiles": len(registry["profiles"]),
        "registrySha256": _file_sha(args.output)}))


if __name__ == "__main__":
    main()

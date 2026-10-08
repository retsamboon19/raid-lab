"""Strict diagnostic input for the installed original-engine five-unit fixture.

This is not a user-build converter. It rejects investment data that cannot yet
be represented faithfully by the original SpotCharacterData construction path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

CLIENT_SHA256 = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"
NAME_CODES = frozenset((5065, 5011, 5105, 5004, 5099))
STAT_NAMES = frozenset(("HealthPoint", "Attack", "Defense", "EnergyResist",
    "MetalResist", "BioResist", "CriticalRatio", "CriticalDamage", "HPRatio"))
TABLE_CRIT = {"source": "installed_character_table"}
BARE_POLICY = {"equipment": [], "attractiveLevel": 0,
    "recycleResearch": [], "harmonyCube": None, "favoriteItem": None}
ENCOUNTER = {"managementType": 0, "processType": 7, "timeLimit": 180,
    "waveId": 6302009, "monsterStageLv": 250, "dynamicObjectLv": 250,
    "raidLvChangeGroup": 209, "isAuto": True, "tddProcess": False}


@lru_cache(maxsize=1)
def current_encounter_registry() -> dict:
    # One immutable, freshly source-verified registry per staging/runner process.
    from mechanics_encounters import load_registry
    return load_registry()


def encounter_profile(request: dict) -> dict | None:
    if request.get("schemaVersion") != 2:
        return None
    from mechanics_encounters import match_profile
    return match_profile(current_encounter_registry(), request["encounterProfileId"],
                         request["encounter"])


def _keys(value: object, expected: set[str], path: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{path} requires exactly {sorted(expected)}")
    return value


def _integer(value: object, lo: int, hi: int, path: str) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{path} must be an integer in [{lo}, {hi}]")
    return value


def validate_request(value: object) -> dict:
    version = value.get("schemaVersion") if isinstance(value, dict) else None
    root = _keys(value, {"schemaVersion", "purpose", "installedClientSha256",
        "characters", "encounter"} | ({"encounterProfileId"} if version == 2 else set()), "request")
    if version not in (1, 2) or type(version) is not int:
        raise ValueError("Unsupported mechanics request schema version")
    purpose = root["purpose"]
    if purpose not in ("diagnostic_synthetic_input", "diagnostic_bare_character_build",
                       "diagnostic_bare_snapshot_build"):
        raise ValueError("Unsupported diagnostic input mode")
    if root["installedClientSha256"] != CLIENT_SHA256:
        raise ValueError("Request is not bound to the installed client")
    characters = root["characters"]
    if not isinstance(characters, list) or len(characters) != 5:
        raise ValueError("Request needs exactly five ordered characters")
    codes = []
    for slot, raw in enumerate(characters, 1):
        path = f"characters[{slot - 1}]"
        row = _keys(raw, {"nameCode", "level", "grade", "core",
            "skillLevels", "stats" if purpose == "diagnostic_synthetic_input"
            else "barePolicy"}, path)
        codes.append(_integer(row["nameCode"], 1, 999999, path + ".nameCode"))
        _integer(row["level"], 1, 1000, path + ".level")
        _integer(row["grade"], 0, 3, path + ".grade")
        _integer(row["core"], 0, 7, path + ".core")
        skills = _keys(row["skillLevels"], {"1", "2", "3"}, path + ".skillLevels")
        for key in ("1", "2", "3"):
            _integer(skills[key], 1, 10, path + ".skillLevels." + key)
        if purpose == "diagnostic_synthetic_input":
            stats = _keys(row["stats"], set(STAT_NAMES), path + ".stats")
            for key in STAT_NAMES:
                stat = stats[key]
                if key in ("CriticalRatio", "CriticalDamage") and stat == TABLE_CRIT:
                    continue
                # JSON numbers cross into Frida JavaScript; keep them exactly
                # representable there until an explicit int64-string schema exists.
                _integer(stat, 0, 2**53 - 1, path + ".stats." + key)
            if stats["HealthPoint"] == 0 or stats["HPRatio"] == 0:
                raise ValueError(path + " needs positive HealthPoint and HPRatio")
        else:
            if row["grade"] != 0 or row["core"] != 0:
                raise ValueError(path + " bare mode supports only installed grade/core 0/0")
            policy = _keys(row["barePolicy"], set(BARE_POLICY), path + ".barePolicy")
            for key, expected in BARE_POLICY.items():
                if type(policy[key]) is not type(expected) or policy[key] != expected:
                    raise ValueError(path + ".barePolicy." + key + " is not explicitly bare")
    if set(codes) != NAME_CODES:
        raise ValueError("Diagnostic bridge supports exactly the five staged character resources")
    encounter = _keys(root["encounter"], set(ENCOUNTER) | {"randomSeed"}, "encounter")
    if version == 2:
        if type(root["encounterProfileId"]) is not str:
            raise ValueError("encounterProfileId must name an exact registered encounter")
        profile = encounter_profile(root)
        source_levels = profile['sourceTableRow']
        if 'CharacterLv' in source_levels:
            if any(row['level'] != source_levels['CharacterLv'] for row in characters):
                raise ValueError('Diagnostic characters differ from the original fixed encounter level')
        elif any(row['level'] > source_levels['LimitCharacterLv'] for row in characters):
            raise ValueError('Diagnostic characters exceed the original encounter level cap')
    else:
        for key, expected in ENCOUNTER.items():
            if type(encounter[key]) is not type(expected) or encounter[key] != expected:
                raise ValueError(f"Unsupported diagnostic encounter.{key}")
    _integer(encounter["randomSeed"], 1, 2**31 - 1, "encounter.randomSeed")
    return root


def request_sha256(value: dict) -> str:
    validate_request(value)
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_request(path: str | Path) -> tuple[dict, str]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_request(value), request_sha256(value)


def verify_request_events(request: dict, events: list[dict]) -> dict:
    """Check native preparation and terminal identities against one staged request.

    This verifies the handoff observed in a trial, not the accuracy of its
    mechanics or the provenance of values supplied by the diagnostic request.
    """
    errors: list[str] = []
    try:
        validate_request(request)
        digest = request_sha256(request)
    except (TypeError, ValueError) as exc:
        return {"passed": False, "errors": [f"invalid request: {exc}"]}
    if not isinstance(events, list) or any(not isinstance(row, dict) for row in events):
        return {"passed": False, "errors": ["events must be a list of objects"],
                "requestSha256": digest}

    def matching(status: str) -> list[dict]:
        return [row for row in events if row.get("status") == status]

    for index, row in enumerate(events):
        if "requestSha256" in row and row["requestSha256"] != digest:
            errors.append(f"events[{index}].requestSha256 differs from staged request")

    prepared = matching("original_character_data_prepared")
    snapshot_mode = request["purpose"] == "diagnostic_bare_snapshot_build"
    bare_mode = request["purpose"] in ("diagnostic_bare_character_build",
                                       "diagnostic_bare_snapshot_build")
    calculated = matching("original_bare_character_stats_calculated") if bare_mode else []
    applied = matching("original_bare_stats_applied") if bare_mode else []
    snapshots = matching("original_bare_snapshot_applied") if snapshot_mode else []
    transporter_status = "original_encounter_transporter_prepared" if request["schemaVersion"] == 2 else "synthetic_kraken_transporter_prepared"
    transporter = matching(transporter_status)
    rng = matching("original_rng_initialized")
    terminal = matching("original_terminal_result")
    for status, rows, required in (
        ("original_character_data_prepared", prepared, 5),
        (transporter_status, transporter, 1),
        ("original_rng_initialized", rng, 1),
        ("original_terminal_result", terminal, 1),
    ):
        if len(rows) != required:
            errors.append(f"{status}: expected {required} rows, got {len(rows)}")
    if bare_mode:
        for status, rows in (("original_bare_character_stats_calculated", calculated),
                             ("original_bare_stats_applied", applied)):
            if len(rows) != 5:
                errors.append(f"{status}: expected 5 rows, got {len(rows)}")
    if snapshot_mode and len(snapshots) != 5:
        errors.append(f"original_bare_snapshot_applied: expected 5 rows, got {len(snapshots)}")

    slots: dict[int, dict] = {}
    resolved_critical: dict[str, dict[str, int]] = {}
    for row in prepared:
        slot = row.get("slot")
        if type(slot) is not int or not 1 <= slot <= 5:
            errors.append(f"prepared character has invalid slot {slot!r}")
            continue
        if slot in slots:
            errors.append(f"prepared character duplicates slot {slot}")
            continue
        slots[slot] = row
        path = f"prepared slot {slot}"
        expected = request["characters"][slot - 1]
        if row.get("requestSha256") != digest:
            errors.append(f"{path} lacks the staged request hash")
        for key in ("nameCode", "level", "grade", "core"):
            if type(row.get(key)) is not int or row[key] != expected[key]:
                errors.append(f"{path}.{key} differs from request")
        for key in ("tableId", "resourceId"):
            if type(row.get(key)) is not int or row[key] <= 0:
                errors.append(f"{path}.{key} is not a resolved installed resource")
        sources = row.get("skillSources")
        skill_fields = ("Skill1Data", "Skill2Data", "SkillBurstData")
        if not isinstance(sources, list) or len(sources) != 3:
            errors.append(f"{path}.skillSources must contain three original lookups")
        else:
            for key, field, source in zip(("1", "2", "3"), skill_fields, sources):
                if not isinstance(source, dict) or source.get("field") != field:
                    errors.append(f"{path}.skillSources[{key}] has wrong field")
                    continue
                if type(source.get("level")) is not int or source["level"] != expected["skillLevels"][key]:
                    errors.append(f"{path}.skillSources[{key}] has wrong level")
                for lookup_key in ("group", "tableType"):
                    if type(source.get(lookup_key)) is not int or source[lookup_key] <= 0:
                        errors.append(f"{path}.skillSources[{key}].{lookup_key} is unresolved")
        stats = row.get("stats")
        if not isinstance(stats, dict) or set(stats) != STAT_NAMES:
            errors.append(f"{path}.stats lacks the nine original readbacks")
            continue
        resolved_critical[str(slot)] = {}
        for key in sorted(STAT_NAMES):
            actual = stats[key]
            if bare_mode:
                if key in ("CriticalRatio", "CriticalDamage", "HPRatio"):
                    if type(actual) is not int or not 0 <= actual <= 2**53 - 1:
                        errors.append(f"{path}.stats.{key} is not an exact integer")
                    elif key == "HPRatio" and actual != 10000:
                        errors.append(f"{path}.stats.HPRatio differs from original converter constant")
                    elif key != "HPRatio":
                        resolved_critical[str(slot)][key] = actual
                elif type(actual) is not str or len(actual) > 20 or \
                        not re.fullmatch(r"-?(0|[1-9][0-9]*)", actual) \
                        or not -(2**63) <= int(actual) < 2**63:
                    errors.append(f"{path}.stats.{key} is not an exact int64 readback")
            else:
                requested = expected["stats"][key]
                if type(actual) is not int or not 0 <= actual <= 2**53 - 1:
                    errors.append(f"{path}.stats.{key} is not a finite exact integer")
                elif requested == TABLE_CRIT:
                    # The installed table is the stated source. No external value
                    # is asserted for it by this diagnostic request.
                    resolved_critical[str(slot)][key] = actual
                elif actual != requested:
                    errors.append(f"{path}.stats.{key} differs from request")
        if bare_mode and row.get("statSource") != "installed_original_bare_builder":
            errors.append(f"{path} lacks original bare-builder provenance")
        if bare_mode and row.get("barePolicy") != expected["barePolicy"]:
            errors.append(f"{path}.barePolicy differs from request")

    if bare_mode:
        def by_slot(rows: list[dict], label: str) -> dict[int, dict]:
            indexed: dict[int, dict] = {}
            for row in rows:
                slot = row.get("slot")
                if type(slot) is not int or not 1 <= slot <= 5 or slot in indexed:
                    errors.append(f"{label} has invalid or duplicate slot {slot!r}")
                else:
                    indexed[slot] = row
            return indexed

        calc_slots = by_slot(calculated, "calculated bare stats")
        applied_slots = by_slot(applied, "applied bare stats")
        for slot, expected in enumerate(request["characters"], 1):
            calc_row, applied_row, prepared_row = (calc_slots.get(slot),
                                                   applied_slots.get(slot), slots.get(slot))
            if calc_row is None or applied_row is None or prepared_row is None:
                errors.append(f"bare slot {slot} lacks calculated/applied/prepared evidence")
                continue
            for label, row in (("calculated", calc_row), ("applied", applied_row)):
                if row.get("requestSha256") != digest:
                    errors.append(f"bare slot {slot} {label} lacks request hash")
                if row.get("nameCode") != expected["nameCode"]:
                    errors.append(f"bare slot {slot} {label} nameCode differs from request")
                if row.get("barePolicy") != expected["barePolicy"]:
                    errors.append(f"bare slot {slot} {label} policy differs from request")
                if row.get("source") != "installed_original_stat_builder":
                    errors.append(f"bare slot {slot} {label} lacks original builder source")
                provenance = row.get("statProvenance")
                if not isinstance(provenance, dict) or set(provenance) != \
                        {"sixCalculated", "critical", "HPRatio"} or \
                        "CharacterStatHelper.Calc" not in provenance.get("sixCalculated", "") or \
                        "CharacterStaticInfo" not in provenance.get("critical", "") or \
                        "not invoked" not in provenance.get("HPRatio", ""):
                    errors.append(f"bare slot {slot} {label} has unsupported stat provenance")
                helper = row.get("originalHelper")
                if not isinstance(helper, dict) or helper.get("providerCount") != 7 or \
                        helper.get("calcFlags") != 0x86 or helper.get("constructorFlags") != 0x1886:
                    errors.append(f"bare slot {slot} {label} lacks original helper construction")
            readback = calc_row.get("readback")
            if not isinstance(readback, dict) or any(readback.get(key) != value for key, value in (
                    ("tableId", prepared_row.get("tableId")),
                    ("nameCode", expected["nameCode"]), ("grade", expected["grade"]),
                    ("core", expected["core"]), ("level", expected["level"]),
                    ("attractiveLevel", expected["barePolicy"]["attractiveLevel"]))):
                errors.append(f"bare slot {slot} original builder readback differs from prepared character")
            if calc_row.get("selectedTableId") != prepared_row.get("tableId"):
                errors.append(f"bare slot {slot} selected table ID differs from prepared character")
            for key in ("tableId", "level", "grade", "core"):
                wanted = prepared_row.get(key)
                if applied_row.get(key) != wanted:
                    errors.append(f"bare slot {slot} applied {key} differs from prepared character")
            if calc_row.get("stats") != applied_row.get("stats") or \
                    applied_row.get("stats") != prepared_row.get("stats"):
                errors.append(f"bare slot {slot} calculated/applied/prepared stats differ")

    if snapshot_mode:
        snapshot_slots = by_slot(snapshots, "applied bare snapshots")
        for slot, expected in enumerate(request["characters"], 1):
            row, prepared_row = snapshot_slots.get(slot), slots.get(slot)
            if row is None or prepared_row is None:
                errors.append(f"snapshot slot {slot} lacks applied/prepared evidence")
                continue
            if row.get("requestSha256") != digest or \
                    row.get("source") != "installed_original_CharacterSnapshot_conversion":
                errors.append(f"snapshot slot {slot} lacks original conversion provenance/hash")
            for key in ("nameCode", "level", "grade", "core"):
                if row.get(key) != expected[key]:
                    errors.append(f"snapshot slot {slot}.{key} differs from request")
            if row.get("tableId") != prepared_row.get("tableId") or \
                    row.get("barePolicy") != expected["barePolicy"]:
                errors.append(f"snapshot slot {slot} table/policy differs from prepared request")
            if row.get("stats") != prepared_row.get("stats") or \
                    row.get("skillSources") != prepared_row.get("skillSources"):
                errors.append(f"snapshot slot {slot} stats/skills differ from prepared character")
            native = row.get("nativeValues")
            if not isinstance(native, dict) or native.get("nameCode") != expected["nameCode"] or \
                    native.get("level") != expected["level"] or \
                    native.get("grade") != expected["grade"] or \
                    native.get("core") != expected["core"] or \
                    native.get("costumeTableId") != 0 or \
                    row.get("positionType") != slot or \
                    native.get("positionType") != row.get("positionType") or \
                    not isinstance(native.get("buffStaticInfos"), dict) or \
                    native["buffStaticInfos"].get("length") != 0:
                errors.append(f"snapshot slot {slot} native identity/position/buffs invalid")
                continue
            if row.get("emptyBuffCount") != 0 or \
                    native.get("stats") != {key: str(value) for key, value in
                                            prepared_row["stats"].items()}:
                errors.append(f"snapshot slot {slot} native status differs from prepared character")
            skills = native.get("skills")
            if not isinstance(skills, dict) or set(skills) != {"skill1", "skill2", "burst"}:
                errors.append(f"snapshot slot {slot} native skills missing")
            else:
                for summary_key, source in zip(("skill1", "skill2", "burst"),
                                               prepared_row["skillSources"]):
                    skill = skills[summary_key]
                    if not isinstance(skill, dict) or skill.get("groupId") != source["group"] or \
                            skill.get("level") != source["level"] or \
                            skill.get("tableType") != source["tableType"] or \
                            skill.get("disabled") is not False or \
                            skill.get("favoriteItem") is not False:
                        errors.append(f"snapshot slot {slot} native {summary_key} differs from original skills")
            for key in ("overrideElements", "addedPassiveList"):
                value = native.get(key)
                if not isinstance(value, dict) or type(value.get("count")) is not int or \
                        value["count"] < 0:
                    errors.append(f"snapshot slot {slot} native {key} summary invalid")
            if type(native.get("battlePower")) is not int or native["battlePower"] < 0:
                errors.append(f"snapshot slot {slot} native battlePower summary invalid")
            if prepared_row.get("characterSource") != \
                    "installed_original_CharacterSnapshot_conversion":
                errors.append(f"snapshot slot {slot} prepared source differs from conversion")

    if len(transporter) == 1:
        row = transporter[0]
        if request['schemaVersion'] == 2:
            from mechanics_encounters import REGISTRY
            if row.get('encounterProfileId') != request['encounterProfileId'] or \
                    row.get('encounterRegistrySha256') != hashlib.sha256(REGISTRY.read_bytes()).hexdigest():
                errors.append('transporter lacks the exact source-bound encounter registry identity')
        if row.get("requestSha256") != digest:
            errors.append("transporter lacks the staged request hash")
        if row.get("roster") != [c["nameCode"] for c in request["characters"]]:
            errors.append("transporter roster differs from requested slot order")
        for key, expected in request["encounter"].items():
            if type(row.get(key)) is not type(expected) or row[key] != expected:
                errors.append(f"transporter.{key} differs from request")
        if row.get("transporterValueTypeSize") != 360:
            errors.append("transporter original value type size is not 360")

    if len(rng) == 1:
        seed = request["encounter"]["randomSeed"]
        for key in ("managerSeed", "sharedSeed"):
            if type(rng[0].get(key)) is not int or rng[0][key] != seed:
                errors.append(f"original RNG {key} differs from request")

    if len(terminal) == 1:
        row = terminal[0]
        if row.get("completeBattle") is not True or row.get("resultCaptured") is not True \
                or row.get("originalResult") is not True or row.get("resultType") != "NK.BattleResult":
            errors.append("terminal row does not contain a completed original BattleResult")
        rounds = row.get("rounds")
        if not isinstance(rounds, list) or len(rounds) != 1 or not isinstance(rounds[0], dict):
            errors.append("terminal result must contain one original encounter round")
        else:
            characters = rounds[0].get("characters")
            if not isinstance(characters, list) or len(characters) != 5 or \
                    any(not isinstance(c, dict) for c in characters):
                errors.append("terminal result must contain five original character results")
            else:
                by_entity: dict[int, dict] = {}
                for character in characters:
                    entity_id = character.get("entityId")
                    if type(entity_id) is not int or entity_id in by_entity:
                        errors.append(f"terminal result has invalid or duplicate entity ID {entity_id!r}")
                    else:
                        by_entity[entity_id] = character
                if set(by_entity) != set(range(4096, 4101)):
                    errors.append("terminal entity IDs differ from the five requested slots")
                for slot, expected in enumerate(request["characters"], 1):
                    result = by_entity.get(4095 + slot)
                    if result is None:
                        continue
                    if type(result.get("nameCode")) is not int or result["nameCode"] != expected["nameCode"]:
                        errors.append(f"terminal slot {slot}.nameCode differs from request")
                    prepared_row = slots.get(slot)
                    if prepared_row is not None and result.get("tableId") != prepared_row.get("tableId"):
                        errors.append(f"terminal slot {slot}.tableId differs from original prepared character")

    return {"passed": not errors, "errors": errors, "requestSha256": digest,
            "preparedCharacterRows": len(prepared), "transporterRows": len(transporter),
            "rngRows": len(rng), "terminalRows": len(terminal),
            "bareCalculatedRows": len(calculated), "bareAppliedRows": len(applied),
            "bareSnapshotRows": len(snapshots),
            "resolvedTableCriticalStats": resolved_critical}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    request, digest = load_request(args.input)
    print(json.dumps({"requestSha256": digest, "purpose": request["purpose"],
        "nameCodes": [row["nameCode"] for row in request["characters"]],
        "waveId": request["encounter"]["waveId"],
        "randomSeed": request["encounter"]["randomSeed"]}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Map Raid Lab build inputs to exact original153 table identities.

Data only: this module never computes combat stats or damage. Unsupported values
are rejected rather than rounded, clamped or replaced by the captured squad.
"""
from __future__ import annotations
import hashlib
import importlib.util
import copy
import json
import math
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT_SHA256 = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"
TABLES = ROOT / "build-tables153.json"
COSTUMES = ROOT / "costume-tables153.json"
COSTUME_SOURCE = ROOT / "costume-tables153-source.json"
NONE = "없음"
PARTS = (("머리", "ModuleA", 1), ("몸통", "ModuleB", 2), ("팔", "ModuleC", 3), ("다리", "ModuleD", 4))
CORPS = {"None": 0, "ELYSION": 1, "MISSILIS": 2, "TETRA": 3, "PILGRIM": 4, "ALL": 5, "RANDOM": 6, "ABNORMAL": 7}
CORP_LABELS = {"엘리시온": "ELYSION", "미실리스": "MISSILIS", "테트라": "TETRA", "필그림": "PILGRIM", "어브노멀": "ABNORMAL", "어브노말": "ABNORMAL", "없음": "None"}
RESEARCH = {"Personal": 1, "Attacker": 2, "Defender": 3, "Supporter": 4, "ELYSION": 5, "MISSILIS": 6, "TETRA": 7, "PILGRIM": 8, "ABNORMAL": 9}
FUNCTION_OPTIONS = {"StatAtk": "atk_pct", "IncElementDmg": "element_bonus", "StatAmmoLoad": "max_ammo_pct", "StatCritical": "crit_rate", "StatCriticalDamage": "crit_dmg", "StatChargeTime": "charge_speed_pct", "StatChargeDamage": "charge_dmg_pct", "StatAccuracyCircle": "accuracy_pct", "StatDef": "def_pct"}
# Original Function.ValueType describes native stat application, not the unit
# used by Raid Lab's percentage editor. All nine original option values are
# indexed in hundredths of that displayed percentage, including these Integer
# functions. Pass the original effect identity to the engine without rescaling.
OPTION_VALUE_TYPES = {name: ("Integer" if name in {"StatCritical", "StatCriticalDamage", "StatChargeDamage"} else "Percent") for name in FUNCTION_OPTIONS}
BUILD_FIELDS = {"level", "breakthrough", "core_enhancement", "affinity", "skill_levels", "equipment", "equip_skills", "cube", "console", "collection_stage", "favorite_stage", "control"}


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def integer(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or int(value) != value or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}.")
    return int(value)


def one(rows, label):
    if len(rows) != 1:
        raise ValueError(f"{label} has no unique original153 table mapping.")
    return rows[0]


@lru_cache(maxsize=1)
def tables():
    return json.loads(TABLES.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def costume_tables():
    data = json.loads(COSTUMES.read_text(encoding="utf-8"))
    source = json.loads(COSTUME_SOURCE.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or data.get("clientSha256") != CLIENT_SHA256 or source.get("clientSha256") != CLIENT_SHA256 or source.get("tableOutputSha256") != hashlib.sha256(COSTUMES.read_bytes()).hexdigest():
        raise ValueError("Original153 costume table source binding differs.")
    return data["records"]


def provenance_digest(value):
    def browser_numbers(item):
        if type(item) is float and math.isfinite(item) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {key: browser_numbers(value) for key, value in item.items()}
        if isinstance(item, list):
            return [browser_numbers(value) for value in item]
        return item
    return hashlib.sha256(json.dumps(browser_numbers(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def costume_for_source(row, build, character):
    """Preserve an explicitly source-bound equipped costume; never infer one."""
    source = row.get("sourceCostumeProvenance")
    if source is None:
        return 0
    required = {"schemaVersion", "source", "nameCode", "characterTableId", "sourceCharacterSerialNumber", "costumeTableId", "sourceAccountSha256", "normalizedBuildSha256", "sourceContentSha256"}
    if not isinstance(source, dict) or set(source) != required or source.get("schemaVersion") != 1 or source.get("source") != "nikke-offline-equipped-character-v1":
        raise ValueError("Original equipped-costume provenance schema differs.")
    if source["nameCode"] != character["NameCode"] or source["characterTableId"] != character["Id"] or source["normalizedBuildSha256"] != provenance_digest(build):
        raise ValueError("Original equipped-costume provenance differs from the selected character or build.")
    if type(source["sourceCharacterSerialNumber"]) is not str or not source["sourceCharacterSerialNumber"].isdigit() or int(source["sourceCharacterSerialNumber"]) <= 0:
        raise ValueError("Original equipped-costume source character identity is absent.")
    account_hash = source["sourceAccountSha256"]
    if type(account_hash) is not str or len(account_hash) != 64 or any(c not in "0123456789abcdef" for c in account_hash):
        raise ValueError("Original equipped-costume account receipt is absent.")
    content = {key: value for key, value in source.items() if key != "sourceContentSha256"}
    if source["sourceContentSha256"] != provenance_digest(content):
        raise ValueError("Original equipped-costume provenance content differs.")
    costume_id = integer(source["costumeTableId"], 0, 2147483647, "Costume table identity")
    if costume_id:
        costume = one([r for r in costume_tables() if r["Id"] == costume_id], "Costume")
        if costume["ResourceId"] != character["ResourceId"] or type(costume["CostumeIndex"]) is not int or costume["CostumeIndex"] <= 0:
            raise ValueError("Original costume belongs to a different character resource.")
    return costume_id


def prebattle_match_for_source(source, characters):
    """Validate actual native output expectations; never stat-builder inputs."""
    if source is None:
        return None
    required = {"schemaVersion", "source", "actualCaptureSha256", "characters"}
    if not isinstance(source, dict) or set(source) != required or type(source.get("schemaVersion")) is not int or source["schemaVersion"] != 1 or source["source"] != "original153-actual-prebattle-native-readback":
        raise ValueError("Original prebattle match source schema differs.")
    digest = source["actualCaptureSha256"]
    if type(digest) is not str or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Original prebattle match capture receipt is absent.")
    rows = source["characters"]
    if not isinstance(rows, list) or len(rows) != 5:
        raise ValueError("Five original actual native prebattle expectations required.")
    values = {"Level", "Grade", "Core", "BattlePower", "CostumeTableId", "HarmonyCubeTableIdID"}
    stats = {"HealthPoint", "Attack", "Defense", "EnergyResist", "MetalResist", "BioResist", "CriticalRatio", "CriticalDamage", "HPRatio"}
    calculated = {"Hp", "Attack", "Defense", "EnergyResist", "MetalResist", "BioResist"}
    skill_fields = {"GroupId", "Level", "TableType", "Disable", "IsFavoriteItemSkill"}
    allowed = {"slot", "characterTableId", "nameCode", "nativeValues", "nativeStats", "nativeCalculatedStats", "nativeSkills", "addedPassiveRecordIds", "itemStateEffectTids"}
    def decimal(value):
        return type(value) is str and 0 < len(value) <= 19 and all(c in "0123456789" for c in value) and (len(value) == 1 or value[0] != "0") and int(value) <= 9223372036854775807
    for row, character in zip(rows, characters):
        if not isinstance(row, dict) or set(row) - allowed or not {"slot", "characterTableId", "nameCode", "nativeValues"}.issubset(row):
            raise ValueError("Original prebattle expectations contain unsupported or missing native fields.")
        for key, expected in (("slot", character["slot"]), ("characterTableId", character["characterTableId"]), ("nameCode", character["nameCode"])):
            if type(row[key]) is not int or row[key] != expected:
                raise ValueError("Original prebattle expected character identities/order differ.")
        native_values = row["nativeValues"]
        if not isinstance(native_values, dict) or "BattlePower" not in native_values or set(native_values) - values:
            raise ValueError("Original per-character native combat power expectation required.")
        for value in native_values.values():
            integer(value, 0, 2147483647, "Original expected native value")
        for key, fields in (("nativeStats", stats), ("nativeCalculatedStats", calculated)):
            if key in row and (not isinstance(row[key], dict) or not row[key] or set(row[key]) - fields or any(not decimal(v) for v in row[key].values())):
                raise ValueError("Original expected native stat readbacks must be exact nonnegative decimal strings.")
        if "nativeSkills" in row:
            skills = row["nativeSkills"]
            if not isinstance(skills, dict) or set(skills) != {"Skill1Data", "Skill2Data", "SkillBurstData"}:
                raise ValueError("Three original native skill expectations required.")
            for skill in skills.values():
                if not isinstance(skill, dict) or set(skill) != skill_fields or any(type(skill[k]) is not bool for k in ("Disable", "IsFavoriteItemSkill")):
                    raise ValueError("Original expected native skill schema differs.")
                for key in ("GroupId", "Level", "TableType"):
                    integer(skill[key], 0, 2147483647, "Original expected skill value")
        for key in ("addedPassiveRecordIds", "itemStateEffectTids"):
            if key in row:
                if not isinstance(row[key], list) or len(row[key]) > 256:
                    raise ValueError("Original expected passive identities exceed the source bound.")
                for tid in row[key]:
                    integer(tid, 1, 2147483647, "Original expected passive identity")
    return copy.deepcopy(source)


def percent_units(value, label):
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{label} must be a finite percentage.") from None
    units = number * 100
    if type(value) is bool or not units.is_finite() or units < 0 or units != units.to_integral_value():
        raise ValueError(f"{label} must be a nonnegative exact original percentage (at most two decimal places).")
    return int(units)


def options_for_build(build, maximum_lines, data):
    by_key = {}
    for row in data["overloadOptions"]:
        key = FUNCTION_OPTIONS.get(row["functionType"])
        if key:
            if row["valueType"] != OPTION_VALUE_TYPES[row["functionType"]]:
                raise ValueError(f"Original153 Overload value type changed for {row['functionType']}.")
            by_key.setdefault(key, {})[abs(row["value"])] = row["stateEffectTid"]
    output = []
    for key, raw in build["equip_skills"].items():
        if key not in by_key:
            if raw not in (0, [], None):
                raise ValueError(f"Overload option {key} has no original153 mapping.")
            continue
        values = by_key[key]
        if isinstance(raw, list):
            units = [percent_units(value, key) for value in raw]
            units = [value for value in units if value]
            if len(units) > maximum_lines or any(value not in values for value in units):
                raise ValueError(f"{key} contains a line unavailable in original153 or exceeds equipped Overload slots.")
        else:
            target = percent_units(raw, key)
            @lru_cache(maxsize=None)
            def find(remaining, count, minimum):
                if remaining == 0:
                    return ()
                if count == 0:
                    return None
                for value in sorted(values):
                    if value < minimum or value > remaining:
                        continue
                    tail = find(remaining - value, count - 1, value)
                    if tail is not None:
                        return (value,) + tail
                return None
            units = None
            for count in range(maximum_lines + 1):
                units = find(target, count, 0)
                if units is not None:
                    break
            if units is None:
                raise ValueError(f"{key} total {raw}% cannot be represented exactly by the equipped original153 Overload lines. Enter actual individual line values in advanced build JSON.")
        output.extend({"stateEffectTid": values[value]} for value in units)
    if len(output) > maximum_lines * 3:
        raise ValueError("Overload effects exceed three lines per equipped Overload item.")
    return output


def equipment_for_build(build, character, slot, request_hash, data, map_options=True):
    equipment = []
    if set(build["equipment"]) != {part for part, _, _ in PARTS}:
        raise ValueError("All four equipment slots must be supplied.")
    for part, subtype, subtype_id in PARTS:
        item = build["equipment"][part]
        if set(item) - {"tier", "level", "skills", "corp"}:
            raise ValueError(f"{part} has unsupported equipment fields.")
        if item.get("skills"):
            raise ValueError("Per-equipment skills must be supplied as equip_skills original Overload lines.")
        level = integer(item.get("level"), 0, 5, f"{part} equipment level")
        tier = item.get("tier")
        if tier == NONE:
            if level:
                raise ValueError(f"Empty {part} equipment must have level zero.")
            continue
        rare = "T10" if tier == "기업" else tier
        row = one([r for r in data["ItemEquip"] if r["Class"] == character["Class"] and r["ItemSubType"] == subtype and r["ItemRare"] == rare], f"{part} {tier}")
        grade = one([r for r in data["GradeCoreEquipment"] if r["Id"] == row["GradeCoreId"]], "Equipment grade")
        if level > grade["MaxLevel"]:
            raise ValueError(f"{part} level {level} exceeds the original153 {tier} maximum {grade['MaxLevel']}.")
        corp = item.get("corp", character["Corporation"] if rare == "T10" else "None")
        corp = CORP_LABELS.get(corp, corp)
        if corp not in CORPS:
            raise ValueError(f"{part} manufacturer has no original153 mapping.")
        equipment.append({"tableId": row["Id"], "level": level, "corporationType": CORPS[corp], "subType": subtype_id, "serialNumber": serial(request_hash, slot * 10 + subtype_id)})
    overload_count = sum(r["tableId"] in {x["Id"] for x in data["ItemEquip"] if x["ItemRare"] == "T10"} for r in equipment)
    return equipment, options_for_build(build, overload_count, data) if map_options else []


def serial(request_hash, suffix):
    return str(int(request_hash[:12], 16) * 1000 + suffix)


def preserve_bound_equipment_source(source, build, character, equipment, data):
    """Retain exact original equipment/effect TIDs from an unchanged account build."""
    def source_bytes(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    def browser_numbers(value):
        if type(value) is float and math.isfinite(value) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {key: browser_numbers(item) for key, item in value.items()}
        if isinstance(value, list):
            return [browser_numbers(item) for item in value]
        return value
    legacy_build = copy.deepcopy(build)
    legacy_build["equip_skills"] = {
        key: [float(item) for item in value] if isinstance(value, list) else float(value)
        for key, value in legacy_build["equip_skills"].items()}
    build_digests = {hashlib.sha256(source_bytes(browser_numbers(build))).hexdigest(),
                     hashlib.sha256(source_bytes(legacy_build)).hexdigest()}
    if not isinstance(source, dict) or source.get("schemaVersion") != 1 or source.get("nameCode") != character["NameCode"] or source.get("normalizedBuildSha256") not in build_digests:
        raise ValueError("Exact equipment provenance no longer matches the selected build. Save or reimport the build before running it.")
    content = {key: value for key, value in source.items() if key != "sourceContentSha256"}
    if source.get("sourceContentSha256") != hashlib.sha256(source_bytes(browser_numbers(content))).hexdigest():
        raise ValueError("Exact equipment provenance content hash differs.")
    actual_options = {r["stateEffectTid"]: r for r in data["overloadOptions"]}
    totals, binary_totals, individual, effects = {}, {}, {}, []
    if set(source.get("gearSlots", {})) != {part for part, _, _ in PARTS}:
        raise ValueError("Exact equipment provenance is missing original gear slots.")
    equipment_by_subtype = {row["subType"]: row for row in equipment}
    for part, subtype, subtype_id in PARTS:
        gear = source["gearSlots"][part]
        item = equipment_by_subtype.get(subtype_id)
        if item is None:
            if gear.get("itemTid") or any(gear.get("overloadLines", [])):
                raise ValueError("Exact equipment source conflicts with an empty selected equipment slot.")
            continue
        if any(gear.get(key) != item[target] for key, target in (("itemTid", "tableId"), ("level", "level"), ("corporationType", "corporationType"))):
            raise ValueError("Exact equipment source conflicts with the selected item, level or manufacturer.")
        lines = gear.get("overloadLines")
        if not isinstance(lines, list) or len(lines) != 3:
            raise ValueError("Exact equipment source needs three original line slots per item.")
        used = set()
        for line in lines:
            if line is None:
                continue
            option = actual_options.get(line.get("stateEffectId"))
            if option is None:
                raise ValueError("An imported Overload value has no original153 effect row; it cannot be substituted.")
            key = FUNCTION_OPTIONS[option["functionType"]]
            if key in used:
                raise ValueError("An original equipment item cannot repeat one Overload option type.")
            used.add(key)
            value = abs(option["value"])
            totals[key] = totals.get(key, 0) + value
            binary_totals[key] = binary_totals.get(key, 0) + value / 100
            individual.setdefault(key, []).append(value)
            effects.append({"stateEffectTid": option["stateEffectTid"]})
    for key, raw in build["equip_skills"].items():
        if isinstance(raw, list):
            expected = sorted(value for value in (percent_units(value, key) for value in raw) if value)
            if expected != sorted(individual.get(key, [])):
                raise ValueError("Selected individual Overload lines differ from original equipment provenance.")
        else:
            # Imported totals were accumulated from original individual decimal
            # lines in Python before crossing the browser JSON boundary. Accept
            # that exact same binary sum or the exact decimal total; no rounding
            # or tolerance is used to admit a different requested percentage.
            if type(raw) not in (int, float) or not math.isfinite(raw) or raw not in (totals.get(key, 0) / 100, binary_totals.get(key, 0)):
                raise ValueError("Selected Overload totals differ from original equipment provenance.")
    return effects


def validate_encounter(settings):
    path = ROOT.parent / 'encounters153/select_encounter153.py'
    spec = importlib.util.spec_from_file_location('_native_build_encounter_selection', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.select_encounter(settings)


def favorite_for_build(build, character, data):
    phase = integer(build["favorite_stage"], 0, 3, "Favorite item phase")
    collection = build["collection_stage"]
    if phase:
        if collection != "SR15":
            raise ValueError("Favorite item builds must retain their SR15 collection prerequisite.")
        row = one([r for r in data["FavoriteItem"] if r["NameCode"] == character["NameCode"] and r["FavoriteType"] == "Favorite"], "Favorite item")
        level_row = one([r for r in data["FavoriteItemLevel"] if r["LevelEnhanceId"] == row["LevelEnhanceId"] and r["Grade"] == phase], "Favorite item phase")
        return {"tableId": row["Id"], "level": level_row["Level"]}
    if collection == NONE:
        return None
    rare = "SR" if str(collection).startswith("SR") else "R" if str(collection).startswith("R") else None
    if rare is None:
        raise ValueError("Unknown collection rarity.")
    try:
        level = int(collection[len(rare):])
    except ValueError:
        raise ValueError("Unknown collection level.") from None
    row = one([r for r in data["FavoriteItem"] if r["FavoriteType"] == "Collection" and r["FavoriteRare"] == rare and r["WeaponType"] == character["WeaponType"]], "Collection item")
    one([r for r in data["FavoriteItemLevel"] if r["LevelEnhanceId"] == row["LevelEnhanceId"] and r["Level"] == level], "Collection item level")
    return {"tableId": row["Id"], "level": level}


def prepare_custom_request(payload):
    """Preserve selected slot order and map every supplied build field exactly."""
    if not isinstance(payload, dict) or set(payload) - {"engine", "members", "roster", "settings", "account_id", "prebattleMatch"}:
        raise ValueError("Unsupported native request fields; encounter or enemy overrides cannot be ignored.")
    if payload.get("engine", "original153") != "original153":
        raise ValueError("The selected battle engine must be original153.")
    data = tables()
    request_hash = hashlib.sha256(canonical(payload)).hexdigest()
    members = payload.get("members")
    if not isinstance(members, list) or len(members) != 5 or len(set(members)) != 5:
        raise ValueError("Choose five different catalogue units.")
    roster = payload.get("roster")
    if not isinstance(roster, list) or len({r["id"] for r in roster}) != len(roster):
        raise ValueError("Roster must contain unique unit entries.")
    settings = payload.get("settings", {})
    encounter = validate_encounter(settings)
    out = {"schemaVersion": 1, "clientSha256": CLIENT_SHA256, "inputSourceSha256": request_hash,
           "encounter": encounter, "characters": []}
    if "random_seed" in settings:
        seed = settings["random_seed"]
        if type(seed) is not int or not 1 <= seed <= 2147483647:
            raise ValueError("Original native random seed must be a positive Int32.")
        out["randomSeed"] = seed
    for slot, member in enumerate(members, 1):
        row = one([r for r in roster if r["id"] == member], f"Selected unit {member}")
        code = data["catalogIds"].get(member)
        if code is None:
            raise ValueError(f"Unit {member} has no exact original153 catalogue identity.")
        build = row.get("build")
        if not isinstance(build, dict) or set(build) != BUILD_FIELDS:
            raise ValueError(f"{member}: all native build fields must be explicit; unsupported build fields cannot be ignored.")
        if build["control"]:
            raise ValueError("Build control scripts are unsupported; choose original auto controls in encounter settings.")
        grade = integer(build["breakthrough"], 0, 3, "Limit breaks")
        core = integer(build["core_enhancement"], 0, 7, "Core enhancement")
        variants = [r for r in data["Character"] if r["NameCode"] == code and r["IsVisible"] is True]
        rare = one(list({r["OriginalRare"] for r in variants}), "Character rarity")
        growth = one([r for r in data["GradeCore"] if r["Rare"] == rare and r["Grade"] == grade and r["Core"] == core], "Limit break/core combination")
        character = one([r for r in variants if r["GradeCoreId"] == growth["Id"]], "Character growth")
        level = integer(build["level"], 1, 1000, "Unit level")
        own_level = level
        level_rule = encounter['unitLevel']
        if level_rule['mode'] == 'fixed':
            level = integer(level_rule['value'], 1, 1000, 'Original encounter unit level')
        elif level_rule['mode'] == 'cap':
            level = min(level, integer(level_rule['value'], 1, 1000, 'Original encounter level cap'))
        elif level_rule['mode'] != 'own':
            raise ValueError('Unknown original encounter unit level rule.')
        affinity = integer(build["affinity"], 1, 40, "Bond level")
        if affinity > growth["MaxAttractiveLevel"]:
            raise ValueError(f"{member}: bond {affinity} exceeds original153 limit {growth['MaxAttractiveLevel']} at the selected limit breaks.")
        skills = build["skill_levels"]
        if set(skills) != {"1", "2", "3"}:
            raise ValueError("Skill levels must have keys 1, 2 and 3.")
        equipment, overload = equipment_for_build(build, character, slot, request_hash, data,
            map_options="sourceProvenance" not in row)
        if "sourceProvenance" in row:
            overload = preserve_bound_equipment_source(row["sourceProvenance"], build, character, equipment, data)
        cube = build["cube"]
        if set(cube) != {"name", "level"}:
            raise ValueError("Cube fields must be name and level.")
        if cube["name"] == NONE:
            if cube["level"] != 0:
                raise ValueError("Unequipped cube must have level zero.")
            cube_input = None
        else:
            cube_row = one([r for r in data["ItemHarmonyCube"] if r["Id"] == data["cubeNames"].get(cube["name"])], "Cube")
            cube_level = integer(cube["level"], 1, 15, "Cube level")
            one([r for r in data["ItemHarmonyCubeLevel"] if r["LevelEnhanceId"] == cube_row["LevelEnhanceId"] and r["Level"] == cube_level], "Cube level")
            cube_input = {"tableId": cube_row["Id"], "level": cube_level, "subType": 18, "serialNumber": serial(request_hash, slot * 10 + 5)}
        research = []
        console = build["console"]
        if set(console) != {"common_level", "class_level", "company_level"}:
            raise ValueError("Research needs common, class and manufacturer levels.")
        for key, subtype in (("common_level", "Personal"), ("class_level", character["Class"]), ("company_level", character["Corporation"])):
            research_level = integer(console[key], 0, 1000, "Research level")
            if research_level:
                one([r for r in data["RecycleResearchLevel"] if r["RecycleSubType"] == subtype and r["RecycleLevel"] == research_level], "Research level")
                research.append({"subType": RESEARCH[subtype], "level": research_level})
        out["characters"].append({"slot": slot, "nameCode": code, "grade": grade, "core": core, "characterTableId": character["Id"], "serialNumber": serial(request_hash, slot), "level": level, "ownLevel": own_level, "affinity": affinity, "skillLevels": [integer(skills[str(k)], 1, 10, "Skill level") for k in (1, 2, 3)], "costumeTableId": costume_for_source(row, build, character), "equipment": equipment, "cube": cube_input, "favorite": favorite_for_build(build, character, data), "research": research, "overload": overload})
    match = prebattle_match_for_source(payload.get("prebattleMatch"), out["characters"])
    if match is not None:
        out["prebattleMatch"] = match
    return out

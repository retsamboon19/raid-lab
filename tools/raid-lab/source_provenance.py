"""Account gear source retained alongside, but never used as, calculator input."""

from __future__ import annotations

import copy
import hashlib
import json
import math

PARTS = (("head", "머리"), ("torso", "몸통"), ("arm", "팔"), ("leg", "다리"))
SOURCE = "BlaBlaLink Game/GetUserCharacterDetails"


def build_digest(build: dict) -> str:
    canonical = json.dumps(build, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _content_digest(source: dict) -> str:
    def browser_number_form(value):
        if type(value) is float and math.isfinite(value) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {key: browser_number_form(item) for key, item in value.items()}
        if isinstance(value, list):
            return [browser_number_form(item) for item in value]
        return value

    payload = {key: value for key, value in source.items()
               if key != "sourceContentSha256"}
    canonical = json.dumps(browser_number_form(payload), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"Account source {label} is not a nonnegative integer")
    return value


def _finite_number(value: object, label: str) -> int | float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"Account source {label} is not a finite number")
    return value


def from_account_detail(detail: dict, options: dict, effects: list[dict],
                        normalized_build: dict, name_code: int) -> dict:
    """Whitelisted equipment/line fields from one complete account detail.

    The source has item TIDs, but no equipment instance ID. Required fields
    must actually be present; neither a missing TID nor an ISN is inferred.
    """
    _nonnegative_int(name_code, "nameCode")
    effect_map = {str(effect["id"]): effect for effect in effects}
    slots = {}
    for api_part, part in PARTS:
        prefix = f"{api_part}_equip_"
        slot = {"itemTid": _nonnegative_int(detail[prefix + "tid"], prefix + "tid"),
                "tier": _nonnegative_int(detail[prefix + "tier"], prefix + "tier"),
                "level": _nonnegative_int(detail[prefix + "lv"], prefix + "lv"),
                "corporationType": _nonnegative_int(
                    detail[prefix + "corporation_type"], prefix + "corporation_type"),
                "overloadLines": []}
        for line in (1, 2, 3):
            effect_id = _nonnegative_int(detail[f"{prefix}option{line}_id"],
                                         f"{prefix}option{line}_id")
            if effect_id == 0:
                slot["overloadLines"].append(None)
                continue
            key = str(effect_id)
            if key not in options or key not in effect_map:
                raise ValueError(f"Account source option {effect_id} has no resolved effect")
            function_details = effect_map[key].get("function_details")
            if not isinstance(function_details, list) or len(function_details) != 1:
                raise ValueError(f"Account source option {effect_id} has unexpected functions")
            function = function_details[0]
            option_key, percent, reference_level = options[key]
            if type(option_key) is not str or not option_key:
                raise ValueError(f"Account source option {effect_id} has no option key")
            if type(function.get("function_type")) is not str or not function["function_type"] or \
                    type(function.get("function_value_type")) is not str or \
                    not function["function_value_type"]:
                raise ValueError(f"Account source option {effect_id} has invalid function types")
            if reference_level is not None:
                _nonnegative_int(reference_level, f"option {effect_id} reference level")
            slot["overloadLines"].append({
                "stateEffectId": effect_id,
                "functionId": _nonnegative_int(function["id"], f"option {effect_id} function id"),
                "functionType": function["function_type"],
                "functionValue": _finite_number(function["function_value"],
                                                 f"option {effect_id} function value"),
                "functionValueType": function["function_value_type"],
                "calculatorOption": option_key,
                "calculatorPercent": _finite_number(percent, f"option {effect_id} percent"),
                "referenceLevel": reference_level})
        slots[part] = slot
    source = {"schemaVersion": 1, "source": SOURCE, "nameCode": name_code,
              "normalizedBuildSha256": build_digest(normalized_build),
              "gearSlots": slots}
    source["sourceContentSha256"] = _content_digest(source)
    return source


def bound_source(source: object, normalized_build: dict,
                 expected_name_code: int) -> dict | None:
    """Retain a source only while its unit, build and payload all match."""
    if not isinstance(source, dict) or set(source) != {
            "schemaVersion", "source", "nameCode", "normalizedBuildSha256",
            "sourceContentSha256", "gearSlots"} or \
            type(source["schemaVersion"]) is not int or \
            source["schemaVersion"] != 1 or source["source"] != SOURCE or \
            type(source["nameCode"]) is not int or \
            source["nameCode"] != expected_name_code or \
            source["normalizedBuildSha256"] != build_digest(normalized_build):
        return None
    slots = source["gearSlots"]
    if not isinstance(slots, dict) or set(slots) != {part for _, part in PARTS}:
        return None
    for slot in slots.values():
        if not isinstance(slot, dict) or set(slot) != {
                "itemTid", "tier", "level", "corporationType", "overloadLines"}:
            return None
        if any(type(slot[key]) is not int or slot[key] < 0 for key in
               ("itemTid", "tier", "level", "corporationType")):
            return None
        lines = slot["overloadLines"]
        if not isinstance(lines, list) or len(lines) != 3:
            return None
        for line in lines:
            if line is None:
                continue
            if not isinstance(line, dict) or set(line) != {
                    "stateEffectId", "functionId", "functionType", "functionValue",
                    "functionValueType", "calculatorOption", "calculatorPercent",
                    "referenceLevel"}:
                return None
            if any(type(line[key]) is not int or line[key] < 0 for key in
                   ("stateEffectId", "functionId")) or \
                    line["stateEffectId"] == 0 or \
                    any(type(line[key]) is not str or not line[key] for key in
                        ("functionType", "functionValueType", "calculatorOption")) or \
                    any(type(line[key]) not in (int, float) or not math.isfinite(line[key])
                        for key in ("functionValue", "calculatorPercent")) or \
                    (line["referenceLevel"] is not None and
                     (type(line["referenceLevel"]) is not int or line["referenceLevel"] < 0)):
                return None
    if type(source["sourceContentSha256"]) is not str or \
            source["sourceContentSha256"] != _content_digest(source):
        return None
    return copy.deepcopy(source)

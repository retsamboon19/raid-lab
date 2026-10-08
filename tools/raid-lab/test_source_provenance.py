"""Exact account gear source survives roster export only for an unchanged build."""

import copy
import json
import sys
import unittest
from unittest.mock import patch

import core
import source_provenance


def account_detail(code):
    detail = {"name_code": code, "harmony_cube_tid": 0}
    for api_part, _ in source_provenance.PARTS:
        prefix = api_part + "_equip_"
        detail.update({prefix + "tid": 0, prefix + "tier": 0,
                       prefix + "lv": 0, prefix + "corporation_type": 0})
        for line in (1, 2, 3):
            detail[f"{prefix}option{line}_id"] = 0
    detail.update({"head_equip_tid": 3121001, "head_equip_tier": 10,
                   "head_equip_lv": 2, "head_equip_option1_id": 7000501})
    return detail


class SourceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.character = core.CODE_MAP["5065"]
        self.build = core.default_build()
        self.build["equipment"]["머리"].update(tier="기업", level=2)
        self.build["equip_skills"]["element_bonus"] = 9.54
        self.build = core.validate_build(self.build)
        self.effect = {"id": 7000501, "function_details": [{
            "id": 700050101, "function_type": "IncElementDmg",
            "function_value": 954, "function_value_type": "Percent"}]}
        self.option = {"7000501": ("element_bonus", 9.54, 1)}

    def test_account_import_roundtrip_keeps_slot_tid_and_original_line_id(self):
        detail = account_detail(5065)
        snapshot = {"format": "nikke-offline-blablalink-v1", "complete": True,
                    "missing_codes": [], "errors": [], "captured_at": "2026-10-08",
                    "roster": {"characters": [{"name_code": 5065, "lv": 400}]},
                    "details": [{"character_details": [detail],
                                 "state_effects": [self.effect]}], "outpost": {}}
        sys.path.insert(0, str(core.ENGINE / "scraper"))
        import profile_fetch as pf
        with patch.object(pf, "_load_equip_skill_table", return_value={}), \
             patch.object(pf, "_build_option_map", return_value=(self.option, {}, [])), \
             patch.object(pf, "_console", return_value={}), \
             patch.object(pf, "_load_cube_name_map", return_value={}), \
             patch.object(pf, "_to_profile", return_value=copy.deepcopy(self.build)):
            imported = core.import_roster(snapshot)
        saved = imported["roster"][0]
        source = saved["sourceProvenance"]
        self.assertEqual(source["normalizedBuildSha256"],
                         source_provenance.build_digest(saved["build"]))
        self.assertEqual(source["nameCode"], 5065)
        self.assertEqual(len(source["sourceContentSha256"]), 64)
        self.assertEqual(source["gearSlots"]["머리"]["itemTid"], 3121001)
        self.assertEqual(source["gearSlots"]["머리"]["overloadLines"][0], {
            "stateEffectId": 7000501, "functionId": 700050101,
            "functionType": "IncElementDmg", "functionValue": 954,
            "functionValueType": "Percent", "calculatorOption": "element_bonus",
            "calculatorPercent": 9.54, "referenceLevel": 1})
        self.assertEqual(source["gearSlots"]["머리"]["overloadLines"][1:],
                         [None, None])
        exported = json.loads(json.dumps({"roster": imported["roster"]}))
        restored = core.import_roster(exported)["roster"][0]
        self.assertEqual(restored["sourceProvenance"], source)
        self.assertEqual(restored["build"], saved["build"])

    def test_edited_build_discards_exact_source_without_changing_calculator_input(self):
        source = source_provenance.from_account_detail(
            account_detail(5065), self.option, [self.effect], self.build, 5065)
        row = {"id": self.character, "build": copy.deepcopy(self.build),
               "enabled": True, "assumptions": [], "sourceProvenance": source}
        edited = copy.deepcopy(row)
        edited["build"]["equipment"]["머리"]["level"] = 3
        imported = core.import_roster({"roster": [edited]})["roster"][0]
        self.assertNotIn("sourceProvenance", imported)
        self.assertEqual(imported["build"]["equipment"]["머리"]["level"], 3)
        self.assertIn("invalidated", " ".join(imported["assumptions"]))
        forged = copy.deepcopy(row)
        forged["sourceProvenance"]["gearSlots"]["머리"]["overloadLines"][0][
            "stateEffectId"] = "7000501"
        self.assertNotIn("sourceProvenance",
                         core.import_roster({"roster": [forged]})["roster"][0])

    def test_changed_unit_or_numeric_option_id_cannot_reuse_source(self):
        source = source_provenance.from_account_detail(
            account_detail(5065), self.option, [self.effect], self.build, 5065)
        row = {"id": self.character, "build": copy.deepcopy(self.build),
               "enabled": True, "assumptions": [], "sourceProvenance": source}
        wrong_unit = copy.deepcopy(row)
        wrong_unit["id"] = core.CODE_MAP["5011"]
        self.assertNotIn("sourceProvenance",
                         core.import_roster({"roster": [wrong_unit]})["roster"][0])
        wrong_line = copy.deepcopy(row)
        wrong_line["sourceProvenance"]["gearSlots"]["머리"]["overloadLines"][0][
            "stateEffectId"] = 7000502
        self.assertNotIn("sourceProvenance",
                         core.import_roster({"roster": [wrong_line]})["roster"][0])
        self.assertEqual(core.import_roster({"roster": [wrong_line]})["roster"][0][
            "build"], self.build)

    def test_browser_integral_float_normalization_keeps_source_but_changed_fraction_drops_it(self):
        build = copy.deepcopy(self.build)
        build["equip_skills"]["element_bonus"] = 100.0
        build = core.validate_build(build)
        effect = copy.deepcopy(self.effect)
        effect["function_details"][0]["function_value"] = 100.0
        source = source_provenance.from_account_detail(
            account_detail(5065), {"7000501": ("element_bonus", 100.0, 1)},
            [effect], build, 5065)
        line = source["gearSlots"]["머리"]["overloadLines"][0]
        self.assertEqual((type(line["functionValue"]), type(line["calculatorPercent"])),
                         (float, float))
        browser_form = json.loads(json.dumps(source))
        browser_line = browser_form["gearSlots"]["머리"]["overloadLines"][0]
        # JSON.parse/JSON.stringify in the app emits integral JS Numbers as
        # 100, even when the source JSON token was 100.0.
        browser_line["functionValue"] = 100
        browser_line["calculatorPercent"] = 100
        row = {"id": self.character, "build": build, "enabled": True,
               "assumptions": [], "sourceProvenance": browser_form}
        retained = core.import_roster({"roster": [row]})["roster"][0]
        self.assertIn("sourceProvenance", retained)
        changed = copy.deepcopy(row)
        changed["sourceProvenance"]["gearSlots"]["머리"]["overloadLines"][0][
            "calculatorPercent"] = 100.25
        self.assertNotIn("sourceProvenance",
                         core.import_roster({"roster": [changed]})["roster"][0])

    def test_sparse_export_keeps_normalized_build_but_omits_exact_source(self):
        full_detail = account_detail(5065)
        full_detail.update({"attractive_lv": 1, "skill1_lv": 1,
                            "skill2_lv": 1, "ulti_skill_lv": 1,
                            "favorite_item_tid": 0})
        detail = copy.deepcopy(full_detail)
        detail.pop("head_equip_tid")
        detail.pop("head_equip_corporation_type")
        snapshot = {"format": "nikke-offline-blablalink-v1", "complete": True,
                    "missing_codes": [], "errors": [], "captured_at": "2026-10-08",
                    "roster": {"characters": [{"name_code": 5065, "lv": 400,
                                                "grade": 0, "core": 0}]},
                    "details": [{"character_details": [detail],
                                 "state_effects": [self.effect]}], "outpost": {}}
        import profile_fetch as pf
        # The preexisting parser uses tier/level and an optional corporation;
        # it never required a gear TID for the normalized calculator build.
        self.assertEqual(pf._equipment(detail)["머리"]["level"], 2)
        self.assertEqual(pf._equip_skills(detail, self.option)["element_bonus"], 9.54)
        with patch.object(pf, "_load_equip_skill_table", return_value={}), \
             patch.object(pf, "_build_option_map", return_value=(self.option, {}, [])), \
             patch.object(pf, "_console", return_value={}), \
             patch.object(pf, "_load_cube_name_map", return_value={}):
            saved = core.import_roster(snapshot)["roster"][0]
            snapshot["details"][0]["character_details"][0] = full_detail
            complete = core.import_roster(snapshot)["roster"][0]
        self.assertNotIn("sourceProvenance", saved)
        self.assertIn("sourceProvenance", complete)
        self.assertEqual(saved["build"], complete["build"])
        self.assertIn("Exact equipment source is incomplete", " ".join(saved["assumptions"]))


if __name__ == "__main__":
    unittest.main()

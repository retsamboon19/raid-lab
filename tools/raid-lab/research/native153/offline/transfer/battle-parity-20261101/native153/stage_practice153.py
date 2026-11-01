"""Freeze original current153 captured Fire/Short90s native candidate; no launch."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
GAME = SANDBOX / "NIKKE/NIKKE/game"
CORE = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
HOOK = ROOT / "NIKKE/NIKKE/game/NKAB/dist/hi_shiftup_dont_mind_me.js"
HOOK_SHA = "779557044a3c3a72feb503ed9561b068fb4bd4e58e2946bcf4156e2e505727e9"
GEOMETRY_SHA = "ff3d69914a3735a7bd9de5493e687af30b8ef4b9ad35845e7446c19533435449"
ADDITIONAL_SHA = "4ae06a243b0674752f5f68ba45a5f84d837efcea5ecffb9c32f8e9c4ba4747bd"
RESOURCE_SHA = "29c9687da1ab0f66ac6bc56f96590ed3bbab1cb9f54cc5ac747be5f13b793170"
FX_SOURCE_SHA = "76141c9385c5854d2e92e11458d94d6fe8cbcf50962a2c1a98f45ca6b2caf3e9"
TIMELINE_SOURCE_SHA = "55be446ab887db2ced8c470c9dbc94946a5b77bf1eb5681969baf89161f80b73"
GRAPHIC_SOURCE_SHA = "6642fcf5e8aebbde638ded07753884a84b17cdc063a3f5d4a1c1cecb4e9788ea"
CUTSCENE_SOURCE_SHA = "eae1d9b0bbccf92750e8ba80617346d0ec9f9024ad06e7c602a7b81fa4686936"
CUTSCENE_PREFAB_SHA = "dc6fa365ddfe842fff60bcbae913e83034571706276850c40a81a99f050f1580"
REFERENCE_SELECTOR_SHA = "fa94e7d270bf105b1c5ee13befd5dd26584e829c0e9ee5c174002e6528f9851d"
CONTINUITY_SOURCE_SHA = "cd7e8d802cd864fd3a82f7e7022d475dd8b19620c582fa1b42851f187dce810c"
LOCALE_BINDING_SHA = "7621643f35dce4a77c4b8b1b99f2f64cbacee29bcecf4ec697f27a6b03efe2d8"
LOCALE_FIXTURE_SHA = "c5de388f70c877553f7adeef916dca1a8778ae2808a58db3cdaf506b09e07688"
LOCALE_STAGER_TEST_SHA = "6fd381c24aa7b98a3d73dde33c174ba7c3ea21098d5e3a7163205ae45c2b0a2a"
OVERLAY_INTEGRATION4_SHA = "3e0d4d9710d2cd22bf3941323ef82ddb298d9610e0f5c3db32121589d4bf55f9"
OVERLAY_INTEGRATION5_SHA = "8a91162460156088884174b07e63e4910a25e99e0177a551da4df9a550d32e72"
OVERLAY_BUILDER4_SHA = "28312f4d5a19d4a3f1a39282cb68bbef0f01c1dcd0ea32bc4d7d3f308a87fe99"
OVERLAY_BUILDER5_SHA = "0451af9280941140ef584c417e4d98955f2160ae972fc23c91edc1aa7b118ae7"
CONTINUITY19_SOURCE_SHA = "f7b532ba3e9b5c9393aac244ccbf98eaf168da688a8bc1a391af6ccf2da44412"
OVERLAY_INTEGRATION6_SHA = "1dec8c991be9233d13ebd904adb884ae00fb1e9e5a05f00f0993351e49265cdc"
OVERLAY_BUILDER6_SHA = "96887efb0fa77ad63d028da90c8f0604fa4656eeef2945ab83712e5cf93f2d56"
CONTINUITY22_SOURCE_SHA = "a9d56a45fa89e8fb164baffc40e4e86f2dd30b970a586287cc9c9f48240705c7"
OVERLAY_INTEGRATION7_SHA = "fc2444650933248c3ae790b5d6eb551c2bcd5ecbc2a60a0865f6179712e06c3b"
OVERLAY_BUILDER7_SHA = "5e3e80739f16923fa6e88c6e45c3f65f4676e627135887ece11cb07ba49cc700"
OVERLAY19_SOURCE_SHA = "e013e7f207f6f6355d2a68f38722b35f9a62049b69909cd18b58def3662d8b5b"
OVERLAY19_TEST_SHA = "99b3ecfe75de1fb2e4917625b6be6924d981fb758e1c43686163e81d0bd0f252"
LOCALE19_SOURCE_SHA = "6d26af5d439d4d1dce86e6e1a7242ae8ca46aea3746f61f576cc8a4bf0d4ab14"
LOCALE19_TEST_SHA = "653097ec9343fe538dedab3acaac954f90c367c055d999573a8ff0e6e0b4d208"
LOCALE18_PROOF_SHA = "803d44e83cfd73035635a51c720210d16afcedce629b5c185c08d157c97300ae"
SOURCE19_CORRECTION_SHA = "e655eca610c2ec9a2f2a875f8b97d66ed8d673009bbdf2bc3ce5f65d8c5cbcf5"
QUEUE19_PROOF_SHA = "ddb21f24cda4408b021c988ad687b299c7f887510fbbfd442ddffc7a3d3f5742"
LOCALE19_PROOF_SHA = "967e08d23f701589daa96ffb9478dbb3c0bf01122b29c3e750d6738925fda5c6"
REFERENCE_INPUT_KEYS = ("originalInput", "expectedReadbacks", "fixtureInput", "modeInput", "rngExpectedInput")


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_selected_reference_paths(paths, proof, reference_run):
    if proof.get("inputBindingReady") is not True or type(proof.get("referenceRunIndex")) is not int or proof["referenceRunIndex"] != reference_run:
        raise ValueError("Validated selected reference binding required")
    for key in REFERENCE_INPUT_KEYS:
        item = proof["files"][key]
        if paths[key].resolve() != Path(item["path"]).resolve() or sha(paths[key]) != item["sha256"]:
            raise ValueError("Selected reference path/artifact hash differs: " + key)
    fixture = json.loads(paths["fixtureInput"].read_text())
    mode = json.loads(paths["modeInput"].read_text())
    contract = proof["fixtureHashContract"]
    producer = hashlib.sha256((json.dumps(fixture, indent=2) + "\n").encode("utf-8")).hexdigest()
    representation = "artifact_bytes" if reference_run == 1 else "existing_producer_indent2_json_plus_LF_utf8"
    wanted = sha(paths["fixtureInput"]) if reference_run == 1 else producer
    if contract.get("modeHashRepresentation") != representation or contract.get("artifactSha256") != sha(paths["fixtureInput"]) or \
       contract.get("originalProducerLfSha256") != producer or contract.get("modeInputSourceSha256") != wanted or mode["inputSourceSha256"] != wanted:
        raise ValueError("Selected mode producer-LF/artifact hash contract differs")
    if fixture["runIndex"] != reference_run or json.loads(paths["rngExpectedInput"].read_text())["referenceRunIndex"] != reference_run:
        raise ValueError("Cross-run fixture/RNG selection rejected")


def prepare_reference_selection(candidate_index, reference_run):
    if type(candidate_index) is not int or not 1 <= candidate_index <= 22 or type(reference_run) is not int or reference_run not in (1, 2, 3):
        raise ValueError("Bounded candidate1..21 and original reference1..3 required")
    if candidate_index < 17:
        if reference_run != 1:
            raise ValueError("References2/3 require a new candidate17 or later")
        return None
    path = HERE / "matched_reference_selection153.py"
    if sha(path) != REFERENCE_SELECTOR_SHA:
        raise ValueError("Reviewed reference selector source differs")
    spec = importlib.util.spec_from_file_location("staged_reference_selection153", path)
    selector = importlib.util.module_from_spec(spec); spec.loader.exec_module(selector)
    paths, proof = selector.select_reference(reference_run)
    verify_selected_reference_paths(paths, proof, reference_run)
    encoded = (json.dumps(proof, indent=2) + "\n").encode("utf-8")
    return {"selector": selector, "paths": paths, "proof": proof, "bytes": encoded,
            "sha256": hashlib.sha256(encoded).hexdigest(), "referenceRunIndex": reference_run}


def admit_reference_input_changes(prior, paths, selection):
    """Only exact old/new selector-verified input keys may bypass JS review."""
    if selection is None:
        return set(), None
    verify_selected_reference_paths(paths, selection["proof"], selection["referenceRunIndex"])
    selector = selection["selector"]
    old_sources = prior["sources"]
    matches = [run for run in (1, 2, 3) if old_sources.get("fixtureInput", {}).get("sha256") == selector.HASHES[run][2]]
    if len(matches) != 1:
        raise ValueError("Historical input set is not an exact original reference")
    old_run = matches[0]
    if old_run == selection["referenceRunIndex"]:
        old_paths, old_proof = selection["paths"], selection["proof"]
    else:
        old_paths, old_proof = selector.select_reference(old_run)
    verify_selected_reference_paths(old_paths, old_proof, old_run)
    for key in REFERENCE_INPUT_KEYS:
        item = old_sources.get(key, {})
        if item.get("sha256") != old_proof["files"][key]["sha256"] or Path(item.get("path", "")).resolve() != old_paths[key].resolve():
            raise ValueError("Historical reference input key/path differs: " + key)
    recorded = prior.get("matchedReferenceSelection")
    if recorded is not None:
        item = old_sources.get("referenceSelectionProof", {})
        proof_path = Path(item.get("path", ""))
        if recorded.get("referenceRunIndex") != old_run or recorded.get("proofPath") != str(proof_path) or \
           recorded.get("proofSha256") != item.get("sha256") or sha(proof_path) != item.get("sha256") or \
           json.loads(proof_path.read_text()) != old_proof or recorded.get("proof") != old_proof:
            raise ValueError("Previous selected reference proof differs")
    elif "referenceSelectionProof" in old_sources:
        raise ValueError("Previous reference proof is missing its staging binding")
    changed_run = old_run != selection["referenceRunIndex"]
    allowed = set(REFERENCE_INPUT_KEYS) | {"referenceSelectionProof"} if changed_run else set()
    return allowed, {"fromReferenceRun": old_run, "toReferenceRun": selection["referenceRunIndex"],
                     "allowedChangedKeys": sorted(allowed), "bothInputSetsSelectorVerified": True}


def source_review_allowed(name, path, candidate_index):
    return path.suffix == ".js" or candidate_index >= 15 and name == "packetArchiverSource" and path.suffix == ".py" or \
        candidate_index >= 16 and name == "autoPreferencesContinuityWitnessSource" and path.suffix == ".py"


def prepared_overlay_proof_specs():
    return {
        "overlayIntegrationProof": (HERE / "practice-overlay-rng-integration4.json", OVERLAY_INTEGRATION4_SHA,
                                    HERE / "practice-overlay-rng-integration5.json", OVERLAY_INTEGRATION5_SHA),
        "overlayIntegrationBuilder": (HERE / "build_overlay_integration153.py", OVERLAY_BUILDER4_SHA,
                                      HERE / "build_overlay_integration153.py", OVERLAY_BUILDER5_SHA),
    }


def prepared_overlay_proof_target(name, path, digest, candidate_index):
    spec = prepared_overlay_proof_specs().get(name)
    return candidate_index >= 17 and spec is not None and path.resolve() == spec[2].resolve() and digest == spec[3]


def prepared_overlay_proof_transition(name, old_item, path, digest, reviewed, candidate_index):
    spec = prepared_overlay_proof_specs().get(name)
    return candidate_index == 17 and prepared_overlay_proof_target(name, path, digest, candidate_index) and \
        Path(old_item["path"]).resolve() == spec[0].resolve() and old_item["sha256"] == spec[1] and reviewed.get(name) == spec[3]


def prepared19_proof_specs():
    """Exact candidate18-to19 changes; old proof APIs remain historical."""
    return {
        "overlayIntegrationProof": (HERE / "practice-overlay-rng-integration5.json", OVERLAY_INTEGRATION5_SHA,
                                    HERE / "practice-overlay-rng-integration6.json", OVERLAY_INTEGRATION6_SHA),
        "overlayIntegrationBuilder": (HERE / "build_overlay_integration153.py", OVERLAY_BUILDER5_SHA,
                                      HERE / "build_practice19_integration153.py", OVERLAY_BUILDER6_SHA),
        "localeNativeSourceProof": (HERE / "practice-localization-source153.json", LOCALE18_PROOF_SHA,
                                    HERE / "practice-localization-source19.json", LOCALE19_PROOF_SHA),
        "overlayTestSource": (HERE / "test_practice_overlay_bootstrap.js", "cf2ad5d621f696cf925274c617c061cfc0ea97b80b7e9ed664a1f777c3dc2086",
                              HERE / "test_practice_overlay_bootstrap.js", OVERLAY19_TEST_SHA),
        "localeRuntimeTestSource": (HERE / "test_practice_localization.js", "6d22f4231c42e04ec229a4a8a9a0e2586a1a2dff8b7a95e90a1b546b0246dea3",
                                    HERE / "test_practice_localization.js", LOCALE19_TEST_SHA),
    }


def prepared22_proof_specs():
    """Exact archived21 integration6 to bounded22 integration7 transition."""
    return {
        "overlayIntegrationProof": (HERE / "practice-overlay-rng-integration6.json", OVERLAY_INTEGRATION6_SHA,
                                    HERE / "practice-overlay-rng-integration7.json", OVERLAY_INTEGRATION7_SHA),
        "overlayIntegrationBuilder": (HERE / "build_practice19_integration153.py", OVERLAY_BUILDER6_SHA,
                                      HERE / "build_practice22_integration153.py", OVERLAY_BUILDER7_SHA),
    }


def current_prepared_target(name, path, digest, candidate_index):
    if candidate_index < 19:
        return prepared_overlay_proof_target(name, path, digest, candidate_index)
    spec = (prepared22_proof_specs() if candidate_index >= 22 and name in prepared22_proof_specs()
            else prepared19_proof_specs()).get(name)
    return spec is not None and path.resolve() == spec[2].resolve() and digest == spec[3]


def current_prepared_transition(name, old_item, path, digest, reviewed, candidate_index):
    if candidate_index < 19:
        return prepared_overlay_proof_transition(name, old_item, path, digest, reviewed, candidate_index)
    if candidate_index >= 22 and name in prepared22_proof_specs():
        spec = prepared22_proof_specs()[name]
        return candidate_index == 22 and current_prepared_target(name, path, digest, candidate_index) and \
            Path(old_item["path"]).resolve() == spec[0].resolve() and old_item["sha256"] == spec[1] and reviewed.get(name) == spec[3]
    spec = prepared19_proof_specs().get(name)
    return candidate_index == 19 and current_prepared_target(name, path, digest, candidate_index) and \
        Path(old_item["path"]).resolve() == spec[0].resolve() and old_item["sha256"] == spec[1] and reviewed.get(name) == spec[3]


def verify_practice19_source_correction(paths):
    """Bind an additive factual correction, preserving both original receipts."""
    receipt = paths["source19ReportingCorrection"]
    if sha(receipt) != SOURCE19_CORRECTION_SHA:
        raise ValueError("Exact candidate19 source reporting correction required")
    correction = json.loads(receipt.read_text())
    for field, key, expected in (("targetSourceProof", "localeNativeSourceProof", LOCALE19_PROOF_SHA),
                                 ("queueRepairReceipt", "mainQueueBackpressureRepairProof", QUEUE19_PROOF_SHA)):
        item = correction[field]
        if Path(item["path"]).resolve() != paths[key].resolve() or item["sha256"] != expected or sha(paths[key]) != expected:
            raise ValueError("Reporting correction target receipt differs: " + field)
    if correction["correction"] != {
            "field": "probeDriverOverlaySchedulerEdited", "reportedValue": False, "correctedValue": True,
            "reason": "The combined candidate19 queue repair edits the overlay bootstrap host retry timer; the inherited false field in source19 is factually stale."} or \
       json.loads(paths["localeNativeSourceProof"].read_text())["probeDriverOverlaySchedulerEdited"] is not False:
        raise ValueError("Exact factual source19 field correction required")
    expected_edits = {"probe": False, "driver": False, "overlayBootstrap": True,
                      "frameScheduler": False, "localizationBootstrap": True}
    if correction["edited"] != expected_edits or set(correction["sourceComparisons"]) != set(expected_edits):
        raise ValueError("Exact candidate19 edited-component disclosure required")
    old = correction["native18Staging"]
    if sha(Path(old["path"])) != old["sha256"]:
        raise ValueError("Original18 reporting source differs")
    prior = json.loads(Path(old["path"]).read_text())["sources"]
    for label, row in correction["sourceComparisons"].items():
        key = row["sourceKey"]
        if paths[key].resolve() != Path(row["path"]).resolve() or sha(paths[key]) != row["currentSha256"] or \
           prior[key]["sha256"] != row["native18Sha256"] or Path(prior[key]["path"]).resolve() != paths[key].resolve() or \
           row["edited"] is not expected_edits[label] or (row["native18Sha256"] != row["currentSha256"]) != expected_edits[label]:
            raise ValueError("Original18/current reporting source comparison differs: " + label)
    if any(correction[key] is not False for key in ("originalProofRewritten", "integration6Rewritten", "runtimeChangedByCorrection", "nativeRunPerformed")):
        raise ValueError("Additive reporting-only correction required")
    return {"source19FactualCorrectionVerified": True, "correctedProbeDriverOverlaySchedulerEdited": True}


def locale19_dependency_transition(name, old_item, path, digest, paths, reviewed, candidate_index):
    if candidate_index != 19 or not name.startswith("localeNativeDependencyProof") or reviewed.get("localeNativeSourceProof") != LOCALE19_PROOF_SHA:
        return False
    old_path = HERE / "practice-localization-source153.json"
    if sha(old_path) != LOCALE18_PROOF_SHA or sha(paths["localeNativeSourceProof"]) != LOCALE19_PROOF_SHA:
        return False
    old = json.loads(old_path.read_text())["inputs"]
    new = json.loads(paths["localeNativeSourceProof"].read_text())["inputs"]
    if set(old) != set(new):
        return False
    for index, key in enumerate(sorted(old), 1):
        if name == "localeNativeDependencyProof" + str(index):
            expected = (ROOT / key).resolve()
            allowed = {HERE / "practice_localization.js": ("57c5f7fa59819ffcb2d2e18f4d85326ea81babcbb02d6efa13a251963094219e", LOCALE19_SOURCE_SHA),
                       HERE / "test_practice_localization.js": ("6d22f4231c42e04ec229a4a8a9a0e2586a1a2dff8b7a95e90a1b546b0246dea3", LOCALE19_TEST_SHA)}
            return expected in allowed and (old[key], new[key]) == allowed[expected] and \
                Path(old_item["path"]).resolve() == expected == path.resolve() and old_item["sha256"] == old[key] and digest == new[key]
    return False


def cutscene_evidence_path(name):
    # Source receipts use Windows relative paths. Accept either separator;
    # selecting the evidence root must not depend on their text spelling.
    relative = Path(name.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Relative mechanical intro source path required")
    base = HERE.parent if relative.parts[0] == "metadata" else HERE
    path = (base / relative).resolve()
    if not path.is_relative_to(HERE.parent.resolve()):
        raise ValueError("Mechanical intro source path escaped evidence root")
    return path


def verify_cutscene_builtin_copies(prefab, installed_game, sandbox_game):
    """Verify only actual native-consumed builtins of this original prefab closure."""
    installed_game, sandbox_game = Path(installed_game).resolve(), Path(sandbox_game).resolve()
    verified = []
    for name, item in sorted(prefab["verifiedBundles"].items()):
        if item["source"] != "installed_builtin":
            continue
        source = Path(item["path"]).resolve()
        if not source.is_relative_to(installed_game):
            raise ValueError("Cutscene original builtin escaped installed game: " + name)
        target = (sandbox_game / source.relative_to(installed_game)).resolve()
        if not target.is_relative_to(sandbox_game) or target == source:
            raise ValueError("Cutscene builtin target must be the private clone: " + name)
        if source.stat().st_size != item["bytes"] or sha(source) != item["sha256"] or \
           target.stat().st_size != item["bytes"] or sha(target) != item["sha256"]:
            raise ValueError("Original/private Cutscene builtin bytes differ: " + name)
        verified.append({"name": name, "source": str(source), "target": str(target),
                         "byteLength": item["bytes"], "sha256": item["sha256"]})
    if not verified:
        raise ValueError("Original Cutscene builtin closure must be explicit")
    return verified


def verify_overlay_bootstrap_copies(proof, installed_game, sandbox_game):
    """Read-only four exact Resources bootstrap files, before and after a run."""
    installed_game, sandbox_game = Path(installed_game).resolve(), Path(sandbox_game).resolve()
    required = {"nikke_Data/globalgamemanagers", "nikke_Data/globalgamemanagers.assets",
                "nikke_Data/resources.assets", "nikke_Data/sharedassets0.assets"}
    rows = proof["builtinCopies"]
    if len(rows) != 4 or {row["relative"].replace("\\", "/") for row in rows} != required:
        raise ValueError("Exact four original overlay bootstrap files required")
    checked = []
    for row in rows:
        relative = Path(row["relative"].replace("\\", "/"))
        source, target = Path(row["source"]).resolve(), Path(row["private"]).resolve()
        if source != (installed_game / relative).resolve() or target != (sandbox_game / relative).resolve() or source == target:
            raise ValueError("Original/private overlay bootstrap paths differ")
        if source.stat().st_size != row["byteLength"] or target.stat().st_size != row["byteLength"] or \
           sha(source) != row["sha256"] or sha(target) != row["sha256"]:
            raise ValueError("Original/private overlay bootstrap bytes differ")
        checked.append({"source": str(source), "target": str(target), "byteLength": row["byteLength"], "sha256": row["sha256"]})
    return checked


def overlay_source_path(name):
    relative = Path(name.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Relative original overlay source evidence required")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(HERE.parent.resolve()):
        raise ValueError("Original overlay source evidence escaped parity directory")
    return path


def original_overlay_source_paths(candidate_index=17):
    return {"overlaySource": HERE / "practice_overlay_bootstrap.js",
            "overlayInput": HERE / "practice-loading-overlay-binding.json",
            "overlayNativeSourceProof": HERE / "practice-loading-overlay-native-source.json",
            "overlayCardSourceProof": HERE / "practice-loading-overlay-card-source.json",
            "overlayBootstrapSourceProof": HERE / "practice-loading-overlay-bootstrap-source.json",
            "popupControlInput": HERE / "practice-popup-control-source.json",
            "overlayPrivateBuiltinsProof": HERE / "practice-loading-overlay-private-builtins1.json",
            "overlayBridgeApiProof": HERE / "practice-loading-overlay-bridge-api-source.json",
            "overlayLineConventionProof": HERE / "practice-loading-overlay-line-conventions.json",
            "overlayActualCapture": HERE.parent / "capture/preload-overlay-live6-36340/preload-overlay-events.jsonl",
            "overlayActualSceneLog": HERE.parent / "capture/preload-overlay-live6-36340/installed-player.log",
            "overlayActualSceneProof": HERE.parent / "results/diagnostic6-scene-entry-source.json",
            "overlayTestSource": HERE / "test_practice_overlay_bootstrap.js",
            "popupControlTestSource": HERE / "test_practice_popup_control.js",
            "startupPacingTestSource": HERE / "test_practice_startup_pacing.js",
            "overlayPreparationProof": HERE / "practice-overlay-preparation-tests1.json",
            "overlayPreparationFailureProof": HERE / "practice16-integration-preparation-failure1.json",
            "overlayBootstrapMetadata": HERE.parent / "metadata/current153-loading-overlay-api1/mechanics-metadata.json",
            "overlayIntegrationProof": HERE / ("practice-overlay-rng-integration7.json" if candidate_index >= 22 else "practice-overlay-rng-integration6.json" if candidate_index >= 19 else "practice-overlay-rng-integration5.json" if candidate_index >= 17 else "practice-overlay-rng-integration4.json"),
            "overlayIntegrationBuilder": HERE / ("build_practice22_integration153.py" if candidate_index >= 22 else "build_practice19_integration153.py" if candidate_index >= 19 else "build_overlay_integration153.py"),
            "overlayStagerTestSource": HERE / "test_stage_overlay_resources.py"}


def verify_original_overlay_inputs(paths, candidate_index=17):
    """Bind selected original APIs/assets/capture and actual private copies only."""
    fixed = {
        "overlaySource": OVERLAY19_SOURCE_SHA if candidate_index >= 19 else "e0d1986acdad8141609f0bbff2199d360f604396303bbe6f62402ba22b10c444" if candidate_index >= 17 else "1aac66e9b46fa93777923b0978d0faaadfaf82e14ba39a3620f225bf9747386d",
        "overlayInput": "7f1422ce5b23386901e61f4c37e825efc49d94a600887beb6f2f8c7d4f667357",
        "overlayNativeSourceProof": "3aa68c288fb97e8408e85fe952a0d9b95cf47fdaa32d74e09079d654fc52b4c9",
        "overlayCardSourceProof": "a21595810f5a21f338f9b7b2a41658a2e6829934bfa9eed779f73355d54fda10",
        "overlayBootstrapSourceProof": "ed3008acd1321c54822338df7d131369c9a37b142647bf99698cfe934142fccc",
        "popupControlInput": "b7abd4f46e21ef1f244746bebfa11300798380de9312f50e82a695007a14d469",
        "overlayPrivateBuiltinsProof": "dce96146b65edd380c48a3c2fb0a82f867ecd643c1b8e276d3bf75f14609e453",
        "overlayBridgeApiProof": "5d1b8803f4ab14ef0185b9ede6782b96038bab1c8e170ff0fb9a9ef5966a8025",
        "overlayLineConventionProof": "7b8e1452398d149a48ff593321447e991b6ab3bd4556bbd67acea725536bb90c",
        "overlayActualCapture": "25aa57f05e3da3a1a69a8b326d916c84067c47e5ff58fdc7a7fa5dae4d7bf4ff",
        "overlayActualSceneLog": "74787d0384feeb98aa69796ca25ba5f784aa9626542e27e0def2df283196f6bd",
        "overlayActualSceneProof": "a058867944368398d5270d0ea510aaad577bb2e9a9f9e124298798ca2a532628",
        "overlayTestSource": OVERLAY19_TEST_SHA if candidate_index >= 19 else "cf2ad5d621f696cf925274c617c061cfc0ea97b80b7e9ed664a1f777c3dc2086" if candidate_index >= 17 else "d378d7954edfd91b5b5d29898710b167168d0509e4956f1043b80cdbb93dbea0",
        "popupControlTestSource": "1c663a6026203cdfd2e2e20b98589220ea36ede218e7fc63ace1cff5213aaafe",
        "startupPacingTestSource": "ae39a0f80b669ee26968546e313037722cd8a2bca876a13dd40b6f7ba91a1473",
        "overlayPreparationProof": "b125db3c600144e9d1a9026616bebf0d771e9b4f4015379459892d5c2d8b8f4f",
        "overlayPreparationFailureProof": "54e8a17db9d4a1f80c86f0f55f2bd4e08d493cc52847d98fef6aec7a636d32d7",
        "overlayBootstrapMetadata": "ab834a97728d1b0c5fdd49fb8db2e167bf1a487a61dddd7305da3ca2dfe6d838",
        "overlayIntegrationProof": OVERLAY_INTEGRATION7_SHA if candidate_index >= 22 else OVERLAY_INTEGRATION6_SHA if candidate_index >= 19 else OVERLAY_INTEGRATION5_SHA if candidate_index >= 17 else OVERLAY_INTEGRATION4_SHA,
    }
    for name, digest in fixed.items():
        if sha(paths[name]) != digest:
            raise ValueError("Reviewed original overlay input differs: " + name)
    native = json.loads(paths["overlayNativeSourceProof"].read_text())
    if len(native["inputs"]) != 64:
        raise ValueError("Exact64 original overlay source inputs required")
    for index, (name, digest) in enumerate(sorted(native["inputs"].items()), 1):
        path = overlay_source_path(name)
        if sha(path) != digest:
            raise ValueError("Original overlay native source dependency differs: " + name)
        paths["overlayNativeDependencyProof" + str(index)] = path
    convention = json.loads(paths["overlayLineConventionProof"].read_text())
    line = paths["overlayActualCapture"].read_bytes().splitlines(keepends=True)[20]
    if convention["captureSha256"] != fixed["overlayActualCapture"] or \
       hashlib.sha256(line).hexdigest() != convention["rawLineIncludingCRLFSha256"] or \
       hashlib.sha256(line.decode("utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest() != convention["normalizedUtf8LFLineSha256"] or \
       hashlib.sha256(line.rstrip(b"\r\n")).hexdigest() != convention["lineWithoutTerminatorSha256"]:
        raise ValueError("Original selected transition line byte conventions differ")
    card = json.loads(paths["overlayCardSourceProof"].read_text())
    bootstrap = json.loads(paths["overlayBootstrapSourceProof"].read_text())
    if card["observedInput"]["rawLineSha256"] != convention["normalizedUtf8LFLineSha256"] or \
       native["actualCapture"]["anchors"][0]["rawLineSha256"] != convention["rawLineIncludingCRLFSha256"]:
        raise ValueError("Selected original transition proofs use mismatching line representations")
    card_copies = verify_cutscene_builtin_copies(card, ROOT / "NIKKE/NIKKE/game", GAME)
    if len(card_copies) != 14:
        raise ValueError("Exact14 original selected card builtins required")
    bootstrap_copies = verify_overlay_bootstrap_copies(bootstrap, ROOT / "NIKKE/NIKKE/game", GAME)
    for label, rows in (("overlayCardPrivateBuiltin", card_copies), ("overlayBootstrapPrivateBuiltin", bootstrap_copies)):
        for index, item in enumerate(rows, 1):
            paths[label + str(index)] = Path(item["target"])
    return {"originalOverlayPrivateBuiltinCopies": card_copies,
            "originalOverlayBootstrapCopies": bootstrap_copies,
            "exactNativeSourceDependencies": 64, "selectedCaptureLineConventionsVerified": True}


def original_overlay_runtime_values(paths):
    return {"PRACTICE_LOADING_OVERLAY_BINDING": json.loads(paths["overlayInput"].read_text()),
            "PRACTICE_POPUP_CONTROL_SOURCE": json.loads(paths["popupControlInput"].read_text()),
            "PRACTICE_POPUP_CONTROL_SOURCE_SHA256": "b7abd4f46e21ef1f244746bebfa11300798380de9312f50e82a695007a14d469"}


def original_overlay_module_order(module_names):
    if module_names.count("probeSource") != 1 or "overlaySource" in module_names:
        raise ValueError("Original overlay/probe module must each be composed once")
    return tuple(name for name in module_names if name != "probeSource") + ("overlaySource", "probeSource")


def original_locale_paths(candidate_index=19):
    return {"localeSource": HERE / "practice_localization.js", "localeInput": HERE / "practice-localization-binding.json",
            "localeNativeSourceProof": HERE / ("practice-localization-source19.json" if candidate_index >= 19 else "practice-localization-source153.json"),
            "localeRuntimeTestSource": HERE / "test_practice_localization.js",
            "localeStagerTestSource": HERE / "test_stage_localization153.py",
            "localeFixtureSourceProof": HERE / "practice-locale-local-source153.json",
            "localeFixtureHelper": HERE / "stage_local_locale153.py",
            "localeFixtureReceipt": SANDBOX / "local-locale153-fixture1.json"}


def verify_original_locale_inputs(paths, candidate_index=19):
    """Read-only pre/post byte/provenance gate; never copies or invokes native."""
    fixed = {"localeSource": LOCALE19_SOURCE_SHA if candidate_index >= 19 else "57c5f7fa59819ffcb2d2e18f4d85326ea81babcbb02d6efa13a251963094219e",
             "localeInput": LOCALE_BINDING_SHA,
             "localeNativeSourceProof": LOCALE19_PROOF_SHA if candidate_index >= 19 else LOCALE18_PROOF_SHA,
             "localeRuntimeTestSource": LOCALE19_TEST_SHA if candidate_index >= 19 else "6d22f4231c42e04ec229a4a8a9a0e2586a1a2dff8b7a95e90a1b546b0246dea3",
             "localeStagerTestSource": LOCALE_STAGER_TEST_SHA,
             "localeFixtureSourceProof": "aa94f6f319d74f7226dd070772e928141075d728decba92219afa84c691ce3e3",
             "localeFixtureHelper": "081ff464819a55710e1bdd1f6c2cabcba737491f021a3b648b32d3aef6c5e908",
             "localeFixtureReceipt": LOCALE_FIXTURE_SHA}
    for name, digest in fixed.items():
        if sha(paths[name]) != digest:
            raise ValueError("Reviewed original locale input differs: " + name)
    proof = json.loads(paths["localeNativeSourceProof"].read_text())
    if len(proof["inputs"]) != 26 or proof["fixtureEvidence"]["sha256"] != LOCALE_FIXTURE_SHA or proof["nativeRunPerformed"] is not False:
        raise ValueError("Exact original locale source/fixture proof required")
    for index, (name, digest) in enumerate(sorted(proof["inputs"].items()), 1):
        path = (ROOT / name).resolve()
        if not path.is_relative_to(HERE.parent.resolve()) or sha(path) != digest:
            raise ValueError("Original locale native source dependency differs: " + name)
        paths["localeNativeDependencyProof" + str(index)] = path
    spec = importlib.util.spec_from_file_location("staged_original_locale_fixture153", paths["localeFixtureHelper"])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    _, plan = helper.prepare()
    if len(plan) != 5 or any(row["existingIdenticalCopy"] is not True for row in plan):
        raise ValueError("All five original private locale fixture copies must already exist")
    binding = json.loads(paths["localeInput"].read_text())
    copies = []
    for index, row in enumerate(plan, 1):
        expected = [item for item in binding["requiredFiles"] if item["assetKey"] == row["assetKey"]]
        if len(expected) != 1 or expected[0]["sha256"] != row["sha256"] or expected[0]["bytes"] != row["bytes"]:
            raise ValueError("Original locale binding/fixture file differs")
        paths["localePrivateFile" + str(index)] = row["target"]
        copies.append({"assetKey": row["assetKey"], "path": str(row["target"]), "sha256": row["sha256"], "bytes": row["bytes"]})
    return {"originalLocaleFixtureFilesVerified": 5, "privateLocaleCopies": copies,
            "nativeRegistrationVerified": False, "nativeCallsPerformed": False, "filesCopiedByGuard": False}


def original_locale_runtime_values(paths):
    return {"PRACTICE_LOCALIZATION_BINDING": json.loads(paths["localeInput"].read_text()),
            "PRACTICE_LOCALIZATION_BINDING_SHA256": LOCALE_BINDING_SHA,
            "PRACTICE_LOCALIZATION_FIXTURE": json.loads(paths["localeFixtureReceipt"].read_text()),
            "PRACTICE_LOCALIZATION_FIXTURE_SHA256": LOCALE_FIXTURE_SHA}


def complete_locale_paths(candidate_index):
    if candidate_index < 20:
        return {}
    return {"completeLocaleSourceProof": HERE / "practice-locale-table-closure-source153.json",
            "completeLocaleFixtureHelper": HERE / "stage_locale_table_closure153.py",
            "completeLocaleFixtureReceipt": SANDBOX / "local-locale153-table-closure1.json",
            "completeLocaleStagerTestSource": HERE / "test_stage_complete_locale153.py"}


def validate_complete_locale_plan(proof, plan, receipt, private_root):
    """Verify the exact additive scope returned by the hash-pinned copy helper."""
    root = Path(private_root).resolve()
    if proof.get("localeTables") != 30 or proof.get("localeTableAndSignatureFiles") != 60 or \
       proof.get("unionFiles") != 63 or proof.get("catalogLocaleEntrySetComplete") is not True or \
       proof.get("baseFixture", {}).get("receiptSha256") != LOCALE_FIXTURE_SHA or \
       proof.get("baseFixture", {}).get("unchanged") is not True:
        raise ValueError("Complete locale proof must preserve base5 and exact30-table/60-file scope")
    if len(plan) != 63 or receipt.get("status") != "original153_complete_locale_table_closure_staged" or \
       receipt.get("unionFiles") != 63 or len(receipt.get("copies", [])) != 63 or \
       receipt.get("baseFixtureReceiptSha256") != LOCALE_FIXTURE_SHA or \
       receipt.get("installedFilesWritten") is not False or receipt.get("catalogsRewritten") is not False or \
       receipt.get("signatureBytesChanged") is not False:
        raise ValueError("Completed63-file original locale receipt required")
    expected = proof["assets"] + proof["unchangedBaseExtras"]
    if len(proof["assets"]) != 60 or len(expected) != 63:
        raise ValueError("Exact complete locale proof entries required")
    copies, seen = [], set()
    for index, (row, wanted, saved) in enumerate(zip(plan, expected, receipt["copies"]), 1):
        target = Path(row["target"]).resolve()
        relative = Path(wanted["privateRelativePath"].replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or not target.is_relative_to(root) or \
           target != (root / relative).resolve() or target != Path(wanted["privateTarget"]).resolve() or \
           str(target).casefold() in seen or row.get("existingIdenticalCopy") is not True:
            raise ValueError("Complete locale target missing, duplicated or outside canonical root")
        seen.add(str(target).casefold())
        if (row["assetKey"], row["sha256"], row["bytes"]) != (wanted["assetKey"], wanted["sha256"], wanted["bytes"]) or \
           (saved["target"], saved["sha256"], saved["bytes"]) != (str(target), row["sha256"], row["bytes"]):
            raise ValueError("Complete locale plan/proof/receipt bytes differ")
        copies.append({"assetKey": row["assetKey"], "path": str(target), "sha256": row["sha256"], "bytes": row["bytes"]})
    total = sum(row["bytes"] for row in copies)
    if total != proof["unionBytes"] or total != receipt["unionBytes"]:
        raise ValueError("Complete locale union byte count differs")
    return copies


def verify_complete_locale_inputs(paths, candidate_index):
    """Read-only pre/post guard; no copying, native calls, globals or old-path changes."""
    if candidate_index < 20:
        raise ValueError("Additive complete locale closure requires candidate20 or later")
    fixed = {"completeLocaleSourceProof": "9cef725daf5479187e7a61b469cbf04d62031d1a045497f0ce4caaa00f92479f",
             "completeLocaleFixtureHelper": "f32a2649417213d9c3f72110f4978dbb842ff4b8e264c467b101e99feb819af2",
             "completeLocaleFixtureReceipt": "1e71f36ad2d70c1146d560a773be691737818aece90348ae55665d6b0c0104e6"}
    for name, digest in fixed.items():
        if sha(paths[name]) != digest:
            raise ValueError("Reviewed complete locale closure input differs: " + name)
    spec = importlib.util.spec_from_file_location("staged_complete_locale_fixture153", paths["completeLocaleFixtureHelper"])
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    proof, plan, receipt = helper.verify_staged()
    copies = validate_complete_locale_plan(proof, plan, receipt, GAME / "nikke_Data/StreamingAssets/lss")
    for index, row in enumerate(copies, 1):
        paths["completeLocalePrivateFile" + str(index)] = Path(row["path"])
    for index, (name, digest) in enumerate(sorted(proof["dependencies"].items()), 1):
        path = Path(name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path) != digest:
            raise ValueError("Complete locale source dependency differs")
        paths["completeLocaleDependencyProof" + str(index)] = path
    return {"completeLocaleTablesVerified": 30, "completeLocaleTableAndSignatureFilesVerified": 60,
            "completeLocalePrivateFilesVerified": 63, "completeLocalePrivateBytes": sum(row["bytes"] for row in copies),
            "completeLocalePrivateCopies": copies, "baseFiveFileFixturePreserved": True,
            "filesCopiedByGuard": False, "nativeCallsPerformed": False,
            "nativeSignatureAcceptanceVerifiedForAddedTables": False}


def original_locale_module_order(module_names):
    if module_names.count("probeSource") != 1 or "localeSource" in module_names:
        raise ValueError("Original locale/probe module must each be composed once")
    return tuple(name for name in module_names if name != "probeSource") + ("localeSource", "probeSource")


def original_practice_dispatch(candidate_index):
    unchanged = "          globalThis.NATIVE153_ACTIVE_PRACTICE=runOriginalPracticeProbe(record,finish);"
    if candidate_index < 18:
        return unchanged
    return """          const localizationFailure=(phase,error)=>{
            try{if(error&&error.nativeFrames)record({phase:phase+"_native_frames",nativeFrames:error.nativeFrames});}catch(_){}
            try{fail(phase,error);}finally{finish();}
          };
          globalThis.NATIVE153_ACTIVE_LOCALIZATION=startOriginalPracticeLocalization(
            runtime,value=>{roots.push(value.ref(true));return value;},record,(error)=>{
              if(error){localizationFailure("original_localization_error",error);return;}
              if(finishing)return;
              try{globalThis.NATIVE153_ACTIVE_PRACTICE=runOriginalPracticeProbe(record,finish);}
              catch(error){localizationFailure("practice_dispatch_error",error);}
            });"""


def verify_resource_receipts(paths):
    chunks = {}
    def collect(data, group):
        if isinstance(data, dict):
            if all(k in data for k in ("store_offset", "compressed_bytes", "compressed_sha256")):
                key, size, digest = (group, data["store_offset"]), data["compressed_bytes"], data["compressed_sha256"]
                if key in chunks and chunks[key] != (size, digest):
                    raise ValueError("Conflicting exact staged chunk receipts")
                chunks[key] = (size, digest)
            for value in data.values():
                collect(value, group)
        elif isinstance(data, list):
            for value in data:
                collect(value, group)
    receipts = {name: json.loads(path.read_text()) for name, path in paths.items()}
    for receipt in receipts.values():
        group = receipt.get("resourceGroup", "core")
        if group not in ("core", "dp"):
            raise ValueError("Only exact current private core/DP resource groups supported")
        collect(receipt, group)
        if group == "dp" and "sourceSha256" in receipt:
            target = CORE.parent / "dp/chunk/store.cdb"
            actual = target.stat()
            expected = receipt["finalScratchStat"]
            if receipt["status"] != "passed" or receipt["sourceSha256"] != receipt["destinationReadbackSha256"] or \
               not receipt["sourceReadOnly"] or not receipt["sourceUnchanged"] or receipt["hardlinksUsed"] or \
               Path(receipt["scratchTarget"]).resolve() != target.resolve() or \
               actual.st_ino != expected["fileId"] or actual.st_size != expected["bytes"] or \
               actual.st_mtime_ns != expected["mtimeNs"] or actual.st_nlink != 1:
                raise ValueError("Complete original DP store receipt/file identity differs")
            for relative, item in receipt["currentCatalogBindings"].items():
                path = (CORE.parent / "dp" / relative).resolve()
                if not path.is_relative_to((CORE.parent / "dp").resolve()) or sha(path) != item["sha256"]:
                    raise ValueError("Exact private DP signed catalog/raw/index binding differs")
            if sha(CORE.parent / "dp/chunk/store.cdb.idx") != receipt["sourceIndexSha256"]:
                raise ValueError("Original DP chunk index differs")
            with target.open("rb") as stream:
                if hashlib.sha256(stream.read(256)).hexdigest() != receipt["originalHeaderSha256"]:
                    raise ValueError("Original DP store header differs")
        if receipt.get("atomicReplacement") == "Windows ReplaceFileW with sparse backup":
            full = receipt
            actual = (CORE / "chunk/store.cdb").stat()
            expected = full["finalScratchStat"]
            if full["status"] != "passed" or full["sourceSha256"] != full["destinationReadbackSha256"] or \
               not full["sourceReadOnly"] or not full["sourceUnchanged"] or full["hardlinksUsed"] or \
               Path(full["scratchTarget"]).resolve() != (CORE / "chunk/store.cdb").resolve() or \
               actual.st_ino != expected["fileId"] or actual.st_size != expected["bytes"] or \
               actual.st_mtime_ns != expected["mtimeNs"] or actual.st_nlink != 1:
                raise ValueError("Complete original-store receipt/file identity no longer matches")
    catalog = receipts["catalogResources"]
    for item in catalog["chunks"]:
        chunks[("core", item["offset"])] = (item["compressedBytes"], item["compressedSha256"])
    for item in catalog["copiedCatalogFiles"]:
        if sha(CORE / item["relative"]) != item["sha256"]:
            raise ValueError("Current private catalog/signature bytes changed")
    if sha(CORE / "chunk/store.cdb.idx") != catalog["sourceIndexSha256"]:
        raise ValueError("Current original chunk index changed")
    with (CORE / "chunk/store.cdb").open("rb") as source:
        if hashlib.sha256(source.read(256)).hexdigest() != catalog["headerSha256"]:
            raise ValueError("Original sparse chunk header changed")
        for (group, offset), (size, digest) in chunks.items():
            if group != "core":
                continue
            source.seek(offset)
            if hashlib.sha256(source.read(size)).hexdigest() != digest:
                raise ValueError("Selected staged mechanical chunk differs")
    dp_chunks = {offset: value for (group, offset), value in chunks.items() if group == "dp"}
    dp_witnesses = [r for r in receipts.values() if r.get("resourceGroup") == "dp" and "sourceSha256" in r]
    if dp_chunks:
        if len(dp_witnesses) != 1:
            raise ValueError("DP chunk witnesses require one exact full DP store identity receipt")
        with (CORE.parent / "dp/chunk/store.cdb").open("rb") as source:
            for offset, (size, digest) in dp_chunks.items():
                source.seek(offset)
                if hashlib.sha256(source.read(size)).hexdigest() != digest:
                    raise ValueError("Selected original DP chunk differs")
    return {"verifiedChunks": len(chunks), "compressedBytes": sum(x[0] for x in chunks.values()),
            "originalCatalogFilesVerified": len(catalog["copiedCatalogFiles"]),
            "originalHeaderAndIndexVerified": True,
            "resourceGroupOffsetNamespacesSeparate": True, "fullDpStoreWitnessesVerified": len(dp_witnesses)}


def main(candidate_index=1, additional_resources=(), reviewed_source_changes=(), last_native_index=None, staged_predecessor=None,
         failed_diagnostic_predecessor_sha256=None, auxiliary_source_predecessor=None, reference_run=1):
    if not 1 <= candidate_index <= 22 or len(additional_resources) > 8:
        raise ValueError("Bounded fresh practice candidate/resource receipt count required")
    selection = prepare_reference_selection(candidate_index, reference_run)
    suffix = str(candidate_index)
    config_path = SANDBOX / ("sandbox-practice" + suffix + ".json")
    if config_path.exists():
        raise FileExistsError("Preserve prior practice candidate")
    native_index = candidate_index - 1 if last_native_index is None else last_native_index
    if last_native_index is not None and not 1 <= native_index < candidate_index:
        raise ValueError("Last native output must precede the fresh candidate")
    previous = SANDBOX / ("fixture-readback-output2" if candidate_index == 1 else
                          "practice-output" + str(native_index))
    previous_verification = json.loads((previous / "verification.json").read_text())
    predecessor = previous
    package_predecessor = previous
    auxiliary_predecessor_ack = None
    normal_failed_predecessor_ack = None
    if candidate_index == 13:
        expected_failure = "bc665aaecf7f418fbf4cdbc0f39e67c5c30a32c7c7437ff469adaa6c38717717"
        if native_index != 12 or staged_predecessor is not None or auxiliary_source_predecessor is not None or \
           sha(previous / "verification.json") != expected_failure or previous_verification["status"] != "failed" or \
           previous_verification["exitCode"] != 0 or previous_verification["timedOut"] or \
           not previous_verification["normalNativeQuitRequested"] or previous_verification["completeBattle"] or \
           previous_verification["completedUpdateCalls"] != 0 or \
           not previous_verification["requiredPreferenceStorageControlsPassed"] or \
           not all(previous_verification["frozenSourceInputsUnchanged"].values()):
            raise ValueError("Main13 requires the exact preserved normally-exited failed-main12 fixture trial")
        from copy_complete153_store import ensure_closed, record_stat
        prior_archive = json.loads((previous / "staging.json").read_text())
        for group in ("sources", "resourceReceipts"):
            for name, item in prior_archive[group].items():
                if sha(previous / ("frozen-" + name + Path(item["path"]).suffix)) != item["sha256"]:
                    raise ValueError("Failed main12 frozen source/resource archive differs")
        before_path = previous / "practice12-full-store-input-before.json"
        after_path = previous / "practice12-full-store-input-after.json"
        before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
        if not after["fullStoreInputUnchanged"] or not after["fullReadbackReceiptReusable"] or \
           before["groupStats"] != after["groupStats"] or any(record_stat(CORE.parent / group / "chunk/store.cdb") != stat for group, stat in after["groupStats"].items()):
            raise ValueError("Failed main12 core/DP pre/post/current witnesses differ")
        normal_failed_predecessor_ack = {"archive": str(previous), "verificationSha256": expected_failure,
            "actualStatus": "failed", "actualExitCode": 0, "normalNativeQuitRequested": True,
            "failureStage": "captured_inputs", "battleCompleted": False, "relabelledUnrun": False,
            "allArchivedSourcesAndReceiptsVerified": True, "preferenceStorageControlsPassed": True,
            "coreDpPrePostAndCurrentIdentityMatch": True,
            "deadChild": ensure_closed(previous_verification["actualPlayerPid"]),
            "storeWitnessSha256": {"before": sha(before_path), "after": sha(after_path)}}
    if staged_predecessor is not None:
        if not native_index < staged_predecessor < candidate_index:
            raise ValueError("Explicit unrun predecessor must follow last actual native trial")
        predecessor = SANDBOX / ("practice-unrun-candidate" + str(staged_predecessor))
        unrun = json.loads((predecessor / "staged-unrun.json").read_text())
        if unrun["status"] != "staged_unrun" or unrun["nativeRunPerformed"] or \
           (SANDBOX / ("practice-output" + str(staged_predecessor))).exists():
            raise ValueError("Staged predecessor has an actual native output")
        package_predecessor = predecessor
    if auxiliary_source_predecessor is not None:
        auxiliary = auxiliary_source_predecessor.resolve()
        expected_auxiliary = SANDBOX / "dp-loader-output2"
        expected_sha = "bc973e780bc49936f94e1a1890ae4e162cd837b9fe80ebfbda69ebe8e61aba19"
        if candidate_index != 10 or native_index != 9 or staged_predecessor is not None or \
           auxiliary != expected_auxiliary.resolve() or sha(auxiliary / "verification.json") != expected_sha:
            raise ValueError("Only explicitly named passed DP-loader2 may be candidate10's auxiliary package predecessor")
        auxiliary_verification = json.loads((auxiliary / "verification.json").read_text())
        if auxiliary_verification["status"] != "passed" or auxiliary_verification["exitCode"] != 0 or \
           auxiliary_verification["timedOut"] or not auxiliary_verification["complete"] or \
           not auxiliary_verification["normalNativeQuitRequested"] or not auxiliary_verification["fullStoreInputsUnchanged"] or \
           len(auxiliary_verification["typedAssetPositiveControls"]) != 10 or \
           not all(auxiliary_verification["frozenSourceInputsUnchanged"].values()):
            raise ValueError("Auxiliary original DP controls no longer pass")
        aux_staging = json.loads((auxiliary / "staging.json").read_text())
        for group in ("sources", "resourceReceipts"):
            for name, item in aux_staging[group].items():
                if sha(auxiliary / ("frozen-" + name + Path(item["path"]).suffix)) != item["sha256"]:
                    raise ValueError("Auxiliary archived source/resource differs")
        from copy_complete153_store import ensure_closed, record_stat
        before_path = auxiliary / "dp-loader2-full-store-input-before.json"
        after_path = auxiliary / "dp-loader2-full-store-input-after.json"
        before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
        if not after["fullStoreInputsUnchanged"] or not after["fullReadbackReceiptsReusable"] or \
           before["groupStats"] != after["groupStats"] or any(record_stat(CORE.parent / group / "chunk/store.cdb") != stat for group, stat in after["groupStats"].items()):
            raise ValueError("Auxiliary core/DP pre/post/current witnesses differ")
        auxiliary_predecessor_ack = {"archive": str(auxiliary), "verificationSha256": expected_sha,
            "scope": auxiliary_verification["scope"], "actualStatus": "passed", "actualExitCode": 0,
            "battleStarted": False, "lastMainPracticeArchive": str(previous),
            "mainSourceComparisonArchive": str(predecessor), "actualPackageAndLogPredecessor": str(auxiliary),
            "hiddenHistoricalRestoration": False, "allFrozenInputsVerified": True,
            "coreDpPrePostAndCurrentIdentityMatch": True,
            "deadChild": ensure_closed(auxiliary_verification["actualPlayerPid"]),
            "storeWitnessSha256": {"before": sha(before_path), "after": sha(after_path)}}
        package_predecessor = auxiliary
    failed_predecessor_ack = None
    if previous_verification.get("exitCode") != 0:
        expected_failure = "b09f56fb11b8c3b55e28734f1233911c23d8d058390678288ad2916931e7b5d7"
        if candidate_index != 9 or native_index != 8 or staged_predecessor is not None or \
           failed_diagnostic_predecessor_sha256 != expected_failure or sha(previous / "verification.json") != expected_failure or \
           previous_verification["status"] != "failed" or previous_verification["exitCode"] != -529697949 or \
           previous_verification["timedOut"] or not all(previous_verification["frozenSourceInputsUnchanged"].values()):
            raise ValueError("Only explicitly acknowledged failed diagnostic8 may precede candidate9")
        from copy_complete153_store import ensure_closed, record_stat
        prior_staging = json.loads((previous / "staging.json").read_text())
        for group in ("sources", "resourceReceipts"):
            for name, item in prior_staging[group].items():
                frozen = previous / ("frozen-" + name + Path(item["path"]).suffix)
                if sha(frozen) != item["sha256"]:
                    raise ValueError("Failed diagnostic archive input differs: " + name)
        before_path, after_path = previous / "practice8-full-store-input-before.json", previous / "practice8-full-store-input-after.json"
        before, after = json.loads(before_path.read_text()), json.loads(after_path.read_text())
        if not after["fullStoreInputUnchanged"] or not after["fullReadbackReceiptReusable"] or \
           before["fullStoreBefore"] != after["fullStoreAfter"] or \
           record_stat(CORE / "chunk/store.cdb") != after["fullStoreAfter"]:
            raise ValueError("Failed diagnostic full-store witnesses differ")
        failed_predecessor_ack = {"archive": str(previous), "verificationSha256": expected_failure,
            "actualStatus": "failed", "actualExitCode": -529697949, "actualExitHex": "0xE06D7363",
            "nativeQuitClaimed": False, "relabelledUnrun": False,
            "deadChild": ensure_closed(previous_verification["actualPlayerPid"]),
            "allFrozenInputsVerified": True, "fullStorePrePostAndCurrentIdentityMatch": True,
            "storeWitnessSha256": {"before": sha(before_path), "after": sha(after_path)}}
    elif failed_diagnostic_predecessor_sha256 is not None:
        raise ValueError("Failed predecessor acknowledgement supplied for ordinary exit")
    if previous_verification["status"] not in ("passed", "failed") or \
            sha(package_predecessor / "scene-probe.js") != sha(GAME / "NKAB/dist/scene-probe.js"):
        raise ValueError("Previous native source must be archived exactly")
    if sha(HOOK) != HOOK_SHA:
        raise ValueError("Frozen dependency package changed")
    paths = {"driver": HERE / "candidate-modules/headless_driver.js",
             "settingsSource": HERE / "practice_settings.js",
             "settingsInput": HERE / "practice-settings-input.json",
             "reconstructionSource": HERE / "replay-input/reconstruct_snapshots.js",
             "originalInput": HERE / "replay-input/run1/native-replay-input.json",
             "expectedReadbacks": HERE / "replay-input/run1/native-conversion-expected.json",
             "fixtureSource": HERE / "replay-input/prepare_practice_fixture.js",
             "fixtureInput": HERE / "replay-input/run1/native-fixture-input.json",
             "waveSource": HERE / "replay-input/practice_wave_resolver.js",
             "callbackSource": HERE / "practice_host_callbacks.js",
             "modeSource": HERE / "practice_mode.js", "modeInput": HERE / "practice-mode-input.json",
             "geometrySource": HERE / "practice_geometry.js", "geometryInput": HERE / "practice-geometry-source.json",
             "additionalGeometryInput": HERE / "practice-additional-geometry-source.json",
             "aimSource": HERE / "practice_aim_binding.js", "schedulerSource": HERE / "practice_frame_scheduler.js",
             "resultSource": HERE / "practice_result_capture.js", "tickSource": HERE / "practice_tick_runner.js",
             "probeSource": HERE / "practice_probe.js",
             "audioSource": HERE / "candidate-modules/mechanics_audio_boundary.js",
             "monsterSource": HERE / "candidate-modules/mechanics_monster_headless.js",
             "fxSource": HERE / "candidate-modules/mechanics_fx_cleanup_parent.js"}
    if candidate_index >= 3:
        paths["packetSource"] = HERE / "practice_packet_export.js"
    if candidate_index >= 6:
        paths.update({"fxControllerInput": HERE / "practice-fx-controller-source.json",
                      "timelineControllerInput": HERE / "practice-timeline-controller-source.json",
                      "skillPoolObserverSource": HERE / "practice_skill_pool_observer.js"})
    if candidate_index >= 7:
        paths.update({"fxSource": HERE / "practice_fx_cleanup_observer.js",
                      "graphicOptionsInput": HERE / "practice-graphic-options-source.json",
                      "cleanupSourceProof": HERE / "practice-fx-cleanup-lookup-source.json",
                      "graphicOptionsMetadata": HERE.parent / "metadata/current153-graphic-options1/mechanics-metadata.json",
                      "gradientDependencyMetadata": HERE.parent / "metadata/current153-gradient-dependencies1/mechanics-metadata.json",
                      "globalShaderProviderMetadata": HERE.parent / "metadata/current153-global-shader-provider2/mechanics-metadata.json",
                      "projectileGenericProof": HERE / "projectile-generic-proof4/report.json",
                      "projectileLoadingSource": HERE / "projectile-loading-chained.json"})
    if candidate_index == 8:
        paths.update({"skeletonObserverSource": HERE / "practice_skeleton_setup_observer.js",
                      "skeletonSourceMetadata": HERE.parent / "metadata/current153-combat-skeleton1/mechanics-metadata.json"})
    if candidate_index >= 9:
        paths.update({"skeletonSourceObserverSource": HERE / "practice_skeleton_source_observer.js",
                      "skeletonSourceObserverProof": HERE / "practice-skeleton-source-observer-source.json",
                      "skeletonSourceMetadata": HERE.parent / "metadata/current153-combat-skeleton1/mechanics-metadata.json",
                      "skeletonLoaderMetadata": HERE.parent / "metadata/current153-mechanical-controllers1/mechanics-metadata.json",
                      "skeletonCoverLoaderMetadata": HERE.parent / "metadata/current153-skeleton-cover-loader1/mechanics-metadata.json"})
    if candidate_index >= 10:
        paths.update({"dpRegistrationSource": HERE / "practice_dp_registration.js",
                      "dpRegistrationSourceProof": HERE / "practice-dp-registration-source.json",
                      "dpNativeControlsProof": SANDBOX / "dp-loader-output2/verification.json",
                      "monsterColorReadinessSource": HERE / "practice_monster_color_readiness.js",
                      "monsterGradientMetadata": HERE.parent / "metadata/current153-monster-gradient1/mechanics-metadata.json",
                      "monsterPrefabReadinessMetadata": HERE.parent / "metadata/current153-monster-prefab-readiness1/mechanics-metadata.json",
                      "monsterAnimationReadinessMetadata": HERE.parent / "metadata/current153-monster-anim-readiness1/mechanics-metadata.json"})
    if candidate_index >= 11:
        paths.update({"autoPreferencesSource": HERE / "practice_auto_preferences.js",
                      "autoInitializationSourceProof": HERE / "practice-auto-initialization-source.json",
                      "autoPreferencesIsolationProof": HERE / "playerprefs-isolation-audit.json",
                      "autoPreferencesCurrentBaseline": HERE / "auto-preferences-before-main11.json",
                      "autoPreferencesWitnessSource": HERE / "check_auto_preferences153.py",
                      "autoPreferenceKeysProof": HERE / "auto-preference-metadata-proof1/report-evaluation.json",
                      "autoPreferenceKeysOriginalReport": HERE / "auto-preference-metadata-proof1/report.json"})
        auto_proof = json.loads(paths["autoInitializationSourceProof"].read_text())
        for index, item in enumerate(auto_proof["metadataFiles"], 1):
            path = ROOT / item["path"]
            if sha(path) != item["sha256"]:
                raise ValueError("Reviewed original auto initialization metadata differs")
            paths["autoInitializationMetadata" + str(index)] = path
        for name, digest in {
            "autoInitializationSourceProof": "8125d8c0a7bca7ac0d3e101ce8b9fadd2aeb4e0b368611dd6fa704f3bbf299b0",
            "autoPreferencesIsolationProof": "149ecd1c37f6b56d7503f0ce04eb110fbe566e67ab0f1798963a809b3ad670fd",
            "autoPreferencesCurrentBaseline": "64b8b0a8f9ddbdc78d46942a1530d867b589b9930b1edfcb263c458a400ea46f",
            "autoPreferencesWitnessSource": "587a40b57ef365111112f754a8c8f30f3d9783c80114f89e086f5bc1c5b62b0d",
            "autoPreferenceKeysProof": "6d66e14af5044947a8bddf607ec385e82cc721c3976ccc394f72408bae36c924",
        }.items():
            if sha(paths[name]) != digest:
                raise ValueError("Exact reviewed auto preference input/proof/helper differs: " + name)
    if candidate_index >= 12:
        paths.update({"monsterSource": HERE / "practice_monster_color_observer.js",
                      "monsterOriginalColorSourceProof": HERE / "practice-monster-color-source.json",
                      "autoPreferencesContinuityWitnessSource": HERE / "check_auto_preferences_continuity153.py",
                      "autoPreferencesEstablishedPostWitness": SANDBOX / "practice-output11/practice11-auto-preferences-post.json",
                      "autoPreferencesEstablishedVerification": SANDBOX / "practice-output11/verification.json",
                      "resultPacketLifetimeAudit": HERE / "practice11-result-packet-order-audit.json",
                      "resultLifetimeHostTestSource": HERE / "test_practice_host_callbacks.js",
                      "resultLifetimeTestSource": HERE / "test_practice_result_lifetime.js",
                      "practiceModeTestSource": HERE / "test_practice_mode.js",
                      "practiceTickTestSource": HERE / "test_practice_tick_runner.js"})
        for name, digest in {
            "monsterOriginalColorSourceProof": "07e954c5a819259cf7d3d1f07576aa87a6b0e80949ba50debd22f3f01d9e5a2f",
            "autoPreferencesContinuityWitnessSource": CONTINUITY22_SOURCE_SHA if candidate_index >= 22 else CONTINUITY19_SOURCE_SHA if candidate_index >= 19 else CONTINUITY_SOURCE_SHA if candidate_index >= 16 else "07673ea91e7580291cd262a782da4b0de2756b3edc99bbc7f4b74545c090b264",
            "autoPreferencesEstablishedPostWitness": "1fcd38c07f9ad25b85405899231ced0d19d7d9ba5ffd5baed322525c82b5681c",
            "autoPreferencesEstablishedVerification": "1c580da3ebf5b58c4ab9b6f49fca9994ded600242ae1d44f2ae4a4dd8790ff3b",
            "resultPacketLifetimeAudit": "c02be8134105ea72af9f8909d4bc3b912fdd632a1ec8d3bb6927c5259b4587dd",
            "resultLifetimeHostTestSource": "d93799106f639928fc2a146031134e09af7067a274e9509a6a4981f1b298840f",
        }.items():
            if sha(paths[name]) != digest:
                raise ValueError("Reviewed original-color/pref-continuity input differs: " + name)
        result_lifetime = json.loads(paths["resultPacketLifetimeAudit"].read_text())
        if result_lifetime["clientSha256"] != "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2" or \
           result_lifetime["failedTrial"]["verificationSha256"] != sha(paths["autoPreferencesEstablishedVerification"]) or \
           Path(result_lifetime["failedTrial"]["path"]).resolve() != (SANDBOX / "practice-output11").resolve() or \
           result_lifetime["failedTrial"]["sceneEventsSha256"] != sha(SANDBOX / "practice-output11/scene-events.jsonl") or \
           len(result_lifetime["sourceReceipts"]) != 7:
            raise ValueError("Exact current153 result lifetime audit binding differs")
        for index, (name, digest) in enumerate(sorted(result_lifetime["sourceReceipts"].items()), 1):
            path = (HERE / name).resolve()
            if path.parent != HERE.resolve() or path.suffix != ".json" or sha(path) != digest:
                raise ValueError("Reviewed result lifetime source receipt differs")
            paths["resultLifetimeSourceReceipt" + str(index)] = path
    if candidate_index >= 13:
        paths.update({"callbackFixtureBoundaryTestSource": HERE / "test_practice_callback_fixture_boundary.js",
                      "callbackFixtureRegressionReceipt": HERE / "practice-callback-fixture-regression.json"})
        if sha(paths["callbackFixtureBoundaryTestSource"]) != "752e96bdeb360aa2a439f37fa7ebeccc62219a6086e49649e560d6da9279e84a" or \
           sha(paths["callbackFixtureRegressionReceipt"]) != "f89bf9c262f6ad774e6bcacf5d510c3091002206e25e67b622999767e55f3afd":
            raise ValueError("Reviewed real callback producer/fixture consumer regression evidence differs")
    if candidate_index >= 14:
        decoder = HERE / "packet-decoder"
        paths.update({"binaryPacketBindingProof": HERE / "practice13-binary-export-binding.json",
                      "binaryPacketSourceAudit": HERE / "practice13-serializer-and-score-audit.json",
                      "binaryPacketArrayApiProof": HERE / "practice13-byte-array-api-source.json",
                      "binaryPacketRawWriterProof": HERE / "practice13-original-raw-wire-writer-source.json",
                      "binaryPacketExportTestSource": HERE / "test_practice_packet_export.js",
                      "binaryPacketWriterTestSource": HERE / "test_practice_packet_writer.js",
                      "binaryPacketMetadata": HERE.parent / "metadata/current153-packet-serialization1/mechanics-metadata.json",
                      "binaryPacketReflectionMetadata": HERE.parent / "metadata/current153-packet-wire-reflection1/mechanics-metadata.json",
                      "binaryPacketRawWriterMetadata": HERE.parent / "metadata/current153-packet-raw-write1/mechanics-metadata.json",
                      "packetDecoderBuildReceipt": decoder / "build-controls3.json",
                      "packetDecoderSource": decoder / "Program.cs", "packetDecoderProject": decoder / "PacketDecoder.csproj",
                      "packetDecoderBuildSource": decoder / "build_and_check.py",
                      "packetArchiveDecoderSource": decoder / "archive_decode.py",
                      "packetArchiveDecoderTestSource": decoder / "test_archive_decode.py",
                      "packetDecoderReferenceControl": decoder / "reference-control1.json",
                      "packetArchiverSource": HERE / "archive_practice153.py"})
        for name, digest in {
            "binaryPacketBindingProof": "c87289e75a10a72cf9c67d8bb216fc8e96de53956856c0c19869470fc3322e92",
            "binaryPacketSourceAudit": "cb4ca706236346ccc6a093ba239b3ea70cad32081803546bb23161a931b75f70",
            "binaryPacketArrayApiProof": "a604a6c78550a7e4b7dc35ceaaa71397f7fb7cc1f2c7ac48e6ddaf43e248a4b3",
            "binaryPacketRawWriterProof": "2bda6cb69b6d9e99910fa0ff26581f18e56113e87499e207c16efd133ca13a61",
            "binaryPacketExportTestSource": "4abbd72ce12b6a68638c0e1db9a4749766a86ea7a457b2e3c22b49419b3f2e10",
            "binaryPacketWriterTestSource": "6603bae2bb7bc3b71469cb78584759975b48d307fe4e7f5d52fd61c78fc9758c" if candidate_index >= 16 else "fef510b5cf99d79d72441e9b50d049ee3cea64ff0d1414b2d5130f839bd276be" if candidate_index >= 15 else "54332fca4d2970cbacb8c92c3e4330766f9016fb4e45bfd723d4f3a5716ce23f",
            "binaryPacketMetadata": "7feaa22d1cd9bb83d506d688d44f1d5137d017083eeb87c1fab81c11969f61e5",
            "binaryPacketReflectionMetadata": "1bc9d04cad7789e00e56b5db74a80582f9f7f2b46b3aa8c52288dd3351b34e4c",
            "binaryPacketRawWriterMetadata": "6d0addeba599ddf292c04f7c64355fe054fcf4386d8e40cfe148e3b5c8cd2bd8",
            "packetDecoderBuildReceipt": "30b858ede40509c6f5f092dcca0118b720d2faa91b93f81430daaf4c495ade9d",
        }.items():
            if sha(paths[name]) != digest:
                raise ValueError("Reviewed binary packet/decoder input differs: " + name)
        decoder_spec = importlib.util.spec_from_file_location("packet_archive_decoder153", paths["packetArchiveDecoderSource"])
        decoder_module = importlib.util.module_from_spec(decoder_spec)
        decoder_spec.loader.exec_module(decoder_module)
        decoder_receipt = decoder_module.validate_build_receipt(paths["packetDecoderBuildReceipt"])
        for name, item in decoder_receipt["artifacts"].items():
            paths["packetDecoderArtifact" + name.replace(".", "_")] = Path(item["path"])
        paths["packetDecoderRuntime"] = Path(decoder_receipt["dotnet"]["path"])
        binary_audit = json.loads(paths["binaryPacketSourceAudit"].read_text())
        if binary_audit["clientSha256"] != "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2" or \
           binary_audit["failedTrial"]["verificationSha256"] != sha(SANDBOX / "practice-output13/verification.json") or \
           binary_audit["failedTrial"]["sceneEventsSha256"] != sha(SANDBOX / "practice-output13/scene-events.jsonl"):
            raise ValueError("Original failed JSON-export evidence binding differs")
        for index, (name, digest) in enumerate(sorted(binary_audit["sourceReports"].items()), 1):
            path = (HERE / name).resolve()
            if path.parent != HERE.resolve() or path.suffix != ".json" or sha(path) != digest:
                raise ValueError("Reviewed binary packet source receipt differs")
            paths["binaryPacketSourceReceipt" + str(index)] = path
    if candidate_index >= 16:
        paths.update(original_overlay_source_paths(candidate_index))
        if candidate_index >= 17:
            paths.update({"overlayPreviousIntegrationProof": HERE / "practice-overlay-rng-integration4.json",
                          "overlayProofTransitionTestSource": HERE / "test_overlay_prepared_proof_transition.py",
                          "archiveFrozenAliasTestSource": HERE / "test_archive_frozen_aliases153.py",
                          "overlayFailed16Verification": SANDBOX / "practice-output16/verification.json"})
            if sha(paths["overlayPreviousIntegrationProof"]) != OVERLAY_INTEGRATION4_SHA or \
               sha(paths["archiveFrozenAliasTestSource"]) != "289322d4cfcbda0c438e304207874c134fbab5f34ff24c4ed5dde10a94dc1c28" or \
               sha(paths["overlayFailed16Verification"]) != "0a91a45e8d5451fe3e3d5ce19af420f32769cc2cac2fefd0b1a2bd8d3bfb66cc":
                raise ValueError("Exact original failed16/current5 provenance required")
        overlay_readback = verify_original_overlay_inputs(paths, candidate_index)
    if candidate_index >= 19:
        paths["mainQueueBackpressureRepairProof"] = HERE / "practice-main-queue-backpressure-repair1.json"
        if sha(paths["mainQueueBackpressureRepairProof"]) != QUEUE19_PROOF_SHA:
            raise ValueError("Exact reviewed pending-main repair receipt required")
    if candidate_index >= 18:
        paths.update(original_locale_paths(candidate_index))
        locale_readback = verify_original_locale_inputs(paths, candidate_index)
    if candidate_index >= 19:
        paths["source19ReportingCorrection"] = HERE / "practice19-source-proof-correction.json"
        verify_practice19_source_correction(paths)
    if candidate_index >= 20:
        paths.update(complete_locale_paths(candidate_index))
        complete_locale_readback = verify_complete_locale_inputs(paths, candidate_index)
    if candidate_index >= 22:
        paths.update({"practice22PriorIntegrationProof": HERE / "practice-overlay-rng-integration6.json",
                      "practice22BoundsTestSource": HERE / "test_stage_matched_reference_selection.py",
                      "practice22ProofTransitionTestSource": HERE / "test_stage_practice22_transition.py",
                      "practice22BoundPreparationPlan": HERE / "practice22-bounded-preparation-plan.json",
                      "practice22Archived21Verification": SANDBOX / "practice-output21/verification.json"})
        if sha(paths["practice22PriorIntegrationProof"]) != OVERLAY_INTEGRATION6_SHA or \
           sha(paths["practice22Archived21Verification"]) != "e703ece059d0773c481ea05420567fac3daf138cd0e4f9c9a295e9878049eb83":
            raise ValueError("Exact archived21 and historical integration6 required for22")
    if candidate_index >= 15:
        paths.update({"rngStateVerifierSource": HERE / "practice_rng_state_verifier.js",
                      "rngStateVerifierTestSource": HERE / "test_practice_rng_state_verifier.js",
                      "rngProbeBoundaryTestSource": HERE / "test_practice_rng_probe_boundary.js",
                      "rngStateSourceProof": HERE / "practice-full-rng-state-source.json",
                      "rngGateIntegrationProof": HERE / "practice-intro-rng-integration3.json",
                      "rngGatePreviousIntegrationProof": HERE / "practice-full-rng-gate-integration2.json",
                      "rngGatePriorIntegrationProof": HERE / "practice-full-rng-gate-integration.json",
                      "rngHistorical14NegativeProof": HERE / "practice14-full-rng-gate-negative.json",
                      "rngExpectedInput": HERE / "rng-state/expected1/run1-onstart-shared-rng.json",
                      "rngExpectedExtractorSource": HERE / "rng-state/extract_expected_states.py",
                      "rngSourceReceiptBuilder": HERE / "rng-state/build_source_receipt.py",
                      "rngArchiveGateSource": HERE / "rng-state/archive_gate.py",
                      "rngArchiveGateTestSource": HERE / "rng-state/test_archive_gate.py",
                      "rngStartupTransporterComparison": HERE / "original-transporter-startup-comparison.json",
                      "cutsceneControllerInput": HERE / "practice-cutscene-control-binding.json",
                      "cutsceneControllerPrefabProof": HERE / "practice-cutscene-control-source.json",
                      "cutsceneControllerTestSource": HERE / "test_practice_cutscene_boundary.js",
                      "introBoundaryTestSource": HERE / "test_practice_intro_boundary.js",
                      "cutsceneBuiltinTestSource": HERE / "test_stage_cutscene_resources.py",
                      "cutsceneUiSlotProof": HERE / "cutscene-ui-slots1/report.json",
                      "cutscenePrivateBuiltinsProof": HERE / "practice-cutscene-private-builtins1.json",
                      "cutsceneDirectorMetadata": HERE.parent / "metadata/current153-cutscene-director1/mechanics-metadata.json",
                      "cutsceneBindingBuilder": HERE / "build_cutscene_binding153.py",
                      "introIntegrationBuilder": HERE / "build_intro_integration153.py",
                      "cutsceneExtractorSource": HERE / "extract_cutscene_control153_source.py"})
        paths["cutscenePathRepairProof"] = HERE / "practice15-staging-path-repair1.json"
        paths["cutscenePathRepairTestSource"] = HERE / "test_cutscene_evidence_paths.py"
        if sha(paths["cutsceneControllerInput"]) != CUTSCENE_SOURCE_SHA or \
           sha(paths["cutsceneControllerPrefabProof"]) != CUTSCENE_PREFAB_SHA:
            raise ValueError("Original mechanical intro source binding differs")
        cutscene_binding = json.loads(paths["cutsceneControllerInput"].read_text())
        for index, (name, digest) in enumerate(sorted(cutscene_binding["sourceEvidence"].items()), 1):
            path = cutscene_evidence_path(name)
            if not path.is_relative_to(HERE.parent.resolve()) or sha(path) != digest:
                raise ValueError("Original mechanical intro dependency source differs: " + name)
            paths["cutsceneDependencyProof" + str(index)] = path
        cutscene_prefab = json.loads(paths["cutsceneControllerPrefabProof"].read_text())
        director_metadata = json.loads(paths["cutsceneDirectorMetadata"].read_text())
        duration_methods = [m for c in director_metadata["classes"]
                            if c["class"] == "UnityEngine.Playables.PlayableDirector"
                            for m in c["methods"] if m["name"] == "get_duration"]
        if director_metadata["clientSha256"] != cutscene_binding["clientSha256"] or \
           director_metadata.get("missingRoots") or len(duration_methods) != 1 or \
           duration_methods[0]["nativeRva"] != cutscene_binding["directorDurationGetter"]["rva"] or \
           duration_methods[0]["returns"] != "System.Double" or duration_methods[0]["parameters"]:
            raise ValueError("Original intro director duration ABI differs")
        builtin_copies = verify_cutscene_builtin_copies(cutscene_prefab, ROOT / "NIKKE/NIKKE/game", GAME)
        for index, item in enumerate(builtin_copies, 1):
            paths["cutscenePrivateBuiltin" + str(index)] = Path(item["target"])
        for name, digest in {
            "rngStateVerifierSource": "2794e0e47fb0f85b8cc6ec36dac96461a9452a74820e528acb0e17370bcdcde2",
            "rngStateVerifierTestSource": "22ebdf1c2138c800745755ee09d4a8b980ab5239effdd4218d88c7d7fa2b3f37",
            "rngProbeBoundaryTestSource": "2365598f15030b5eb7d5a19a44b3496c8ca002de4d0fa17426407653a5cd68c5" if candidate_index >= 16 else "d849762eb27ce82ecd0b0a7bf3cba87022ce1f134518d62336431060b2d6e5f8",
            "rngArchiveGateSource": "e4f6efdb9100abc1e6f64f297b442fc7485371b0e35898cdd02d2e88b9257c7d",
            "rngArchiveGateTestSource": "b45355986adf82712227bffb39454e320bfcba7c6d462d59f2bdefeff69652f5",
            "rngStateSourceProof": "5d1acddd9d2e1e3a68575f46abe7eb5b12a37c243247158843184fe42815ac61",
            "rngGatePreviousIntegrationProof": "a153291baf326eab6569e403d6696787a7cb2c2a99d29d7896d01e7b4447592f",
            "rngGateIntegrationProof": "bec9fd51648ecaf5c7f92db6c8a020bda092c0c37a8c193a74bc6b5e3f2f7cef",
            "rngGatePriorIntegrationProof": "ceaf654b3dad5dfd37734629d31d9df608c50a607de937f015e14997331ae7a9",
            "rngHistorical14NegativeProof": "856f046638069c6da05f344bc2485e0b8314557f62ec501f388cc5b5aed489e4",
            "rngExpectedInput": "214742a251316375b8b2e3527d97df9150ee2039238fc3042ed358cb5183bb55",
            "rngStartupTransporterComparison": "1d7cd752263a826d43077389a4e4bce9addc0776306081bfe3d04b7726ffe6e7",
            "cutsceneControllerTestSource": "fca4f9c2cc694695bb47e229dc39778c0251503cbe25014f318947741dc0980e",
            "introBoundaryTestSource": "f9871c0f023f96ac3e471a20d720ba3401772e2879e7134a0d6fcbf9d138459d",
            "cutsceneBuiltinTestSource": "9ac9eb8f02ea5aa4f7bef32575e62bb9361f85f70ff0db6f79368af13a11b236",
            "cutsceneUiSlotProof": "d0d91682797d2a69f4126eea7b5d47e3491cf2c6e7ef6b33baf3578b5fb9c786",
            "cutsceneDirectorMetadata": "ba7051d4ce42b0f2a374a8e11d22c9d62b09f3d09d72b16d63fd29752288c724",
            "cutscenePrivateBuiltinsProof": "d6f1fe206121c9d1482b73320c82f60ad41d120c4713c9023397c252fa6424be",
        }.items():
            if sha(paths[name]) != digest:
                raise ValueError("Reviewed complete original shared RNG guard input differs: " + name)
        rng_proof = json.loads(paths["rngStateSourceProof"].read_text())
        # Integration3 is immutable historical evidence. Candidate16+ uses its
        # own exact current source/mock proof, with the same strict RNG reader.
        integration_proof = json.loads(paths["overlayIntegrationProof" if candidate_index >= 16 else "rngGateIntegrationProof"].read_text())
        if integration_proof["nativeRunPerformed"] is not False or integration_proof["candidateFrozen"] is not False or \
           any(row["exitCode"] != 0 for row in integration_proof["commands"]):
            raise ValueError("Reviewed RNG integration source/mock controls differ")
        for name, digest in integration_proof["sourceHashes"].items():
            path = (HERE / name).resolve()
            if not path.is_relative_to(HERE.resolve()) or sha(path) != digest:
                raise ValueError("Reviewed RNG integration/archiver source differs")
        for name, item in rng_proof["inputs"].items():
            path = Path(item["path"]).resolve()
            if not path.is_relative_to(ROOT.resolve()) or sha(path) != item["sha256"]:
                raise ValueError("Original RNG reader provenance source differs")
            paths["rngReaderSourceProof" + name] = path
        for run, item in rng_proof["expectedStates"].items():
            path = Path(item["path"]).resolve()
            if not path.is_relative_to((HERE / "rng-state/expected1").resolve()) or sha(path) != item["sha256"]:
                raise ValueError("Original captured complete RNG expectation differs")
            paths["rngExpectedSourceProofRun" + run] = path
    if selection is not None:
        for key in REFERENCE_INPUT_KEYS:
            paths[key] = selection["paths"][key]
        paths.update({"referenceSelectionSource": HERE / "matched_reference_selection153.py",
                      "referenceRngExtractorSource": HERE / "rng-state/extract_expected_states.py",
                      "matchedReferenceInputSource": HERE / "matched_reference_inputs153.py",
                      "matchedReferenceSnapshotExtractor": HERE / "replay-input/extract_snapshot_inputs.py",
                      "matchedReferenceFixtureExtractor": HERE / "replay-input/extract_fixture_input.py",
                      "matchedReferenceProvenanceRun2": HERE / "replay-input/run2/matched-reference-provenance.json",
                      "matchedReferenceProvenanceRun3": HERE / "replay-input/run3/matched-reference-provenance.json",
                      "referenceSelectionProof": SANDBOX / ("practice-reference-selection" + suffix + ".json")})
        if paths["referenceSelectionProof"].exists():
            raise FileExistsError("Preserve original selected-reference staging proof")
    reviewed = {}
    for item in reviewed_source_changes:
        name, digest = item.split("=", 1)
        allowed_source = name in paths and (source_review_allowed(name, paths[name], candidate_index) or
            current_prepared_target(name, paths[name], digest, candidate_index))
        if not allowed_source or not re.fullmatch("[a-f0-9]{64}", digest):
            raise ValueError("Explicit reviewed source name=SHA256 required; Python/JSON exceptions require exact prepared-proof or archiver/continuity pins")
        if sha(paths[name]) != digest:
            raise ValueError("Reviewed changed JS source differs: " + name)
        reviewed[name] = digest
    if "packetSource" in paths and reviewed.get("packetSource") != sha(paths["packetSource"]):
        raise ValueError("New packet serializer requires an explicit reviewed source hash")
    if "skillPoolObserverSource" in paths and reviewed.get("skillPoolObserverSource") != sha(paths["skillPoolObserverSource"]):
        raise ValueError("Passive observer requires an explicit reviewed source hash")
    if "skeletonObserverSource" in paths and reviewed.get("skeletonObserverSource") != sha(paths["skeletonObserverSource"]):
        raise ValueError("Skeleton diagnostic requires an explicit reviewed source hash")
    if "skeletonSourceObserverSource" in paths and reviewed.get("skeletonSourceObserverSource") != sha(paths["skeletonSourceObserverSource"]):
        raise ValueError("Skeleton source observer requires an explicit reviewed source hash")
    if "dpRegistrationSource" in paths and reviewed.get("dpRegistrationSource") != sha(paths["dpRegistrationSource"]):
        raise ValueError("Original DP registration requires an explicit reviewed source hash")
    if "monsterColorReadinessSource" in paths and reviewed.get("monsterColorReadinessSource") != sha(paths["monsterColorReadinessSource"]):
        raise ValueError("Read-only monster color readiness requires an explicit reviewed source hash")
    if "autoPreferencesSource" in paths and reviewed.get("autoPreferencesSource") != sha(paths["autoPreferencesSource"]):
        raise ValueError("Original isolated auto preference inputs require an explicit reviewed source hash")
    if "rngStateVerifierSource" in paths and reviewed.get("rngStateVerifierSource") != sha(paths["rngStateVerifierSource"]):
        raise ValueError("Read-only full shared RNG state verifier requires an explicit reviewed source hash")
    if candidate_index >= 16 and reviewed.get("autoPreferencesContinuityWitnessSource") != (CONTINUITY22_SOURCE_SHA if candidate_index >= 22 else CONTINUITY19_SOURCE_SHA if candidate_index >= 19 else CONTINUITY_SOURCE_SHA):
        raise ValueError("Extended continuity witness requires its exact explicit reviewed source hash")
    if "overlaySource" in paths and reviewed.get("overlaySource") != sha(paths["overlaySource"]):
        raise ValueError("Original overlay loader requires its exact explicit reviewed source hash")
    if "localeSource" in paths and reviewed.get("localeSource") != sha(paths["localeSource"]):
        raise ValueError("Original localization initializer requires its exact explicit reviewed source hash")
    prior = json.loads((predecessor / "staging.json").read_text())
    reference_changes, reference_change_proof = admit_reference_input_changes(prior, paths, selection)
    changed_sources = []
    removed_sources = {}
    for name, item in prior["sources"].items():
        if name == "referenceSelectionProof" and selection is not None:
            if item["sha256"] != selection["sha256"]:
                if name not in reference_changes:
                    raise ValueError("Selected-reference proof changed without a verified reference switch")
                changed_sources.append(name)
            continue
        if name not in paths:
            if candidate_index != 9 or name != "skeletonObserverSource" or \
               item["sha256"] != "6bb5ed7b24e4ccb1b45d0498cc1ad0e8e6b7a3e3e1ff2a6a7aaf7f58392818f0" or failed_predecessor_ack is None:
                raise ValueError("Unreviewed source removal: " + name)
            removed_sources[name] = {"sha256": item["sha256"], "reason": "Unsafe exception-helper observer removed; failed diagnostic8 preserved"}
            continue
        if sha(paths[name]) != item["sha256"]:
            prepared_names = {**prepared19_proof_specs(), **prepared22_proof_specs()} if candidate_index >= 22 else prepared19_proof_specs() if candidate_index >= 19 else prepared_overlay_proof_specs()
            if name in prepared_names and not current_prepared_transition(
                    name, item, paths[name], sha(paths[name]), reviewed, candidate_index):
                raise ValueError("Exact reviewed original prepared overlay proof transition required: " + name)
            locale_alias = locale19_dependency_transition(name, item, paths[name], sha(paths[name]), paths, reviewed, candidate_index)
            if name not in reference_changes and not locale_alias and reviewed.get(name) != sha(paths[name]):
                raise ValueError("Prior native source changed without reviewed hash: " + name)
            changed_sources.append(name)
    resources = {"catalogResources": SANDBOX / "catalog153-resources1.json",
                 "sharedResources": SANDBOX / "shared-mechanical-resources1.json",
                 "practiceResources": SANDBOX / "practice-mechanical-resources1.json",
                 "themeSource": HERE / "practice-theme-source.json"}
    if candidate_index >= 10:
        resources["dpCompleteStore"] = SANDBOX / "complete-current153-dp-store1.json"
        if sha(resources["dpCompleteStore"]) != "e2d3f2a929c85f3773ce37dda0f62569c5cd8a0a2876500e4bb856955c7efb6c":
            raise ValueError("Reviewed complete original DP resource witness differs")
    for name, item in prior.get("resourceReceipts", {}).items():
        if name not in resources:
            path = Path(item["path"])
            if sha(path) != item["sha256"]:
                raise ValueError("Previously bound added-resource receipt changed")
            resources[name] = path
    for raw_path in additional_resources:
        path = raw_path.resolve()
        if not path.is_relative_to(SANDBOX) or path.suffix != ".json" or not path.is_file():
            raise ValueError("Additional resource receipt must exist inside private clone")
        if path not in resources.values():
            resources["resourceAddition" + str(len([k for k in resources if k.startswith("resourceAddition")]) + 1)] = path
    if candidate_index >= 6:
        if sha(paths["fxControllerInput"]) != FX_SOURCE_SHA or sha(paths["timelineControllerInput"]) != TIMELINE_SOURCE_SHA:
            raise ValueError("Reviewed original FX/timeline source proofs differ")
        resources["fxControllerSourceProof"] = paths["fxControllerInput"]
        resources["timelineControllerSourceProof"] = paths["timelineControllerInput"]
    if candidate_index >= 7:
        if sha(paths["graphicOptionsInput"]) != GRAPHIC_SOURCE_SHA:
            raise ValueError("Reviewed original graphic-options source proof differs")
        resources["graphicOptionsSourceProof"] = paths["graphicOptionsInput"]
    if candidate_index >= 15:
        resources["cutsceneControllerSourceProof"] = paths["cutsceneControllerPrefabProof"]
    if candidate_index >= 16:
        resources["overlayCardSourceProof"] = paths["overlayCardSourceProof"]
        resources["popupControlSourceProof"] = paths["popupControlInput"]
    if sha(paths["geometryInput"]) != GEOMETRY_SHA or sha(paths["additionalGeometryInput"]) != ADDITIONAL_SHA or \
       sha(resources["practiceResources"]) != RESOURCE_SHA:
        raise ValueError("Fresh practice source receipts differ")
    resource_check = verify_resource_receipts(resources)
    if candidate_index >= 15:
        resource_check["cutscenePrivateBuiltinCopies"] = builtin_copies
    if candidate_index >= 16:
        resource_check.update(overlay_readback)
    if candidate_index >= 18:
        resource_check.update(locale_readback)
    if candidate_index >= 20:
        resource_check.update(complete_locale_readback)
    settings = json.loads(paths["settingsInput"].read_text())
    actual_input = json.loads(paths["originalInput"].read_text())
    expected = json.loads(paths["expectedReadbacks"].read_text())
    fixture = json.loads(paths["fixtureInput"].read_text())
    mode = json.loads(paths["modeInput"].read_text())
    if selection is not None:
        verify_selected_reference_paths(paths, selection["proof"], reference_run)
    mode_fixture_sha = selection["proof"]["fixtureHashContract"]["modeInputSourceSha256"] if selection else sha(paths["fixtureInput"])
    if actual_input["captureSha256"] != mode["captureSourceSha256"] or mode["inputSourceSha256"] != mode_fixture_sha:
        raise ValueError("Mode and original fixture source capture binding differ")
    if "rngExpectedInput" in paths:
        rng_expected = json.loads(paths["rngExpectedInput"].read_text())
        if rng_expected["referenceRunIndex"] != actual_input["runIndex"] or rng_expected["captureSha256"] != actual_input["captureSha256"] or \
           any(row["state"]["seed"] != mode["randomSeed"] for row in rng_expected["phases"].values()):
            raise ValueError("Full shared RNG expectation does not match selected actual reference inputs")
    if selection is not None:
        with paths["referenceSelectionProof"].open("xb") as sink:
            sink.write(selection["bytes"])
        if sha(paths["referenceSelectionProof"]) != selection["sha256"]:
            raise ValueError("Selected-reference proof byte readback differs")
    source = paths["driver"].read_text()
    boolean = "verified:retval.toInt32()!==0"
    dispatch = "          runMechanicsLifecycleProbe(record,finish,true);"
    if source.count(boolean) != 1 or source.count(dispatch) != 1:
        raise ValueError("Original driver completion/bool guard changed")
    source = source.replace(boolean, "verified:(retval.toInt32() & 0xff)!==0")
    source = source.replace(dispatch, original_practice_dispatch(candidate_index))
    source = source.replace("__TABLE_ARCHIVE__", json.dumps(str(SANDBOX / "current-tables.zip")))
    source = source.replace("__SCRATCH_PROFILE__", json.dumps(str(SANDBOX / "profile")))
    values = {"PRACTICE_SETTINGS_INPUT": settings, "CAPTURED_REPLAY_INPUT": actual_input,
              "CAPTURED_REPLAY_EXPECTED": expected,
              "CAPTURED_FIXTURE_INPUT": {"fixtureInput": fixture, "snapshotInput": actual_input},
              "PRACTICE_MODE_INPUT": mode,
              "MECHANICS_GEOMETRY_SOURCE": json.loads(paths["geometryInput"].read_text()),
              "MECHANICS_GEOMETRY_SOURCE_SHA256": GEOMETRY_SHA,
              "PRACTICE_ADDITIONAL_GEOMETRY_SOURCE": json.loads(paths["additionalGeometryInput"].read_text()),
              "PRACTICE_ADDITIONAL_GEOMETRY_SOURCE_SHA256": ADDITIONAL_SHA,
              "NATIVE153_BINDING": {"commonGeometryReceiptSha256": GEOMETRY_SHA,
                                    "practiceResourceReceiptSha256": RESOURCE_SHA}}
    if selection is not None:
        values["PRACTICE_REFERENCE_SELECTION"] = {"proof": selection["proof"], "proofSha256": selection["sha256"],
            "selectorSourceSha256": REFERENCE_SELECTOR_SHA}
    if candidate_index >= 18:
        values.update(original_locale_runtime_values(paths))
    for name, value in values.items():
        source += "\nglobalThis." + name + "=" + json.dumps(value, separators=(",", ":")) + ";\n"
    if candidate_index >= 6:
        for name, value in {"PRACTICE_FX_CONTROLLER_SOURCE": json.loads(paths["fxControllerInput"].read_text()),
                            "PRACTICE_FX_CONTROLLER_SOURCE_SHA256": FX_SOURCE_SHA,
                            "PRACTICE_TIMELINE_CONTROLLER_SOURCE": json.loads(paths["timelineControllerInput"].read_text()),
                            "PRACTICE_TIMELINE_CONTROLLER_SOURCE_SHA256": TIMELINE_SOURCE_SHA}.items():
            source += "\nglobalThis." + name + "=" + json.dumps(value, separators=(",", ":")) + ";\n"
    if candidate_index >= 7:
        source += "\nglobalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE=" + json.dumps(
            json.loads(paths["graphicOptionsInput"].read_text()), separators=(",", ":")) + ";\n"
        source += "\nglobalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE_SHA256=" + json.dumps(GRAPHIC_SOURCE_SHA) + ";\n"
    if candidate_index >= 15:
        source += "\nglobalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE=" + json.dumps(
            cutscene_binding, separators=(",", ":")) + ";\n"
        source += "\nglobalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256=" + json.dumps(CUTSCENE_SOURCE_SHA) + ";\n"
    if candidate_index >= 16:
        for name, value in original_overlay_runtime_values(paths).items():
            source += "\nglobalThis." + name + "=" + json.dumps(value, separators=(",", ":")) + ";\n"
    if "rngExpectedInput" in paths:
        source += "\nglobalThis.PRACTICE_RNG_EXPECTED=" + json.dumps(rng_expected, separators=(",", ":")) + ";\n"
        source += "\nglobalThis.PRACTICE_RNG_EXPECTED_SHA256=" + json.dumps(sha(paths["rngExpectedInput"])) + ";\n"
    result_filename = "practice" + suffix + ("-original-result.pb" if candidate_index >= 14 else "-original-result.json") if "packetSource" in paths else None
    if result_filename:
        if (GAME / result_filename).exists():
            raise FileExistsError("Original result output must be fresh")
        source += "\nglobalThis.PRACTICE_RESULT_FILENAME=" + json.dumps(result_filename) + ";\n"
    module_names = ("settingsSource", "reconstructionSource", "fixtureSource", "waveSource", "callbackSource",
                    "modeSource", "geometrySource", "aimSource", "schedulerSource", "resultSource", "tickSource",
                    "audioSource", "monsterSource", "fxSource")
    module_names += (("packetSource",) if "packetSource" in paths else ()) + ("probeSource",)
    if "skillPoolObserverSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("skillPoolObserverSource", "probeSource")
    if "skeletonObserverSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("skeletonObserverSource", "probeSource")
    if "skeletonSourceObserverSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("skeletonSourceObserverSource", "probeSource")
    if "dpRegistrationSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("dpRegistrationSource", "probeSource")
    if "monsterColorReadinessSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("monsterColorReadinessSource", "probeSource")
    if "autoPreferencesSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("autoPreferencesSource", "probeSource")
    if "rngStateVerifierSource" in paths:
        module_names = tuple(name for name in module_names if name != "probeSource") + ("rngStateVerifierSource", "probeSource")
    if "overlaySource" in paths:
        module_names = original_overlay_module_order(module_names)
    if "localeSource" in paths:
        module_names = original_locale_module_order(module_names)
    for name in module_names:
        source += "\n" + paths[name].read_text()
    if candidate_index >= 9 and ("installPracticeSkeletonSetupObserver" in source or "Skeleton diagnostic requires the existing evidence sink" in source):
        raise ValueError("Unsafe exception-helper observer remains in executable candidate")
    if candidate_index >= 12 and "installMechanicsMonsterHeadless" in source:
        raise ValueError("Removed monster color adapter remains in executable candidate")
    if "__TABLE_ARCHIVE__" in source or "__SCRATCH_PROFILE__" in source:
        raise ValueError("Native source path placeholder remains")
    sys.path.insert(0, str(ROOT / "event-selector/chainsaw-man/catalog-repair/hook-testing"))
    from build_bundle import parse, DELIMITER
    headers, modules = parse(HOOK.read_bytes())
    dependencies = modules[2:]
    modules[0] = json.dumps({"version": 3, "file": "nmm_030.js", "sources": [], "names": [], "mappings": ""}, separators=(",", ":")).encode()
    modules[1] = source.encode()
    headers[1], headers[2] = f"{len(modules[0])} /src/nmm_030.js.map", f"{len(modules[1])} /src/nmm_030.js"
    for name in ("scene-events.jsonl", "headless-bootstrap.log", "offline-network.log"):
        current, archived = GAME / name, package_predecessor / name
        if current.exists():
            if not archived.is_file() or sha(current) != sha(archived):
                raise ValueError("Preserve previous native log before clearing " + name)
            current.unlink()
    (GAME / "NKAB/dist/scene-probe.js").write_bytes("\n".join(headers).encode()+DELIMITER+DELIMITER.join(modules))
    check_headers, check_modules = parse((GAME / "NKAB/dist/scene-probe.js").read_bytes())
    if check_headers != headers or check_modules[2:] != dependencies:
        raise ValueError("Frozen Frida dependencies changed")
    source_path = SANDBOX / ("practice" + suffix + "-source.js")
    with source_path.open("x", encoding="utf-8") as sink:
        sink.write(source)
    config = json.loads((SANDBOX / "sandbox-table-bootstrap1.json").read_text())
    config["output_dir"] = str(SANDBOX / ("practice-output" + suffix))
    for item in config["diagnostic_files"].values():
        item["sha256"] = sha(Path(item["path"]))
    with config_path.open("x", encoding="utf-8") as sink:
        json.dump(config, sink, indent=2)
    spec = importlib.util.spec_from_file_location("practice153_host", ROOT / "tools/raid-lab/native_player_host.py")
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    plan = host.validate(config_path)
    with (SANDBOX / ("practice-plan" + suffix + ".json")).open("x", encoding="utf-8") as sink:
        json.dump(plan, sink, indent=2)
    staging = {"schemaVersion": 1, "planSha256": plan["plan_sha256"],
        "sources": {name: {"path": str(path), "sha256": sha(path)} for name, path in paths.items()},
        "resourceReceipts": {name: {"path": str(path), "sha256": sha(path)} for name, path in resources.items()},
        "resourceReadback": resource_check, "captureSha256": actual_input["captureSha256"],
        "sourceSha256": sha(source_path), "moduleOrder": list(module_names),
        "reviewedChangedSourceHashes": reviewed, "changedPriorSourceInputs": changed_sources,
        "removedPriorSourceInputs": removed_sources, "failedDiagnosticPredecessorAcknowledgement": failed_predecessor_ack,
        "auxiliarySourcePredecessorAcknowledgement": auxiliary_predecessor_ack,
        "normalFailedPredecessorAcknowledgement": normal_failed_predecessor_ack,
        "lastActualNativeArchive": str(previous), "sourcePredecessorArchive": str(predecessor),
        "originalResultFilename": result_filename,
        "originalResultFormat": "protobuf_wire" if candidate_index >= 14 else "native_diagnostic_json",
        "independentManagedPacketDecodeRequired": candidate_index >= 14,
        "fullSharedRngStateRequired": candidate_index >= 15,
        "autoPreferenceControlPlan": {"inputScope": "Explicit original two private preference inputs; current full-auto behavior, not raw historical captured preferences",
            "normalRegistryWritesAllowed": False, "preWitnessRequiredBeforeLaunch": True,
            "postWitnessRequiredAfterExit": True, "witnessHelperSourceSha256": sha(paths.get("autoPreferencesContinuityWitnessSource", paths["autoPreferencesWitnessSource"])),
            "witnessHelperPath": str(paths.get("autoPreferencesContinuityWitnessSource", paths["autoPreferencesWitnessSource"])),
            "preWitnessPath": str(SANDBOX / ("practice" + suffix + "-auto-preferences-pre.json")),
            "postWitnessPath": str(SANDBOX / ("practice" + suffix + "-auto-preferences-post.json")),
            "precondition": "Established private1/1 and unchanged normal1/1 from main11 post witness" if "autoPreferencesContinuityWitnessSource" in paths else "Normal1/1 and private absent before first input trial",
            "continuityBaselinePostSha256": sha(paths["autoPreferencesEstablishedPostWitness"]) if "autoPreferencesEstablishedPostWitness" in paths else None,
            "originalGetIntExpected": {"SpotAutoAimMode": 1, "SpotAutoSkillMode": 1},
            "directTeamFlagOrCounterWritesAllowed": False, "contentsOpenGateOverrideAllowed": False,
            "originalDataContextInitializationPreserved": True,
            "originalGateAndPlayingFlagReadbackRequired": True} if "autoPreferencesWitnessSource" in paths else None,
        "expectedReadbacksUsedOnlyAfterNativeConversion": True,
        "packageDependenciesPreserved": True, "legacyInterceptDriverIncluded": False,
        "scope": "Originalcurrent153capturednormalFireShort90s;stopfirstfailure;privatehostcallbacksandboundedpresentationadaptations",
        "driverDeadlineMs": 50000, "hostMaxSeconds": plan["max_seconds"],
        "originalUiCallbacksReplayed": False, "nativeRunPerformed": False,
        "fullAccuracyVerified": False, "productionIntegrated": False}
    if selection is not None:
        staging["matchedReferenceSelection"] = {"referenceRunIndex": reference_run,
            "proofPath": str(paths["referenceSelectionProof"]), "proofSha256": selection["sha256"],
            "proof": selection["proof"], "historicalInputSwitch": reference_change_proof}
    with (SANDBOX / ("practice-staging" + suffix + ".json")).open("x", encoding="utf-8") as sink:
        json.dump(staging, sink, indent=2)
    print(json.dumps({"config": str(config_path), "planSha256": plan["plan_sha256"], "launched": False,
                      "sourceSha256": sha(source_path), "moduleCount": len(module_names), "resourceReadback": resource_check}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-index", type=int, default=1)
    parser.add_argument("--reference-run", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--additional-resource", type=Path, action="append", default=[])
    parser.add_argument("--reviewed-source-change", action="append", default=[], metavar="NAME=SHA256")
    parser.add_argument("--last-native-index", type=int)
    parser.add_argument("--staged-predecessor-index", type=int)
    parser.add_argument("--failed-diagnostic-predecessor-sha256")
    parser.add_argument("--auxiliary-source-predecessor", type=Path)
    args = parser.parse_args()
    main(args.candidate_index, args.additional_resource, args.reviewed_source_change,
         args.last_native_index, args.staged_predecessor_index, args.failed_diagnostic_predecessor_sha256,
         args.auxiliary_source_predecessor, args.reference_run)

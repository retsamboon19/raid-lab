"""Select immutable original references1/2/3 and their own RNG readback proof.

No extraction output is written, no raw Obscured payload is normalized, and no
expected RNG value is applied to native state. This does not authorize a run.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay-input"
CAPTURE = HERE.parent / "capture/prebattle-live-44944/prebattle-events.jsonl"
METADATA = HERE.parent / "metadata/current153-run3/mechanics-metadata.json"
CAPTURE_SHA = "634ab51506bd28c10f4c229a6b0c1baabe0aa757f1c3611ca5142dcff936d82d"
CLIENT = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"
SEEDS = {1: 555063220, 2: 1168227811, 3: 1892208568}
KEYS = ("originalInput", "expectedReadbacks", "fixtureInput", "modeInput", "rngExpectedInput")
HASHES = {
    1: ("ee9cdb419bce429c7141b891a283ccab09414f08ca5eaf6c2ec6b5698338184b", "026f246d692854f0167393ac6b2e261bdcb4c76961f43ed5e13a9d8b88b56f43", "9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7", "fe2e44567bcbe6256ff431f35171abfcfb9c09503379644e8a31ba8f5033b37d", "214742a251316375b8b2e3527d97df9150ee2039238fc3042ed358cb5183bb55"),
    2: ("c30590b8e616f76da7d5ad05583aad0dc18c861d82ff9df7ca7d10c7ef7ba9f7", "aa0c63c1f48e6d7cdc0194e11c1b269049431130b941e3cfb0b26bb8eef37327", "a788e56a293be3e5a07a3cd87b2b40a9b626add089411b6b5eb7ec15c579aca5", "a3437b1046aa71f2e0b74a2a3a0f8c94525ee1682681a03e348ec4f684d02c62", "4257d7add5e7dc7c7e4dfd058b5a01ca18da0d774628e7bb365e3c9cdaaeb03a"),
    3: ("d51fc096dc01c935bad64b3d3c3a4d53b0f8a26b2563be0fdf74f0ab5c43503c", "afc6a3687852bbfd5f7fb73cd11c088e1a4f788318818605305d84f5cbbe0bff", "4c22f38dfd5e6efe5fe99576a7c89fc2c1354b5ba815b17dcbb76033b355b1d0", "0a3081786fd58cca40d52718f0e7f64803245aecbe2315c83dda70c3f9237962", "cf35319df594e84fbf7943d59df627d5072e5b28d52c798c25c31ccff5b82807"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same(left, right):
    # JSON comparison keeps Boolean and integer types distinct.
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def producer_lf_sha(fixture):
    """Exact existing producer representation; never rewrite the stored file."""
    return hashlib.sha256((json.dumps(fixture, indent=2) + "\n").encode("utf-8")).hexdigest()


def validate_semantics(run, fixture, mode, expected, source_phases, fixture_sha):
    if type(run) is not int or run not in SEEDS:
        raise ValueError("Only original reference indices1/2/3 are supported")
    if not same(fixture.get("runIndex"), run) or fixture.get("clientSha256") != CLIENT or fixture.get("captureSha256") != CAPTURE_SHA:
        raise ValueError("Original fixture run/client/capture differs")
    wanted = {"rangeId": 1, "waveId": 6801001, "processType": 9, "transporterProcessType": 0,
              "managementType": 0, "teamNumber": 0, "timeLimit": 90, "teamType": 24, "specActive": False,
              "randomSeed": SEEDS[run], "captureSourceSha256": CAPTURE_SHA,
              "inputSourceSha256": fixture_sha if run == 1 else producer_lf_sha(fixture)}
    if any(not same(mode.get(key), value) for key, value in wanted.items()) or not same(mode.get("referenceRunIndex", 1), run):
        raise ValueError("Original mode/fixture seed or encounter binding differs")
    if "sourceOnStart" in mode and not same(mode["sourceOnStart"], fixture["sourceOnStart"]):
        raise ValueError("Mode and fixture original OnStart anchors differ")
    seeds = [field for field in fixture["fields"] if field["name"] == "<RandomSeed>k__BackingField"]
    if len(seeds) != 1 or seeds[0].get("kind") != "int32" or not same(seeds[0].get("value"), SEEDS[run]):
        raise ValueError("Original semantic transporter seed differs")
    headers = {"schemaVersion": 1, "clientSha256": CLIENT, "captureSha256": CAPTURE_SHA,
               "referenceRunIndex": run, "boundary": "NK.Spot.SpotManagement::OnStart", "methodRva": 0x076064C0,
               "all56ElementsCaptured": True, "enterAndLeaveExactlyEqual": True, "rngPathCaptureErrors": [],
               "originalCaptureRewritten": False, "rngValuesCalculatedOrAdvanced": False, "nativeRngStateWritesAllowed": False}
    if any(not same(expected.get(key), value) for key, value in headers.items()) or not same(expected.get("phases"), source_phases):
        raise ValueError("Complete original RNG state/anchors differ from captured source")
    if not same(source_phases["enter"]["state"], source_phases["leave"]["state"]):
        raise ValueError("Original OnStart entry/leave RNG states differ")
    for phase in ("enter", "leave"):
        state = source_phases[phase]["state"]
        if not same(state["seed"], SEEDS[run]) or state["drawCount"] != "1" or len(state["seedArray"]) != 56 or any(type(x) is not int for x in state["seedArray"]):
            raise ValueError("All56 original shared state values and exact counter required")
    start = source_phases["enter"]["source"]
    if not same(fixture["sourceOnStart"], {key: start[key] for key in ("sequence", "sha256")}):
        raise ValueError("Fixture and full RNG proof refer to different original OnStart rows")


def select_reference(run):
    """Return (Path mapping, source proof). Read-only; no stager integration."""
    if type(run) is not int or run not in SEEDS:
        raise ValueError("Only original reference indices1/2/3 are supported")
    if sha(CAPTURE) != CAPTURE_SHA:
        raise ValueError("Original three-reference capture changed")
    matched = load(HERE / "matched_reference_inputs153.py", "selected_reference_validator153")
    folder = REPLAY / ("run" + str(run))
    paths = {"originalInput": folder / "native-replay-input.json", "expectedReadbacks": folder / "native-conversion-expected.json",
             "fixtureInput": folder / "native-fixture-input.json",
             "modeInput": HERE / "practice-mode-input.json" if run == 1 else folder / "practice-mode-input.json",
             "rngExpectedInput": HERE / "rng-state/expected1" / ("run" + str(run) + "-onstart-shared-rng.json")}
    for key, digest in zip(KEYS, HASHES[run]):
        if sha(paths[key]) != digest:
            raise ValueError("Immutable original reference bytes differ: " + key)
    extractor = matched.load_extractors()
    if run in (2, 3):
        checked, _ = matched.validate(run)
        if any(Path(checked[key]).resolve() != paths[key].resolve() for key in KEYS[:4]):
            raise ValueError("Existing matched validator selected another run/path")
        paths.update(checked)
    else:
        original, conversion = extractor.snapshots.extract(CAPTURE, 1)
        fixture = extractor.extract(CAPTURE, METADATA, 1)
        for key, fresh in (("originalInput", original), ("expectedReadbacks", conversion), ("fixtureInput", fixture)):
            if not same(read(paths[key]), fresh):
                raise ValueError("Frozen original run1 source extraction differs: " + key)
    graphs = extractor.g
    groups, incomplete = graphs.read_capture(CAPTURE)
    if incomplete or len(groups) != 3:
        raise ValueError("Complete original three-reference groups required")
    rng_source = HERE / "rng-state/extract_expected_states.py"
    rng = load(rng_source, "selected_original_shared_rng153")
    phases = {}
    for phase in ("enter", "leave"):
        rows = [row for row in groups[run - 1] if row["boundary"] == "NK.Spot.SpotManagement::OnStart@0x76064c0" and row["phase"] == phase]
        if len(rows) != 1:
            raise ValueError("Unique original OnStart entry/leave required")
        phases[phase] = rng.extract(rows[0], graphs)
    expected = read(paths["rngExpectedInput"])
    if expected["extractorSourceSha256"] != sha(rng_source) or expected["sourceMetadataSha256"] != sha(METADATA):
        raise ValueError("Original RNG extractor/metadata source differs")
    validate_semantics(run, read(paths["fixtureInput"]), read(paths["modeInput"]), expected, phases, sha(paths["fixtureInput"]))
    paths["referenceSelectionSource"] = Path(__file__).resolve()
    paths["referenceRngExtractorSource"] = rng_source
    proof = {"schemaVersion": 1, "referenceRunIndex": run, "actualCapturedSeed": SEEDS[run],
             "capturePath": str(CAPTURE), "captureSha256": CAPTURE_SHA, "clientSha256": CLIENT,
             "files": {key: {"path": str(path), "sha256": sha(path)} for key, path in paths.items()},
             "fixtureHashContract": {"artifactSha256": sha(paths["fixtureInput"]),
                 "originalProducerLfSha256": producer_lf_sha(read(paths["fixtureInput"])),
                 "modeInputSourceSha256": read(paths["modeInput"])["inputSourceSha256"],
                 "modeHashRepresentation": "artifact_bytes" if run == 1 else "existing_producer_indent2_json_plus_LF_utf8",
                 "artifactBytesRewritten": False, "producerRepresentationUsedOnlyForHashValidation": True},
             "sourceOnStart": read(paths["fixtureInput"])["sourceOnStart"],
             "fullSharedRngAnchors": {phase: phases[phase]["source"] for phase in phases},
             "all56ElementsComparedAtEachOriginalBoundary": True, "ownRunRawObscuredPayloadBytesPreserved": True,
             "expectedConversionReadbacksKeptSeparate": True, "rngExpectedIsReadbackOnly": True,
             "rngStateWritten": False, "rngMethodsInvoked": False, "nativeRunPerformed": False,
             "inputBindingReady": True, "nativeStartupAndBattleValidated": False,
             "nativeFreezeReady": False, "stagerIntegrationPerformed": False}
    return paths, proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, choices=(1, 2, 3), required=True)
    args = parser.parse_args()
    print(json.dumps(select_reference(args.run)[1], indent=2))

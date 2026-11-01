"""Prepare/validate source-bound reference2/3 inputs; no native execution."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPLAY = HERE / "replay-input"
CAPTURE = HERE.parent / "capture/prebattle-live-44944/prebattle-events.jsonl"
CAPTURE_SHA = "634ab51506bd28c10f4c229a6b0c1baabe0aa757f1c3611ca5142dcff936d82d"
METADATA = HERE.parent / "metadata/current153-run3/mechanics-metadata.json"
CLIENT = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_extractors():
    spec = importlib.util.spec_from_file_location("matched_original_fixture_extractor153", REPLAY / "extract_fixture_input.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def produce(run):
    if run not in (2, 3) or sha(CAPTURE) != CAPTURE_SHA:
        raise ValueError("Exact completed original capture/run2 or3 required")
    extractor = load_extractors()
    base_input, base_expected = extractor.snapshots.extract(CAPTURE, 1)
    base_fixture = extractor.extract(CAPTURE, METADATA, 1)
    for name, value in (("native-replay-input.json", base_input), ("native-conversion-expected.json", base_expected),
                        ("native-fixture-input.json", base_fixture)):
        if json.loads((REPLAY / "run1" / name).read_text()) != value:
            raise ValueError("Existing original run1 extraction no longer reproduces frozen inputs")
    original, expected = extractor.snapshots.extract(CAPTURE, run)
    fixture = extractor.extract(CAPTURE, METADATA, run)
    field_differences = [a["name"] for a, b in zip(base_fixture["fields"], fixture["fields"]) if a != b]
    if field_differences != ["<RandomSeed>k__BackingField"] or len(fixture["fields"]) != 61:
        raise ValueError("Reference encounter has unexpected semantic transporter difference")
    source_differences = []
    for before, after, before_result, after_result in zip(base_input["characters"], original["characters"], base_expected["characters"], expected["characters"]):
        changed = [key for key in before if before[key] != after[key]]
        if changed != ["levelObscuredIntRawHex", "characterStatDataRawHex", "sourceRow"] or \
           before_result["nativeConversion"] != after_result["nativeConversion"]:
            raise ValueError("Original converted build equality or per-run raw-payload differences changed")
        source_differences.append({"slot": after["slot"], "sourceCsn": after["sourceCsn"], "changedInputFields": changed,
                                   "independentNativeConversionExactlyEqual": True,
                                   "ownRunRawObscuredPayloadsUsed": True})
    seed = next(f for f in fixture["fields"] if f["name"] == "<RandomSeed>k__BackingField")
    if seed["kind"] != "int32" or seed["value"] != original["nativeEncounterReferenceOnly"]["seed"] or \
       seed["value"] != {2: 1168227811, 3: 1892208568}[run] or not seed["setter"]:
        raise ValueError("Actual original seed field/setter identity differs")
    groups, incomplete = extractor.g.read_capture(CAPTURE)
    if incomplete:
        raise ValueError("Complete reference capture required")
    settings = json.loads((HERE / "practice-settings-input.json").read_text())
    settings_proof, seed_boundaries = [], []
    for index, group in enumerate(groups, 1):
        for row in group:
            if row["phase"] != "enter" or not any(name in row["boundary"] for name in ("::OnInit@", "::OnStart@")):
                continue
            actual = row["value"]["settings"]
            for name, size in (("GameSetting", 100), ("ControlSetting", 24), ("VideoSetting", 36)):
                if actual[name]["$valueSize"] != size or actual[name] != settings["settings"][name]:
                    raise ValueError("Shared captured settings are not exactly equal at every original boundary")
            anchor = {"runIndex": index, "sequence": row["sequence"], "sha256": row["completeLineSha256"], "boundary": row["boundary"]}
            settings_proof.append(anchor)
            if index == run:
                graph = extractor.g.Graph(row["value"])
                boundary_seed = graph.f(row["value"]["transporter"], "<RandomSeed>k__BackingField")
                expected_boundary_seed = seed["value"] if "::OnStart@" in row["boundary"] else 0
                if boundary_seed != expected_boundary_seed:
                    raise ValueError("Actual original zero-OnInit/nonzero-OnStart seed contract differs")
                seed_boundaries.append({**anchor, "seed": boundary_seed})
    if len(settings_proof) != 6 or len(seed_boundaries) != 2:
        raise ValueError("All original OnInit/OnStart boundary anchors required")
    mode = copy.deepcopy(json.loads((HERE / "practice-mode-input.json").read_text()))
    mode.update({"randomSeed": seed["value"], "referenceRunIndex": run,
                 "sourceOnStart": fixture["sourceOnStart"], "captureSourceSha256": CAPTURE_SHA})
    values = {"native-replay-input.json": original, "native-conversion-expected.json": expected,
              "native-fixture-input.json": fixture}
    fixture_bytes = (json.dumps(fixture, indent=2) + "\n").encode()
    mode["inputSourceSha256"] = hashlib.sha256(fixture_bytes).hexdigest()
    values["practice-mode-input.json"] = mode
    proof = {"schemaVersion": 1, "scope": "Matched original reference input provenance/equality only; no native execution",
             "clientSha256": CLIENT, "capturePath": str(CAPTURE), "captureSha256": CAPTURE_SHA, "referenceRunIndex": run,
             "sourceOnStart": fixture["sourceOnStart"], "actualCapturedSeed": seed["value"], "seedBoundaryAnchors": seed_boundaries,
             "sourceExtraction": {name: {"path": str(path), "sha256": sha(path)} for name, path in {
                 "snapshotExtractor": REPLAY / "extract_snapshot_inputs.py", "fixtureExtractor": REPLAY / "extract_fixture_input.py",
                 "sourceGraphReader": HERE.parent / "results/compare_references.py", "transporterMetadata": METADATA,
                 "preparationAndValidationSource": Path(__file__).resolve()}.items()},
             "run1InputsReproducedExactly": True, "perUnitInputEquality": source_differences,
             "semanticTransporterFieldCount": 61, "semanticTransporterFieldsChangedFromRun1": field_differences,
             "originalSeedInput": {"field": seed["name"], "value": seed["value"], "nativeFieldOffset": seed["offset"],
                                   "setterName": seed["setter"]["name"], "setterRva": seed["setter"]["nativeRva"],
                                   "path": "Captured JSON -> original transporter set_RandomSeed -> original static install -> original manager lifecycle",
                                   "liveRngOrManagerFieldsForced": False},
             "unresolvedInitializationTiming": {"referenceTransporterSeedAtOnInitEntry": 0,
                 "referenceTransporterSeedAtOnStartEntry": seed["value"],
                 "existingHostFixtureSourceBoundary": "OnStart",
                 "existingHostInstallsCapturedNonzeroSeedBeforeOnInit": True,
                 "referenceSharedRngDrawCountAtOnStart": 1, "native14SharedRngDrawCountAtFirstPlaying": 0,
                 "originalMissingDrawPathAuditPending": True, "directRngStateCountWritesAllowed": False,
                 "nativeFreezeReady": False},
             "sharedSettings": {"path": str(HERE / "practice-settings-input.json"), "sha256": sha(HERE / "practice-settings-input.json"),
                                "allSixOriginalBoundariesExactlyEqual": True, "sourceAnchors": settings_proof},
             "settingsWaveDurationBuildAndClockBehaviorChanged": False,
             "historicalNativeOnStartTimingReplayed": False, "nativeFrameScheduleCaptured": False,
             "expectedConversionValuesKeptSeparateFromInputs": True,
             "nativeBattleOutputsAppliedAsInputs": False, "nativeRunPerformed": False}
    return values, proof


def validate(run):
    values, proof = produce(run)
    folder = REPLAY / ("run" + str(run))
    stored = json.loads((folder / "matched-reference-provenance.json").read_text())
    for name, value in values.items():
        if json.loads((folder / name).read_text()) != value:
            raise ValueError("Fresh original reference input differs from source extraction: " + name)
    expected_files = {name: {"path": str(folder / name), "sha256": sha(folder / name)} for name in values}
    if stored != {**proof, "files": expected_files}:
        raise ValueError("Matched reference provenance/equality receipt differs")
    return {"originalInput": folder / "native-replay-input.json", "expectedReadbacks": folder / "native-conversion-expected.json",
            "fixtureInput": folder / "native-fixture-input.json", "modeInput": folder / "practice-mode-input.json",
            "matchedReferenceProvenance": folder / "matched-reference-provenance.json",
            "matchedReferenceInputSource": Path(__file__).resolve(),
            "matchedReferenceSnapshotExtractor": REPLAY / "extract_snapshot_inputs.py",
            "matchedReferenceFixtureExtractor": REPLAY / "extract_fixture_input.py"}, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", type=int, choices=(2, 3), required=True)
    args = parser.parse_args()
    if args.prepare:
        values, proof = produce(args.run)
        folder = REPLAY / ("run" + str(args.run))
        folder.mkdir(exist_ok=False)
        for name, value in values.items():
            with (folder / name).open("x", encoding="utf-8") as sink:
                json.dump(value, sink, indent=2); sink.write("\n")
        proof["files"] = {name: {"path": str(folder / name), "sha256": sha(folder / name)} for name in values}
        with (folder / "matched-reference-provenance.json").open("x", encoding="utf-8") as sink:
            json.dump(proof, sink, indent=2); sink.write("\n")
    paths, proof = validate(args.run)
    print(json.dumps({"status": "passed", "referenceRun": args.run, "actualCapturedSeed": proof["actualCapturedSeed"],
                      "sourceOnStart": proof["sourceOnStart"], "provenanceSha256": sha(paths["matchedReferenceProvenance"]),
                      "nativeRunPerformed": False}))


if __name__ == "__main__":
    main()

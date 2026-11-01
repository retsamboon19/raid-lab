"""Extract complete original OnStart RNG states; no RNG calculation or native call."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
CAPTURE = NATIVE.parent / "capture/prebattle-live-44944/prebattle-events.jsonl"
METADATA = NATIVE.parent / "metadata/current153-run3/mechanics-metadata.json"
CAPTURE_SHA = "634ab51506bd28c10f4c229a6b0c1baabe0aa757f1c3611ca5142dcff936d82d"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(row, graphs):
    related = [error for error in row["errors"] if error["path"].startswith("spotRandom")]
    if related:
        raise ValueError("Original RNG subtree has capture errors")
    graph = graphs.Graph(row["value"])
    shared = graph.ref(row["value"]["spotRandom"])
    random = graph.ref(graph.f(shared, "<Random>k__BackingField"))
    array = graph.ref(graph.f(random, "_seedArray"))
    if shared["$type"] != "NK.Spot.Common.SpotRandom" or random["$type"] != "System.Random" or \
       array["$type"] != "System.Int32[]" or array["length"] != 56:
        raise ValueError("Exact original RNG types/full56-element array required")
    values = graph.items(array)
    if len(values) != 56 or any(type(value) is not int or not -(2 ** 31) <= value < 2 ** 31 for value in values):
        raise ValueError("All56 original Int32 elements required")
    state = {"seed": graph.f(shared, "_currSeed"), "drawCount": str(graphs.scalar(graph.f(shared, "<DrawCount>k__BackingField"))),
             "inext": graph.f(random, "_inext"), "inextp": graph.f(random, "_inextp"), "seedArray": values}
    if any(type(state[key]) is not int for key in ("seed", "inext", "inextp")) or not state["drawCount"].isdigit():
        raise ValueError("Exact original seed/count/indices required")
    return {"source": {"sequence": row["sequence"], "sha256": row["completeLineSha256"],
                       "boundary": row["boundary"], "phase": row["phase"], "rngPathCaptureErrors": related,
                       "unrelatedOtherGraphErrorCount": len(row["errors"])}, "state": state}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    if sha(CAPTURE) != CAPTURE_SHA:
        raise ValueError("Exact final original capture differs")
    spec = importlib.util.spec_from_file_location("rng_source_graphs153", NATIVE.parent / "results/compare_references.py")
    graphs = importlib.util.module_from_spec(spec); spec.loader.exec_module(graphs)
    groups, incomplete = graphs.read_capture(CAPTURE)
    if incomplete or len(groups) != 3:
        raise ValueError("All3 original completed capture groups required")
    rows = []
    for run, group in enumerate(groups, 1):
        phases = {}
        for phase in ("enter", "leave"):
            selected = [row for row in group if row["boundary"] == "NK.Spot.SpotManagement::OnStart@0x76064c0" and row["phase"] == phase]
            if len(selected) != 1:
                raise ValueError("Unique original OnStart enter/leave required")
            phases[phase] = extract(selected[0], graphs)
        if phases["enter"]["state"] != phases["leave"]["state"]:
            raise ValueError("OnStart changes original RNG state; phase-specific handling needs review")
        rows.append({"schemaVersion": 1, "clientSha256": "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2",
                     "capturePath": str(CAPTURE), "captureSha256": CAPTURE_SHA, "sourceMetadataSha256": sha(METADATA),
                     "referenceRunIndex": run, "boundary": "NK.Spot.SpotManagement::OnStart", "methodRva": 0x076064C0,
                     "scope": "Complete original shared RNG expected readback only; never an RNG state input",
                     "phases": phases, "enterAndLeaveExactlyEqual": True, "all56ElementsCaptured": True,
                     "rngPathCaptureErrors": [], "originalCaptureRewritten": False,
                     "rngValuesCalculatedOrAdvanced": False, "nativeRngStateWritesAllowed": False,
                     "extractorSourceSha256": sha(Path(__file__).resolve())})
    args.output_directory.mkdir(exist_ok=False)
    for run, row in enumerate(rows, 1):
        path = args.output_directory / ("run" + str(run) + "-onstart-shared-rng.json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(row, stream, indent=2); stream.write("\n")
        print(json.dumps({"run": run, "path": str(path), "sha256": sha(path),
                          "seed": row["phases"]["enter"]["state"]["seed"], "drawCount": row["phases"]["enter"]["state"]["drawCount"]}))


if __name__ == "__main__":
    main()


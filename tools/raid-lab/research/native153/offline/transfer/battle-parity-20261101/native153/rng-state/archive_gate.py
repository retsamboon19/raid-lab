"""Require exact same-boundary full RNG evidence; this module reads JSON only."""
import re


def valid_state(state):
    return isinstance(state, dict) and type(state.get("seed")) is int and -(2 ** 31) <= state["seed"] < 2 ** 31 and \
        isinstance(state.get("drawCount"), str) and re.fullmatch(r"0|[1-9][0-9]{0,18}", state["drawCount"]) is not None and \
        int(state["drawCount"]) <= 9223372036854775807 and \
        all(type(state.get(key)) is int and 0 <= state[key] < 56 for key in ("inext", "inextp")) and \
        isinstance(state.get("seedArray"), list) and len(state["seedArray"]) == 56 and \
        all(type(value) is int and -(2 ** 31) <= value < 2 ** 31 for value in state["seedArray"])


def verify(rows, terminal, expected, expected_sha):
    errors = []
    observations = [row for row in rows if row.get("status") == "original_practice_full_shared_rng_observed"]
    read_errors = [row for row in rows if row.get("status") == "original_practice_full_shared_rng_read_failed"]
    if read_errors:
        errors.append("Full RNG boundary read failure retained")
    if len(observations) != 2:
        errors.append("Exactly one original OnStart entry and return observation required")
    if [row.get("boundaryPhase") for row in observations] != ["enter", "leave"]:
        errors.append("Original OnStart boundary observations must be ordered entry then return")
    snapshot = terminal.get("fullSharedRngState")
    if not isinstance(snapshot, dict):
        errors.append("Terminal full RNG verifier snapshot absent")
        snapshot = {}
    if snapshot.get("seen") != {"enter": True, "leave": True} or snapshot.get("fault") is not None or \
       snapshot.get("expectedFileSha256") != expected_sha or snapshot.get("referenceRunIndex") != expected["referenceRunIndex"] or \
       snapshot.get("comparedArrayElementsPerBoundary") != 56 or snapshot.get("rngStateWritten") is not False or \
       snapshot.get("rngMethodsInvoked") is not False or snapshot.get("typedArrayAccessorPrimedOutsideNativeHooks") is not True or \
       snapshot.get("helperInstallsHooks") is not False:
        errors.append("Terminal full RNG verifier completion/binding/no-mutation proof differs")
    for phase in ("enter", "leave"):
        selected = [row for row in observations if row.get("boundaryPhase") == phase]
        if len(selected) != 1:
            errors.append("Unique original OnStart " + phase + " proof absent")
            continue
        row = selected[0]; want = expected["phases"][phase]
        if row.get("passed") is not True or row.get("mismatchFields") != [] or row.get("mismatchArrayIndices") != [] or \
           row.get("comparedArrayElements") != 56 or row.get("expectedFileSha256") != expected_sha or \
           row.get("referenceRunIndex") != expected["referenceRunIndex"] or row.get("source") != want["source"] or \
           row.get("sameOriginalOnStartBoundary") is not True or row.get("rngStateWritten") is not False or \
           row.get("rngMethodsInvoked") is not False:
            errors.append("Original OnStart " + phase + " binding/comparison/no-mutation proof differs")
        if not valid_state(row.get("actual")) or not valid_state(want["state"]) or row.get("actual") != want["state"]:
            errors.append("Original OnStart " + phase + " seed/count/indices/full56 state differs")
    normalize = lambda row: {key: value for key, value in row.items() if key not in ("time", "phase", "fullAccuracyVerified")}
    if snapshot.get("observations") != [normalize(row) for row in observations]:
        errors.append("Terminal snapshot does not retain the same original boundary observations")
    return {"status": "failed" if errors else "passed", "required": True, "errors": errors,
            "expectedFileSha256": expected_sha, "referenceRunIndex": expected["referenceRunIndex"],
            "observedBoundaries": len(observations), "readFailures": read_errors,
            "all56ElementsComparedAtEachOriginalBoundary": not errors,
            "rngStateWritten": False, "rngMethodsInvoked": False}

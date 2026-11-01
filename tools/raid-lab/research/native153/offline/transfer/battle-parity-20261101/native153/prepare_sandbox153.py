"""Plan a fresh current153 private player; copying requires explicit --stage-client.

This tool never builds native helpers, creates a launch-ready receipt, launches a
process, or copies external patch stores/accounts. Its default path only lists
client file metadata. Run the copy batch after coordinating with live baselines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "NIKKE/NIKKE/game"
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
EXPECTED = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"
ROOT_FILES = ("nikke.exe", "UnityPlayer.dll", "GameAssembly.dll", "baselib.dll",
              "CrashSight64.dll", "GameBabyConfig64.dat", "libraries.txt",
              "d3d11.dll", "frida-gadget.dll")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_path(path, root):
    if not path.is_relative_to(root):
        raise ValueError("Source/destination escaped its exact root")
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink() or current.is_junction():
            raise ValueError("Source/destination traverses a link")


def inventory():
    files = [SOURCE / name for name in ROOT_FILES]
    # Actual client essentials only. Current plugins/builtins are retained;
    # startup installation/title movies do not affect the mechanics bootstrap.
    omitted_movies = []
    for path in (SOURCE / "nikke_Data").rglob("*"):
        check_path(path, SOURCE)
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE)
        if relative.parts[:2] == ("nikke_Data", "StreamingAssets") and path.suffix.lower() == ".mp4":
            omitted_movies.append({"relative": relative.as_posix(), "bytes": path.stat().st_size})
            continue
        files.append(path)
    rows = []
    for path in sorted(files):
        check_path(path, SOURCE)
        if not path.is_file():
            raise ValueError("Client essential missing: " + str(path))
        stat = path.stat()
        rows.append({"relative": path.relative_to(SOURCE).as_posix(), "bytes": stat.st_size,
                     "mtimeNs": stat.st_mtime_ns})
    return rows, omitted_movies


def plan():
    rows, movies = inventory()
    host_sources = [ROOT / "tools/raid-lab/native-player/HeadlessUnityEntry.cpp",
                    ROOT / "tools/raid-lab/native-player/OfflineNetwork.cpp",
                    ROOT / "tools/raid-lab/native_player_host.py"]
    return {"schemaVersion": 1, "source": str(SOURCE), "sandbox": str(SANDBOX),
            "clientSha256RequiredBeforeCopy": EXPECTED,
            "files": rows, "fileCount": len(rows), "bytes": sum(r["bytes"] for r in rows),
            "omittedStartupMovies": movies,
            "nativeSourceInputs": {str(path): sha(path) for path in host_sources},
            "copyPerformed": False, "nativeBuildPerformed": False, "gameLaunched": False,
            "requiresBeforeRun": ["Build153 headless/deny-all helpers from reviewed source",
                "Fresh deny-all self-test tied to new sandbox (not old149 receipt)",
                "Bind current153 migrated source bundle and exact current MPK archive",
                "Stage sparse exact shooting-range mechanical assets after actual range selection",
                "Bind copied client hashes plus source/asset/bootstrap/network receipts",
                "Validate host plan and explicit integration-ready receipt"]}


def stage(plan_path):
    approved = json.loads(plan_path.read_text())
    current = plan()
    for key in ("source", "sandbox", "clientSha256RequiredBeforeCopy", "files", "nativeSourceInputs"):
        if approved.get(key) != current[key]:
            raise ValueError("Planned source changed before copy: " + key)
    if sha(SOURCE / "GameAssembly.dll") != EXPECTED:
        raise ValueError("Installed153 GameAssembly differs")
    check_path(SANDBOX, ROOT / "tools/raid-lab/private")
    if SANDBOX.exists():
        raise FileExistsError("Preserve existing sandbox; fresh destination required")
    destination = SANDBOX / "NIKKE/NIKKE/game"
    destination.mkdir(parents=True)
    copied = []
    for row in current["files"]:
        source, target = SOURCE / row["relative"], destination / row["relative"]
        check_path(source, SOURCE)
        check_path(target, SANDBOX)
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = sha(source)
        shutil.copy2(source, target)
        if target.stat().st_nlink != 1 or sha(target) != expected:
            raise ValueError("Client copy/readback mismatch: " + row["relative"])
        copied.append(dict(row, sha256=expected))
    for name in ("AppData/Local", "AppData/LocalLow", "AppData/Roaming", "Temp"):
        (SANDBOX / "profile" / name).mkdir(parents=True)
    # These two reviewed startup inputs contain no player account/save. The
    # certificate is used solely in the guard's process-local in-memory store.
    startup = ((ROOT / "EpinelPS-runtime/myCA.pem", SANDBOX / "EpinelPS-runtime/myCA.pem"),
               (ROOT / "profile/offline-variants.json", SANDBOX / "profile/offline-variants.json"))
    startup_rows = []
    for source, target in startup:
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = sha(source)
        shutil.copy2(source, target)
        if sha(target) != expected:
            raise ValueError("Startup input readback mismatch")
        startup_rows.append({"source": str(source), "target": str(target), "sha256": expected})
    report = {"schemaVersion": 1, "clientSha256": EXPECTED, "files": copied,
              "startupInputs": startup_rows, "planSha256": sha(plan_path),
              "nativeHelpersPresent": False, "launchReady": False, "gameLaunched": False}
    (SANDBOX / "clone153-manifest.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"copiedFiles": len(copied), "sandbox": str(SANDBOX), "launchReady": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-output", type=Path)
    parser.add_argument("--stage-client", type=Path, metavar="REVIEWED_PLAN")
    args = parser.parse_args()
    if args.stage_client:
        stage(args.stage_client.resolve(strict=True))
    else:
        data = plan()
        if args.plan_output:
            with args.plan_output.open("x", encoding="utf-8") as sink:
                json.dump(data, sink, indent=2)
                sink.write("\n")
        print(json.dumps({"files": data["fileCount"], "bytes": data["bytes"],
                          "copyPerformed": False, "plan": str(args.plan_output) if args.plan_output else None}))

"""Build only this managed read-only decoder; freeze fresh synthetic control receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(receipt):
    if receipt.exists():
        raise FileExistsError("Preserve existing decoder receipt")
    dotnet = ROOT / "tools/dotnet/dotnet.exe"
    source = {name: HERE / name for name in ("Program.cs", "PacketDecoder.csproj", "build_and_check.py")}
    source_before = {name: {"path": str(path), "sha256": sha(path)} for name, path in source.items()}
    build = subprocess.run([str(dotnet), "build", str(HERE / "PacketDecoder.csproj"), "--configuration", "Release", "--no-restore", "--verbosity", "minimal"],
                           capture_output=True, text=True, timeout=45)
    if build.returncode:
        raise RuntimeError(build.stdout + build.stderr)
    binary = HERE / "bin/Release/net10.0"
    test = subprocess.run([str(dotnet), str(binary / "PacketDecoder.dll"), "--self-test"], capture_output=True, text=True, timeout=30)
    controls = json.loads(test.stdout) if test.returncode == 0 else None
    if test.returncode or not controls or controls["status"] != "passed":
        raise RuntimeError(test.stdout + test.stderr)
    if any(sha(source[name]) != item["sha256"] for name, item in source_before.items()):
        raise ValueError("Decoder source changed during build/controls")
    artifacts = {name: {"path": str(binary / name), "sha256": sha(binary / name)} for name in
                 ("PacketDecoder.dll", "PacketDecoder.runtimeconfig.json", "PacketDecoder.deps.json", "EpinelPS.dll", "Google.Protobuf.dll")}
    backend = ROOT / "EpinelPS/EpinelPS/bin/Release/net10.0/win-x64"
    for name in ("EpinelPS.dll", "Google.Protobuf.dll"):
        if artifacts[name]["sha256"] != sha(backend / name):
            raise ValueError("Exact current generated/protobuf assembly copy differs")
    report = {"schemaVersion": 1, "status": "passed", "scope": "Read-only decoder managed build and synthetic controls only; no native player/backend run",
              "sourceInputs": source_before, "artifacts": artifacts, "dotnet": {"path": str(dotnet), "sha256": sha(dotnet)},
              "commands": {"buildExitCode": build.returncode, "buildStdout": build.stdout, "testExitCode": test.returncode,
                           "testStdout": test.stdout}, "syntheticControls": controls, "nativeBattleRun": False,
              "backendRebuiltOrLaunched": False}
    with receipt.open("x", encoding="utf-8") as sink:
        json.dump(report, sink, indent=2)
        sink.write("\n")
    print(json.dumps({"status": "passed", "path": str(receipt), "sha256": sha(receipt), "syntheticAssertions": controls["assertions"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    main(parser.parse_args().receipt.resolve())

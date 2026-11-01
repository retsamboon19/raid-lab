"""Bind unchanged native wire bytes to an independent, exact managed decoder."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_build_receipt(receipt_path):
    receipt = json.loads(receipt_path.read_text())
    if receipt["status"] != "passed" or receipt["nativeBattleRun"] is not False or receipt["backendRebuiltOrLaunched"] is not False:
        raise ValueError("Exact decoder build/synthetic receipt required")
    expected_sources = {name: HERE / name for name in ("Program.cs", "PacketDecoder.csproj", "build_and_check.py")}
    expected_artifacts = {name: HERE / "bin/Release/net10.0" / name for name in
                          ("PacketDecoder.dll", "PacketDecoder.runtimeconfig.json", "PacketDecoder.deps.json", "EpinelPS.dll", "Google.Protobuf.dll")}
    for group, expected in (("sourceInputs", expected_sources), ("artifacts", expected_artifacts)):
        if set(receipt[group]) != set(expected):
            raise ValueError("Decoder receipt path inventory differs")
        for name, path in expected.items():
            item = receipt[group][name]
            if Path(item["path"]).resolve() != path.resolve() or sha(path) != item["sha256"]:
                raise ValueError("Frozen exact decoder source/artifact differs: " + name)
    dotnet = ROOT / "tools/dotnet/dotnet.exe"
    if Path(receipt["dotnet"]["path"]).resolve() != dotnet.resolve() or sha(dotnet) != receipt["dotnet"]["sha256"]:
        raise ValueError("Bound managed decoder runtime differs")
    return receipt


def validate_native_contract(terminal, mode, packet_length, packet_sha):
    source = terminal.get("originalPacketSource", {})
    native = terminal.get("originalAntiCheat", {})
    characters = mode["characters"]
    if terminal.get("completeBattle") is not True or terminal.get("originalPacketExported") is not True or \
       terminal.get("statisticsAndPacketCapturedBeforeCleanup") is not True or \
       source.get("format") != "protobuf_wire" or \
       type(source.get("byteLength")) is not int or source["byteLength"] != packet_length:
        raise ValueError("Completed original binary export/byte count proof required")
    digest = source.get("sha256")
    if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest) or digest != packet_sha):
        raise ValueError("Original binary export digest differs")
    if native.get("source") != "original_BattleResult_AntiCheatBattleDataInit" or \
       native.get("waveId") != mode["waveId"] or native.get("battleDuration") != mode["timeLimit"] * 1000 or \
       native.get("characterCount") != len(characters) or len(characters) != 5 or \
       type(native.get("monsterCount")) is not int or not 0 < native["monsterCount"] <= 100000:
        raise ValueError("Original typed DTO identity/count proof differs")
    tids = [item["tableId"] for item in characters]
    if any(type(tid) is not int or tid <= 0 for tid in tids) or len(set(tids)) != 5:
        raise ValueError("Captured five typed character identities required")
    return native, source, tids


def decode_archived_packet(packet_path, report_path, terminal, mode, build_receipt_path):
    if report_path.exists():
        raise FileExistsError("Preserve existing independent decode")
    if not 0 < packet_path.stat().st_size <= 16777216:
        raise ValueError("Original wire bytes exceed bounds")
    receipt = validate_build_receipt(build_receipt_path)
    before = sha(packet_path)
    native, source, tids = validate_native_contract(terminal, mode, packet_path.stat().st_size, before)
    command = [receipt["dotnet"]["path"], receipt["artifacts"]["PacketDecoder.dll"]["path"],
               "--input", str(packet_path), "--output", str(report_path),
               "--wave", str(mode["waveId"]), "--duration", str(mode["timeLimit"] * 1000),
               "--characters", str(len(tids)), "--monsters", str(native["monsterCount"]),
               "--tids", ",".join(map(str, tids)), "--native-byte-length", str(source["byteLength"])]
    if source.get("sha256") is not None:
        command += ["--native-sha256", source["sha256"]]
    process = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if process.returncode:
        raise ValueError("Independent wire decode failed: " + process.stdout + process.stderr)
    report = json.loads(report_path.read_text())
    if sha(packet_path) != before or report["status"] != "passed" or report["originalWire"]["sha256"] != before or \
       report["decoder"]["assemblySha256"] != receipt["artifacts"]["PacketDecoder.dll"]["sha256"] or \
       report["decoder"]["generatedTypesAssemblySha256"] != receipt["artifacts"]["EpinelPS.dll"]["sha256"] or \
       report["decoder"]["protobufAssemblySha256"] != receipt["artifacts"]["Google.Protobuf.dll"]["sha256"]:
        raise ValueError("Independent wire decode binding differs")
    # Recheck sources/binaries after execution; never rewrite raw original packet.
    validate_build_receipt(build_receipt_path)
    return {"status": "passed", "provenance": "Independent managed decode, not native JSON", "reportPath": str(report_path),
            "reportSha256": sha(report_path), "rawPacketSha256": before, "rawPacketByteLength": packet_path.stat().st_size,
            "decoderBuildReceiptSha256": sha(build_receipt_path), "nativeTypedReadback": native,
            "nativeExportSource": source, "typedReadback": report["typedReadback"], "rawBytesUnchanged": True,
            "fullKnownSchemaJsonIncluded": True, "allInt64AndUInt64AreStrings": True,
            "opaqueUnknownFieldsPreservedInRawArtifact": True, "byteIdenticalRoundTripRequired": False,
            "combatCalculationsPerformed": False}

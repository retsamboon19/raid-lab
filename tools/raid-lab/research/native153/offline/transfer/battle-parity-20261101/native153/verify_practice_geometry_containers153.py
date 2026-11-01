"""Verify all frozen geometry targets against original bundle container GUIDs."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools/raid-lab/private/native-python"))
import UnityPy
import zstandard


def main():
    receipt = HERE / "practice-geometry-source.json"
    output = HERE / "practice-geometry-container-proof.json"
    if output.exists():
        raise FileExistsError("Preserve original container proof")
    source = json.loads(receipt.read_text())
    clone = ROOT / "tools/raid-lab/private/native-player153-20261101"
    store = clone / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core/chunk/store.cdb"
    rows = []
    decoder = zstandard.ZstdDecompressor()
    with store.open("rb") as stream:
        for role, data in source["bundles"].items():
            verified = data["verified_bundle"]
            if verified["source"] == "patch_chunk_store":
                pieces = []
                for chunk in verified["chunks"]:
                    stream.seek(chunk["store_offset"])
                    packed = stream.read(chunk["compressed_bytes"])
                    if hashlib.sha256(packed).hexdigest() != chunk["compressed_sha256"]:
                        raise ValueError("Staged current geometry chunk differs")
                    pieces.append(decoder.decompress(packed))
                payload = b"".join(pieces)
            else:
                original = Path(verified["path"])
                staged = clone / "NIKKE/NIKKE/game" / original.relative_to(ROOT / "NIKKE/NIKKE/game")
                payload = staged.read_bytes()
            if hashlib.sha256(payload).hexdigest() != data["decoded_sha256"]:
                raise ValueError("Current frozen geometry bundle bytes differ")
            env = UnityPy.load(payload)
            objects = {obj.path_id: obj for obj in env.objects}
            internal = data["selected_asset"]["internal_id"]
            refs = [value["asset"] for obj in objects.values() if obj.type.name == "AssetBundle"
                    for key, value in obj.read_typetree()["m_Container"] if key == internal]
            if len(refs) != 1 or refs[0]["m_FileID"] != 0 or refs[0]["m_PathID"] not in objects:
                raise ValueError("Frozen current geometry internalId is not unique local target")
            target = objects[refs[0]["m_PathID"]]
            rows.append({"role": role, "internal_id": internal, "path_id": target.path_id,
                         "native_serialized_type": target.type.name,
                         "serialized_name": target.read_typetree().get("m_Name"), "passed": True})
    report = {"schemaVersion": 1, "status": "passed", "geometryReceiptSha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
              "checks": rows, "nativeLaunched": False, "battleStarted": False}
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": len(rows), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()

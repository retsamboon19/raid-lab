"""Stage exact current shared mechanical keys and serialized canvas references.

Fresh receipt only; adds verified original chunks to the separate sparse store.
This is the retained source of the successful shared-resource staging command.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
TARGET = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
KEYS = ["SpotCameraControl", "UIAimControll", "SpotCharacterMap", "AutoModeCameraControl", "UICanvasControl",
        "9022068b08512344181fc634755eff39", "ae0ee471e5e1d23458b6b485b5522b0f",
        "342d3a4ea95847344911914d0d1b0de1", "71e8cc9931c3ae7489afb1315a4e4c34"]
sys.path.insert(0, str(ROOT / "tools/raid-lab/private/native-python"))
sys.path.insert(0, str(ROOT / "tools/raid-lab/native-player"))
sys.path.insert(0, str(ROOT / "transfer"))
import UnityPy
import zstandard
from build_logged_bundle_evidence import database, key_bundles, verify_bundle
from chunk_index import decode_index


def main():
    receipt = SANDBOX / "shared-mechanical-resources1.json"
    if receipt.exists():
        raise FileExistsError("Preserve successful staging receipt; do not repeat unchanged resource reads")
    raw = database(CORE / "raw/6a46ed93faa7c6fd01f1aa66253becc7.db")
    patch = database(CORE / "catalog.ndb")
    index_bytes = (CORE / "chunk/store.cdb.idx").read_bytes()
    index = decode_index(index_bytes)
    entries, bundles = {}, set()
    for key in KEYS:
        rows, names = key_bundles(raw, key)
        entries[key] = rows
        bundles.update(names)
    store, decoder = CORE / "chunk/store.cdb", zstandard.ZstdDecompressor()
    verified, canvas_refs = {}, set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "m_AssetGUID" and isinstance(child, str) and child:
                    canvas_refs.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    with store.open("rb") as source:
        for name in sorted(bundles):
            verified[name] = verify_bundle(patch, index, name, store, source, decoder)
        canvas_bundle = next(iter(key_bundles(raw, "UICanvasControl")[1]))
        row, payload = verified[canvas_bundle], b""
        if row["source"] == "patch_chunk_store":
            for chunk in row["chunks"]:
                source.seek(chunk["store_offset"])
                payload += decoder.decompress(source.read(chunk["compressed_bytes"]))
        else:
            payload = Path(row["path"]).read_bytes()
        for obj in UnityPy.load(payload).objects:
            if obj.type.name == "MonoBehaviour":
                walk(obj.read_typetree())
        for key in sorted(canvas_refs):
            rows, names = key_bundles(raw, key)
            entries[key] = rows
            for name in names:
                if name not in verified:
                    verified[name] = verify_bundle(patch, index, name, store, source, decoder)
        chunks = {chunk["store_offset"]: chunk for row in verified.values()
                  if row["source"] == "patch_chunk_store" for chunk in row["chunks"]}
        with (TARGET / "chunk/store.cdb").open("r+b") as target:
            for offset, chunk in sorted(chunks.items()):
                source.seek(offset)
                packed = source.read(chunk["compressed_bytes"])
                if hashlib.sha256(packed).hexdigest() != chunk["compressed_sha256"]:
                    raise ValueError("Verified source chunk changed")
                target.seek(offset)
                target.write(packed)
            target.flush()
            os.fsync(target.fileno())
        with (TARGET / "chunk/store.cdb").open("rb") as target:
            for offset, chunk in chunks.items():
                target.seek(offset)
                if hashlib.sha256(target.read(chunk["compressed_bytes"])).hexdigest() != chunk["compressed_sha256"]:
                    raise ValueError("Copied original chunk differs")
    for row in verified.values():
        if row["source"] == "installed_builtin":
            relative = Path(row["path"]).relative_to(ROOT / "NIKKE/NIKKE/game")
            copy = SANDBOX / "NIKKE/NIKKE/game" / relative
            if hashlib.sha256(copy.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("Copied current builtin differs")
    spec = importlib.util.spec_from_file_location("shared153_sparse", ROOT / "tools/raid-lab/native-player/stage_resource_chunks.py")
    sparse = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sparse)
    physical, logical = sparse.standard_info(TARGET / "chunk/store.cdb")
    result = {"schemaVersion": 1, "currentCatalogSha256": hashlib.sha256((CORE / "catalog.ndb").read_bytes()).hexdigest(),
              "sourceIndexSha256": hashlib.sha256(index_bytes).hexdigest(), "originalKeys": KEYS,
              "currentSerializedCanvasReferences": sorted(canvas_refs), "entries": entries,
              "verifiedBundles": verified, "sparsePhysicalBytes": physical, "sparseLogicalBytes": logical,
              "stagedChunks": len(chunks), "compressedBytes": sum(c["compressed_bytes"] for c in chunks.values()),
              "nativeLoaded": False, "battleStarted": False}
    with receipt.open("x", encoding="utf-8") as sink:
        json.dump(result, sink, indent=2)
        sink.write("\n")
    print(json.dumps({"stagedChunks": len(chunks), "physicalBytes": physical}))


if __name__ == "__main__":
    main()

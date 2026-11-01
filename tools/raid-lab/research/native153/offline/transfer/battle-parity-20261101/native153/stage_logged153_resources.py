"""Stage exact newly logged missing bundles and their original typed references."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
TARGET = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
sys.path[:0] = [str(HERE), str(ROOT / "tools/raid-lab/private/native-python"),
               str(ROOT / "tools/raid-lab/native-player"), str(ROOT / "transfer")]
import UnityPy
import zstandard
from build_logged_bundle_evidence import database, key_bundles, verify_bundle
from chunk_index import decode_index
from extract_practice_geometry153 import asset_rows, sha
from stage_practice153_resources import refs


def main(log, output):
    log, output = log.resolve(), output.resolve()
    if not log.is_relative_to(SANDBOX) or not output.is_relative_to(SANDBOX) or output.exists():
        raise ValueError("Archived private log and fresh private output required")
    data = log.read_text()
    names = sorted(set(re.findall(r"Chunk decompression failed: key='([^'\r\n]+\.bundle)'", data)))
    if not names or len(names) > 32:
        raise ValueError("One bounded set of distinct actual missing bundle keys required")
    raw = CORE / "raw/6a46ed93faa7c6fd01f1aa66253becc7.db"
    catalog, patch = database(raw), database(CORE / "catalog.ndb")
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source_store = CORE / "chunk/store.cdb"
    verified, entries, serialized, text_assets = {}, {}, [], []
    pending, done = list(names), set()
    decoder = zstandard.ZstdDecompressor()
    with source_store.open("rb") as source:
        def body(name):
            if name not in verified:
                verified[name] = verify_bundle(patch, index, name, source_store, source, decoder)
            row = verified[name]
            if row["source"] == "installed_builtin":
                return Path(row["path"]).read_bytes()
            parts = []
            for chunk in row["chunks"]:
                source.seek(chunk["store_offset"])
                parts.append(decoder.decompress(source.read(chunk["compressed_bytes"])))
            return b"".join(parts)
        while pending:
            key = pending.pop(0)
            if key in done:
                continue
            done.add(key)
            if len(done) > 128:
                raise ValueError("Stop original selected reference closure at128")
            rows, closure = key_bundles(catalog, key)
            entries[key] = rows
            for name in sorted(closure):
                if name not in verified:
                    verified[name] = verify_bundle(patch, index, name, source_store, source, decoder)
            # Only original objects in explicitly logged or typed-reference main
            # bundles are inspected. No catalog-wide/default numeric key search.
            inspect = [key] if key.endswith(".bundle") else list(closure)
            wanted_ids = None if key.endswith(".bundle") else {r["internal_id"] for r in asset_rows(catalog, key)}
            for name in inspect:
                payload = body(name)
                env = UnityPy.load(payload)
                objects = {obj.path_id: obj for obj in env.objects}
                for asset_bundle in objects.values():
                    if asset_bundle.type.name != "AssetBundle":
                        continue
                    for internal, container in asset_bundle.read_typetree()["m_Container"]:
                        if wanted_ids is not None and internal not in wanted_ids:
                            continue
                        target = container["asset"]
                        if target["m_FileID"] != 0 or target["m_PathID"] not in objects:
                            raise ValueError("Original container target not local")
                        obj = objects[target["m_PathID"]]
                        if obj.type.name == "TextAsset":
                            typed = obj.read(); value = typed.m_Script
                            value = value.encode("utf-8", "surrogateescape") if isinstance(value, str) else bytes(value)
                            text_assets.append({"bundle": name, "internal_id": internal, "name": typed.m_Name,
                                                "sha256": hashlib.sha256(value).hexdigest(),
                                                "bytes": len(value), "text": value.decode("utf-8")})
                        else:
                            targets = ([obj] if obj.type.name == "MonoBehaviour" else
                                       [o for o in objects.values() if o.type.name == "MonoBehaviour"]
                                       if obj.type.name == "GameObject" else [])
                            for component in targets:
                                fields = component.read_typetree(); found = refs(fields)
                                serialized.append({"bundle": name, "internal_id": internal,
                                                   "component_path_id": component.path_id,
                                                   "fields": fields, "asset_references": found})
                                for ref in found:
                                    if not asset_rows(catalog, ref["guid"]):
                                        raise ValueError("Exact original serialized reference absent")
                                    if ref["guid"] not in done:
                                        pending.append(ref["guid"])
        chunks = {c["store_offset"]: c for v in verified.values() if v["source"] == "patch_chunk_store" for c in v["chunks"]}
        copied = reused = 0
        with (TARGET / "chunk/store.cdb").open("r+b") as target:
            for offset, ch in sorted(chunks.items()):
                target.seek(offset)
                if hashlib.sha256(target.read(ch["compressed_bytes"])).hexdigest() == ch["compressed_sha256"]:
                    reused += 1; continue
                source.seek(offset); packed = source.read(ch["compressed_bytes"])
                if hashlib.sha256(packed).hexdigest() != ch["compressed_sha256"]:
                    raise ValueError("Original verified source changed")
                target.seek(offset); target.write(packed); copied += 1
            target.flush(); os.fsync(target.fileno())
        with (TARGET / "chunk/store.cdb").open("rb") as target:
            for offset, ch in chunks.items():
                target.seek(offset)
                if hashlib.sha256(target.read(ch["compressed_bytes"])).hexdigest() != ch["compressed_sha256"]:
                    raise ValueError("Copied original chunk readback mismatch")
    for v in verified.values():
        if v["source"] == "installed_builtin":
            staged = SANDBOX / "NIKKE/NIKKE/game" / Path(v["path"]).relative_to(ROOT / "NIKKE/NIKKE/game")
            if sha(staged) != v["sha256"]:
                raise ValueError("Copied original builtin mismatch")
    result = {"schemaVersion": 1, "scope": "Distinct actual missing native bundles and original typed AssetReference closure",
              "stagerSourceSha256": sha(Path(__file__)),
              "sourceLog": str(log), "sourceLogSha256": sha(log), "loggedBundleKeys": names,
              "clientSha256": sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll"),
              "currentCatalogSha256": sha(CORE / "catalog.ndb"), "rawCatalogSha256": sha(raw),
              "sourceIndexSha256": sha(index_path), "entries": entries, "verifiedBundles": verified,
              "serializedAssets": serialized, "originalTextAssets": text_assets,
              "copiedNewChunks": copied, "existingChunksReadbackOnly": reused,
              "compressedBytes": sum(c["compressed_bytes"] for c in chunks.values()),
              "nativeLaunched": False, "aliasesAdded": False, "defaultsInvented": False}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"path": str(output), "sha256": sha(output), "loggedBundles": len(names),
                      "verifiedBundles": len(verified), "newChunks": copied, "reusedChunks": reused,
                      "compressedBytes": result["compressedBytes"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.log, args.output)

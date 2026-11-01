"""Stage exact current core catalog and SpotSetting's one verified sparse chunk."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
TARGET = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
sys.path.insert(0, str(ROOT / "tools/raid-lab/private/native-python"))
sys.path.insert(0, str(ROOT / "transfer"))
import zstandard
from chunk_index import decode_index
from decode_nkdb import decode


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def db(path):
    connection = sqlite3.connect(":memory:")
    connection.deserialize(decode(path.read_bytes()))
    if connection.execute("pragma integrity_check").fetchone()[0] != "ok":
        raise ValueError("Catalog SQLite integrity failed")
    return connection


def main():
    receipt = SANDBOX / "catalog153-resources1.json"
    if receipt.exists() or TARGET.exists():
        raise FileExistsError("Preserve existing scratch catalog evidence")
    frozen = json.loads((ROOT / "transfer/update-20261030/catalog-metadata.json").read_text())
    expected_catalog = [r for r in frozen["files"] if str(r.get("path", "")).replace("\\", "/").endswith("/core/153.6.b29/catalog.ndb")]
    # The frozen metadata report uses project-relative paths; require exact bytes
    # when selecting its current core entry, not the retained historical catalog.
    if len(expected_catalog) != 1 or sha(CORE / "catalog.ndb") != expected_catalog[0]["sha256"]:
        raise ValueError("Installed core differs from frozen current153 catalog")
    patch = db(CORE / "catalog.ndb")
    raw_rows = patch.execute("select key,lower(hex(hash)),extension,size from files_rawtype").fetchall()
    by_key = {row[0]: row for row in raw_rows}
    if set(by_key) != {"catalog.db", "catalog.db.nds"}:
        raise ValueError("Unexpected current core raw requirements")
    raw_path = CORE / "raw" / (by_key["catalog.db"][1] + by_key["catalog.db"][2])
    raw = db(raw_path)
    query = """select e.dependency_key_rowid,i.internal_id,t.class_name from keys k
        join key_entries m on m.key_rowid=k.rowid join entries e on e.rowid=m.entry_rowid
        join internal_ids i on i.rowid=e.internal_id_rowid join types t on t.rowid=e.type_rowid where k.key=?"""
    assets = raw.execute(query, ("SpotSetting",)).fetchall()
    if len(assets) != 1 or assets[0][2] != "NK.Spot.SpotSetting":
        raise ValueError("Original SpotSetting asset identity/type differs")
    todo, seen, bundles = [assets[0][0]], set(), set()
    while todo:
        key = todo.pop()
        if not key or key in seen:
            continue
        seen.add(key)
        if len(seen) > 100:
            raise ValueError("SpotSetting closure unexpectedly exceeds100keys")
        for dependency, name in raw.execute("""select e.dependency_key_rowid,i.internal_id
            from key_entries m join entries e on e.rowid=m.entry_rowid
            join internal_ids i on i.rowid=e.internal_id_rowid where m.key_rowid=?""", (key,)):
            if dependency:
                todo.append(dependency)
            if name.endswith(".bundle"):
                bundles.add(name)
    if len(bundles) != 1:
        raise ValueError("Review changed SpotSetting closure before expanding")
    index_path = CORE / "chunk/store.cdb.idx"
    index_bytes = index_path.read_bytes()
    index = decode_index(index_bytes)
    store = CORE / "chunk/store.cdb"
    logical = store.stat().st_size
    chunks = []
    with store.open("rb") as source:
        header = source.read(256)
        if len(header) != 256 or struct.unpack_from("<II", header) != (0x424C4243, 1):
            raise ValueError("Original256byte chunk header magic/version differs")
        for bundle in bundles:
            rows = patch.execute("""select c.hash,c.compressed_size,c.original_size,m.file_offset from files_chunktype f
                join chunk_file_map m on m.file_id=f.file_id join chunks c on c.chunk_id=m.chunk_id
                where f.key=? order by m.file_offset""", (bundle,)).fetchall()
            if len(rows) != 1:
                raise ValueError("Review unexpected SpotSetting chunk count")
            digest, compressed, decoded, bundle_offset = rows[0]
            offset, indexed_size = index[digest]
            if indexed_size != compressed or bundle_offset != 0 or offset + compressed > logical:
                raise ValueError("Exact original chunk/index bounds differ")
            source.seek(offset)
            packed = source.read(compressed)
            payload = zstandard.ZstdDecompressor().decompress(packed)
            if len(payload) != decoded or not payload.startswith(b"UnityFS"):
                raise ValueError("Original SpotSetting chunk decode failed")
            chunks.append({"bundle": bundle, "hash": digest.hex(), "offset": offset,
                "compressedBytes": compressed, "decodedBytes": decoded,
                "compressedSha256": hashlib.sha256(packed).hexdigest(),
                "decodedSha256": hashlib.sha256(payload).hexdigest(), "packed": packed})
    TARGET.mkdir(parents=True)
    copied = []
    relative_files = ["catalog.ndb", "catalog.ndb.nds"] + ["raw/" + row[1] + row[2] for row in raw_rows]
    for relative in relative_files:
        source, target = CORE / relative, TARGET / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha(source) != sha(target):
            raise ValueError("Current catalog copy/readback mismatch")
        copied.append({"relative": relative, "bytes": source.stat().st_size, "sha256": sha(source)})
    (TARGET / "chunk").mkdir()
    target_index = TARGET / "chunk/store.cdb.idx"
    target_index.write_bytes(index_bytes)
    helper_path = ROOT / "tools/raid-lab/native-player/stage_resource_chunks.py"
    spec = importlib.util.spec_from_file_location("sparse153_primitives", helper_path)
    sparse = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sparse)
    target_store = TARGET / "chunk/store.cdb"
    with target_store.open("x+b") as target:
        sparse.set_sparse(target)
        target.truncate(logical)
        sparse.deallocate_zeros(target, logical)
        target.seek(0)
        target.write(header)
        for row in chunks:
            target.seek(row["offset"])
            target.write(row["packed"])
        target.flush()
        os.fsync(target.fileno())
    physical, eof = sparse.standard_info(target_store)
    if eof != logical or physical > 1024 * 1024:
        raise ValueError("Unexpected sparse storage allocation")
    with target_store.open("rb") as target:
        if target.read(256) != header:
            raise ValueError("Sparse header mismatch")
        for row in chunks:
            target.seek(row["offset"])
            if target.read(row["compressedBytes"]) != row.pop("packed"):
                raise ValueError("Sparse chunk readback mismatch")
    result = {"schemaVersion": 1, "currentCatalogSha256": sha(CORE / "catalog.ndb"),
        "copiedCatalogFiles": copied, "spotSettingAsset": assets[0][1], "bundles": sorted(bundles),
        "sourceStore": str(store), "sourceIndexSha256": sha(index_path),
        "sparseStore": str(target_store), "logicalBytes": logical, "allocatedBytes": physical,
        "headerSha256": hashlib.sha256(header).hexdigest(), "chunks": chunks,
        "nativeCatalogLoaded": False, "nativeSpotSettingLoaded": False, "battleStarted": False}
    with receipt.open("x", encoding="utf-8") as sink:
        json.dump(result, sink, indent=2)
        sink.write("\n")
    print(json.dumps({"catalogFiles": len(copied), "chunks": len(chunks), "allocatedBytes": physical,
                      "logicalBytes": logical, "receipt": str(receipt)}))


if __name__ == "__main__":
    main()

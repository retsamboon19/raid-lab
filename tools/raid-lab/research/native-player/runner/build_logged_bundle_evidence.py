"""Verify exact logged failures or explicitly selected catalog dependencies.

The output is accepted by stage_resource_chunks.py. Optional --key arguments
add catalog dependencies for known Addressables keys; no key is inferred from
a bundle name. This command reads installed sources but does not stage them.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

import zstandard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
BUILTINS = ROOT / "NIKKE/NIKKE/game/nikke_Data/StreamingAssets/aa/StandaloneWindows64"
BASE = HERE / "resource-staging-evidence.json"
CHUNK_FAILURE = re.compile(r"Chunk decompression failed: key='([^'\r\n]+\.bundle)'", re.I)

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index
from decode_nkdb import decode


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def database(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.deserialize(decode(path.read_bytes()))
    if conn.execute("pragma integrity_check").fetchone()[0] != "ok":
        raise ValueError(f"Invalid catalog database: {path}")
    return conn


def key_bundles(catalog: sqlite3.Connection, key: str) -> tuple[list[dict], set[str]]:
    rows = catalog.execute("""select e.dependency_key_rowid,i.internal_id,e.quality_texture,t.class_name
        from keys k join key_entries ke on ke.key_rowid=k.rowid
        join entries e on e.rowid=ke.entry_rowid
        join internal_ids i on i.rowid=e.internal_id_rowid
        join types t on t.rowid=e.type_rowid where k.key=?""", (key,)).fetchall()
    if not rows:
        raise ValueError(f"Exact catalog key absent: {key}")
    bundles: set[str] = set()
    entries = []
    for dependency, internal, quality, asset_type in rows:
        entries.append({"key": key, "asset_type": asset_type, "quality": quality,
                        "internal_id": internal})
        if internal.endswith(".bundle"):
            bundles.add(internal)
        todo = [dependency] if dependency else []
        seen = set()
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            for child, name in catalog.execute("""select e.dependency_key_rowid,i.internal_id
                from key_entries ke join entries e on e.rowid=ke.entry_rowid
                join internal_ids i on i.rowid=e.internal_id_rowid
                where ke.key_rowid=?""", (node,)):
                if child:
                    todo.append(child)
                if name.endswith(".bundle"):
                    bundles.add(name)
    if not bundles:
        raise ValueError(f"Catalog key has no bundle dependency: {key}")
    return entries, bundles


def verify_bundle(patch: sqlite3.Connection, index: dict, name: str,
                  source: Path, stream, decoder) -> dict:
    mapped = patch.execute("select file_id from files_chunktype where key=?", (name,)).fetchone()
    if not mapped:
        path = BUILTINS / name
        if not path.is_file():
            raise ValueError(f"Missing source bundle: {name}")
        with path.open("rb") as bundle_stream:
            if bundle_stream.read(7) != b"UnityFS":
                raise ValueError(f"Invalid built-in UnityFS bundle: {name}")
        return {"name": name, "source": "installed_builtin", "path": str(path),
                "bytes": path.stat().st_size, "sha256": sha(path)}
    rows = patch.execute("""select c.hash,c.compressed_size,c.original_size,m.file_offset
        from chunk_file_map m join chunks c on c.chunk_id=m.chunk_id
        where m.file_id=? order by m.file_offset""", mapped).fetchall()
    if not rows:
        raise ValueError(f"No source chunks: {name}")
    expected_offset = 0
    digest = hashlib.sha256()
    chunks = []
    for chunk_hash, packed_size, decoded_size, file_offset in rows:
        if chunk_hash not in index:
            raise ValueError(f"Missing indexed chunk {chunk_hash.hex()} for {name}")
        offset, length = index[chunk_hash]
        if length != packed_size or offset + length > source.stat().st_size or file_offset != expected_offset:
            raise ValueError(f"Invalid source chunk bounds for {name}")
        stream.seek(offset)
        packed = stream.read(length)
        if len(packed) != length:
            raise ValueError(f"Short source chunk for {name}")
        decoded = decoder.decompress(packed)
        if len(decoded) != decoded_size or (not expected_offset and not decoded.startswith(b"UnityFS")):
            raise ValueError(f"Invalid decoded UnityFS chunk for {name}")
        chunks.append({"hash": chunk_hash.hex(), "store_offset": offset,
                       "compressed_bytes": length, "compressed_sha256": hashlib.sha256(packed).hexdigest(),
                       "decoded_bytes": decoded_size, "bundle_offset": file_offset})
        digest.update(decoded)
        expected_offset += decoded_size
    return {"name": name, "source": "patch_chunk_store", "chunks": chunks,
            "compressed_bytes": sum(item["compressed_bytes"] for item in chunks),
            "verified_decoded": {"name": name, "chunksDecoded": len(chunks),
                                 "decodedSha256": digest.hexdigest(), "decodedBytes": expected_offset}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="One exact private-player actual-player.log")
    parser.add_argument("--output", type=Path, required=True, help="New evidence JSON path")
    parser.add_argument("--key", action="append", default=[], help="Exact additional Addressables key whose catalog dependencies to include")
    args = parser.parse_args()
    log = args.log.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite evidence: {output}")
    failed = sorted(set(CHUNK_FAILURE.findall(log.read_text(encoding="utf-8", errors="replace"))))
    if not failed and not args.key:
        raise ValueError("Provide an exact logged chunk failure or an explicit catalog key")
    base = json.loads(BASE.read_text(encoding="utf-8"))
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    row = patch.execute("select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    if not row:
        raise ValueError("Patch catalog has no raw Addressables catalog")
    raw = CORE / "raw" / (row[0].hex() + row[1])
    catalog = database(raw)
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source = CORE / "chunk/store.cdb"
    all_bundles = set(failed)
    key_entries = []
    for key in sorted(set(args.key)):
        entries, bundles = key_bundles(catalog, key)
        key_entries += entries
        all_bundles.update(bundles)
    verified = {}
    builtins = {}
    decoder = zstandard.ZstdDecompressor()
    with source.open("rb") as stream:
        for name in sorted(all_bundles):
            result = verify_bundle(patch, index, name, source, stream, decoder)
            if result["source"] == "patch_chunk_store":
                verified[name] = result
            else:
                builtins[name] = result
    if any(name not in verified and name not in builtins for name in failed):
        raise ValueError("A logged bundle could not be verified")
    result = {key: base[key] for key in ("client_sha256", "installed_patch_root",
             "sandbox_patch_root_suffix", "core_bootstrap_files", "core_chunk_store")}
    result.update({"schema_version": 1, "status": "static_catalog_mapping_only",
                   "scope": "Exact logged failed bundles and explicitly selected key dependencies only",
                   "log_path": str(log), "log_sha256": sha(log),
                   "logged_failed_bundles": failed, "requested_catalog_keys": key_entries,
                   "catalog_sha256": sha(patch_path), "raw_catalog_sha256": sha(raw),
                   "index_sha256": sha(index_path), "bundle_scope": sorted(verified),
                   "verified_bundles": verified, "built_in_bundles": builtins,
                   "limits": ["Unspecified dynamic Addressables keys are not inferred or staged.",
                              "This verifies source bytes/catalog mapping, not runtime loading."]})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "logged_bundles": len(failed), "patch_bundles": len(verified),
                      "builtins": len(builtins),
                      "unique_chunks": len({c["hash"] for b in verified.values() for c in b["chunks"]})}))


if __name__ == "__main__":
    main()

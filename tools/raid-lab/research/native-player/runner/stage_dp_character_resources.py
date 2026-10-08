"""Stage only source-verified five-character DP resources in private player.

Never writes installed sources. The 13 GB logical chunk store is sparse and
contains only the original header plus chunks in dp-character-evidence.json.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys

from stage_resource_chunks import (HEADER_BYTES, SPARSE_ATTRIBUTE, attrs,
    set_sparse, deallocate_zeros, verify_sparse_allocation, allocated_bytes)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/dp"
SANDBOX = ROOT / "tools/raid-lab/private/native-player-20261008a"
STAGED = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/dp"
EVIDENCE = HERE / "dp-character-evidence.json"
RECEIPT = SANDBOX / "dp-character-resource-chunks.json"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_copy(rel: str, digest: str) -> dict:
    source = SOURCE / rel
    target = STAGED / rel
    if sha(source) != digest:
        raise ValueError(f"Installed DP bootstrap changed: {source}")
    if target.exists():
        if sha(target) != digest or os.path.samefile(source, target):
            raise ValueError(f"Existing scratch DP bootstrap differs: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".partial")
        if partial.exists():
            raise ValueError(f"Unresolved scratch partial: {partial}")
        shutil.copy2(source, partial)
        if sha(partial) != digest:
            raise ValueError(f"DP bootstrap copy differs: {partial}")
        partial.replace(target)
    return {"source": str(source), "copy": str(target), "bytes": source.stat().st_size,
            "sha256": digest}


def all_chunks(evidence: dict) -> list[dict]:
    chunks = {}
    for bundle in evidence["verified_bundles"].values():
        if bundle["source"] != "patch_chunk_store" or not bundle["verified_decoded"]["decodedSha256"]:
            raise ValueError("Unverified DP bundle")
        for row in bundle["chunks"]:
            item = {k: row[k] for k in ("hash", "store_offset", "compressed_bytes", "compressed_sha256", "decoded_bytes")}
            prior = chunks.get(item["store_offset"])
            if prior is not None and prior != item:
                raise ValueError("Conflicting DP chunk offsets")
            chunks[item["store_offset"]] = item
    result = sorted(chunks.values(), key=lambda row: row["store_offset"])
    if len(result) != evidence["unique_chunks"]:
        raise ValueError("DP evidence chunk count mismatch")
    if any(a["store_offset"] + a["compressed_bytes"] > b["store_offset"] for a, b in zip(result, result[1:])):
        raise ValueError("Overlapping DP source chunks")
    return result


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if evidence["status"] != "static_catalog_mapping_only" or evidence["source_patch_root"] != str(SOURCE):
        raise ValueError("DP evidence source mismatch")
    if len(evidence["requested_keys"]) != 20:
        raise ValueError("DP key scope changed")
    if sha(SOURCE / "catalog.ndb") != evidence["catalog_sha256"] or sha(SOURCE / "catalog.ndb.nds") != evidence["catalog_signature_sha256"]:
        raise ValueError("Installed DP signed catalog changed")
    if sha(ROOT / evidence["client_manifest_path"]) != evidence["client_manifest_sha256"]:
        raise ValueError("Current-client metadata manifest changed")
    source_store = SOURCE / "chunk/store.cdb"
    target_store = STAGED / "chunk/store.cdb"
    logical = evidence["store_logical_bytes"]
    if source_store.stat().st_size != logical:
        raise ValueError("Installed DP store length changed")
    with source_store.open("rb") as stream:
        header = stream.read(HEADER_BYTES)
    if hashlib.sha256(header).hexdigest() != evidence["store_header_sha256"] or struct.unpack_from("<II", header) != (0x424C4243, 1):
        raise ValueError("Installed DP store header changed")
    chunks = all_chunks(evidence)
    sys.path.insert(0, str(ROOT / "transfer"))
    from chunk_index import decode_index
    index = decode_index((SOURCE / "chunk/store.cdb.idx").read_bytes())
    if sha(SOURCE / "chunk/store.cdb.idx") != evidence["index_sha256"]:
        raise ValueError("Installed DP index changed")
    for row in chunks:
        if index.get(bytes.fromhex(row["hash"])) != (row["store_offset"], row["compressed_bytes"]):
            raise ValueError(f"DP index mapping changed: {row['hash']}")
        if row["store_offset"] + row["compressed_bytes"] > logical:
            raise ValueError("DP chunk exceeds store")
    boot = [checked_copy("catalog.ndb", evidence["catalog_sha256"]),
            checked_copy("catalog.ndb.nds", evidence["catalog_signature_sha256"])]
    for row in evidence["raw_files"]:
        source = Path(row["path"])
        if not source.is_relative_to(SOURCE):
            raise ValueError("DP raw source outside installed tree")
        boot.append(checked_copy(source.relative_to(SOURCE).as_posix(), row["sha256"]))
    boot.append(checked_copy("chunk/store.cdb.idx", evidence["index_sha256"]))
    target_store.parent.mkdir(parents=True, exist_ok=True)
    if RECEIPT.exists():
        old = json.loads(RECEIPT.read_text(encoding="utf-8"))
        if old.get("evidence_sha256") != sha(EVIDENCE) or old.get("store_path") != str(target_store):
            raise ValueError("Existing DP receipt differs")
        if not target_store.is_file() or not attrs(target_store) & SPARSE_ATTRIBUTE:
            raise ValueError("Existing DP sparse store missing")
        with target_store.open("rb") as staged, source_store.open("rb") as original:
            if staged.read(HEADER_BYTES) != header:
                raise ValueError("Existing DP header differs")
            for row in chunks:
                staged.seek(row["store_offset"])
                original.seek(row["store_offset"])
                if staged.read(row["compressed_bytes"]) != original.read(row["compressed_bytes"]):
                    raise ValueError(f"Existing DP chunk differs at {row['store_offset']}")
        allocation, ranges = verify_sparse_allocation(target_store, logical, chunks, require_header=True)
        print(json.dumps({"status": "verified_existing", "chunks": len(chunks), "allocated_bytes": allocation}))
        return
    if target_store.exists():
        raise ValueError("DP scratch store exists without receipt")
    partial = target_store.with_name(target_store.name + ".partial")
    if partial.exists():
        raise ValueError("Unresolved DP scratch partial exists")
    with partial.open("x+b") as staged:
        set_sparse(staged)
        if not attrs(partial) & SPARSE_ATTRIBUTE:
            raise ValueError("DP scratch file did not become sparse")
        staged.truncate(logical)
        deallocate_zeros(staged, logical)
        staged.flush()
        os.fsync(staged.fileno())
    verify_sparse_allocation(partial, logical, [])
    with source_store.open("rb") as original, partial.open("r+b") as staged:
        staged.write(header)
        for row in chunks:
            original.seek(row["store_offset"])
            packed = original.read(row["compressed_bytes"])
            if hashlib.sha256(packed).hexdigest() != row["compressed_sha256"]:
                raise ValueError(f"DP source chunk changed at {row['store_offset']}")
            staged.seek(row["store_offset"])
            staged.write(packed)
        staged.flush()
        os.fsync(staged.fileno())
    with partial.open("rb") as staged:
        if staged.read(HEADER_BYTES) != header:
            raise ValueError("DP scratch header mismatch")
        for row in chunks:
            staged.seek(row["store_offset"])
            if hashlib.sha256(staged.read(row["compressed_bytes"])).hexdigest() != row["compressed_sha256"]:
                raise ValueError(f"DP scratch chunk mismatch at {row['store_offset']}")
    allocation, ranges = verify_sparse_allocation(partial, logical, chunks, require_header=True)
    partial.replace(target_store)
    report = {"schema_version": 1, "status": "source_verified_sparse_dp_chunks",
              "evidence_path": str(EVIDENCE), "evidence_sha256": sha(EVIDENCE),
              "source_store_path": str(source_store), "store_path": str(target_store),
              "logical_bytes": logical, "allocation_size_bytes": allocation,
              "compressed_file_size_bytes": allocated_bytes(target_store), "sparse_attribute": True,
              "allocated_ranges": [{"offset": offset, "length": length} for offset, length in ranges],
              "header": {"length": HEADER_BYTES, "sha256": evidence["store_header_sha256"]},
              "bootstrap_files": boot, "chunks": chunks,
              "bundle_scope": evidence["bundle_scope"]}
    receipt_partial = RECEIPT.with_name(RECEIPT.name + ".partial")
    if receipt_partial.exists():
        raise ValueError("Unresolved DP receipt partial exists")
    receipt_partial.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    receipt_partial.replace(RECEIPT)
    print(json.dumps({"status": report["status"], "keys": 20,
                      "bundles": len(report["bundle_scope"]), "chunks": len(chunks),
                      "logical_bytes": logical, "allocated_bytes": allocation,
                      "receipt": str(RECEIPT), "sha256": sha(RECEIPT)}))


if __name__ == "__main__":
    main()

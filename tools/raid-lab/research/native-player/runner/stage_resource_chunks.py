"""Stage only source-verified patch chunks in a sparse private-player store.

The installed chunk store is opened read-only. Existing scratch resources are
preserved and verified; a new evidence file may add verified chunks later.
"""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import shutil
import struct
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player-20261008a"
PATCH_SOURCE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
PATCH_STAGED = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
EVIDENCE = HERE / "resource-staging-evidence.json"
BOOTSTRAP = SANDBOX / "bootstrap-resources.json"
RECEIPT = SANDBOX / "resource-chunks.json"
PRE_HEADER_RECEIPT = SANDBOX / "resource-chunks-pre-header.json"
INDEX_SOURCE = PATCH_SOURCE / "chunk/store.cdb.idx"
INDEX_STAGED = PATCH_STAGED / "chunk/store.cdb.idx"
STORE_SOURCE = PATCH_SOURCE / "chunk/store.cdb"
STORE_STAGED = PATCH_STAGED / "chunk/store.cdb"
SPARSE_ATTRIBUTE = 0x200
INVALID_ATTRIBUTES = 0xFFFFFFFF
FSCTL_SET_SPARSE = 0x000900C4
MAX_INITIAL_ALLOCATION = 16 * 1024 * 1024
HEADER_BYTES = 0x100  # Current-client ChunkStore.ReadHeader reads exactly 0x100 bytes.
HEADER_SHA256 = "cb639b5a1c95de8bde6e8592e91c0c1e87fb7c92e4f021cc42a47710411b9bba"
FSCTL_SET_ZERO_DATA = 0x000980C8
FSCTL_QUERY_ALLOCATED_RANGES = 0x000940CF


class FileStandardInfo(ctypes.Structure):
    _fields_ = [("AllocationSize", ctypes.c_int64),
                ("EndOfFile", ctypes.c_int64),
                ("NumberOfLinks", wintypes.DWORD),
                ("DeletePending", wintypes.BOOLEAN),
                ("Directory", wintypes.BOOLEAN)]


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def attrs(path: Path) -> int:
    kernel = ctypes.windll.kernel32
    kernel.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    kernel.GetFileAttributesW.restype = wintypes.DWORD
    value = kernel.GetFileAttributesW(str(path))
    if value == INVALID_ATTRIBUTES:
        raise ctypes.WinError()
    return value


def allocated_bytes(path: Path) -> int:
    kernel = ctypes.windll.kernel32
    kernel.GetCompressedFileSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetCompressedFileSizeW.restype = wintypes.DWORD
    high = wintypes.DWORD()
    ctypes.set_last_error(0)
    low = kernel.GetCompressedFileSizeW(str(path), ctypes.byref(high))
    if low == 0xFFFFFFFF and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return (high.value << 32) | low


def standard_info(path: Path) -> tuple[int, int]:
    """Read allocation and EOF from the file handle, independent of compression APIs."""
    kernel = ctypes.windll.kernel32
    kernel.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                    wintypes.LPVOID, wintypes.DWORD]
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    with path.open("rb") as stream:
        info = FileStandardInfo()
        if not kernel.GetFileInformationByHandleEx(msvcrt.get_osfhandle(stream.fileno()), 1,
                                                    ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError()
    return info.AllocationSize, info.EndOfFile


def allocated_ranges(path: Path, logical_size: int) -> list[tuple[int, int]]:
    """Ask the filesystem which original-offset regions actually occupy storage."""
    kernel = ctypes.windll.kernel32
    query = (ctypes.c_int64 * 2)(0, logical_size)
    output = ctypes.create_string_buffer(1024 * 1024)
    returned = wintypes.DWORD()
    with path.open("rb") as stream:
        handle = msvcrt.get_osfhandle(stream.fileno())
        if not kernel.DeviceIoControl(handle, FSCTL_QUERY_ALLOCATED_RANGES,
                                      ctypes.byref(query), ctypes.sizeof(query),
                                      output, len(output), ctypes.byref(returned), None):
            raise ctypes.WinError()
    if returned.value % 16:
        raise ValueError("Malformed allocated-range response")
    ranges = [(ctypes.c_int64.from_buffer_copy(output, start).value,
               ctypes.c_int64.from_buffer_copy(output, start + 8).value)
              for start in range(0, returned.value, 16)]
    if any(offset < 0 or length <= 0 or offset + length > logical_size
           for offset, length in ranges):
        raise ValueError("Filesystem returned invalid allocated ranges")
    return ranges


def verify_sparse_allocation(path: Path, logical_size: int, chunks: list[dict],
                             require_header: bool = False) -> tuple[int, list[tuple[int, int]]]:
    if not attrs(path) & SPARSE_ATTRIBUTE:
        raise ValueError("Scratch store lost sparse attribute")
    physical, eof = standard_info(path)
    # Sparse writes allocate whole filesystem clusters, not packed byte counts.
    kernel = ctypes.windll.kernel32
    sectors = wintypes.DWORD()
    bytes_per_sector = wintypes.DWORD()
    free = wintypes.DWORD()
    total = wintypes.DWORD()
    kernel.GetDiskFreeSpaceW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD),
                                         ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                                         ctypes.POINTER(wintypes.DWORD)]
    kernel.GetDiskFreeSpaceW.restype = wintypes.BOOL
    if not kernel.GetDiskFreeSpaceW(path.anchor, ctypes.byref(sectors),
                                    ctypes.byref(bytes_per_sector), ctypes.byref(free),
                                    ctypes.byref(total)):
        raise ctypes.WinError()
    unit = sectors.value * bytes_per_sector.value
    if unit < 512 or unit > 1024 * 1024 or unit & (unit - 1):
        raise ValueError(f"Unexpected filesystem allocation unit: {unit}")
    regions = [(row["store_offset"], row["compressed_bytes"]) for row in chunks]
    if require_header:
        regions.append((0, HEADER_BYTES))
    ceiling = MAX_INITIAL_ALLOCATION + sum(
        ((offset % unit + length + unit - 1) // unit) * unit for offset, length in regions)
    if eof != logical_size or physical > ceiling:
        raise ValueError(f"Scratch store allocation/EOF unexpected: {physical}, {eof}")
    ranges = allocated_ranges(path, logical_size)
    if not chunks and ranges:
        raise ValueError("New sparse store unexpectedly has allocated ranges")
    for row in chunks:
        start, end = row["store_offset"], row["store_offset"] + row["compressed_bytes"]
        if not any(offset <= start and offset + length >= end for offset, length in ranges):
            raise ValueError(f"Staged chunk lacks an allocated range: {start}")
    if require_header and not any(offset == 0 and length >= HEADER_BYTES for offset, length in ranges):
        raise ValueError("Staged header lacks an allocated range")
    return physical, ranges


def source_header() -> bytes:
    with STORE_SOURCE.open("rb") as stream:
        header = stream.read(HEADER_BYTES)
    if len(header) != HEADER_BYTES or hashlib.sha256(header).hexdigest() != HEADER_SHA256:
        raise ValueError("Installed chunk-store header differs from current-client source")
    if struct.unpack_from("<II", header) != (0x424C4243, 1):
        raise ValueError("Installed chunk-store header has unexpected magic/version")
    return header


def verify_header(path: Path, header: bytes, allow_empty: bool = False) -> bool:
    with path.open("rb") as stream:
        staged = stream.read(HEADER_BYTES)
    if staged == header:
        return True
    if allow_empty and staged == bytes(HEADER_BYTES):
        return False
    raise ValueError("Scratch chunk-store header differs from verified source")


def set_sparse(stream) -> None:
    kernel = ctypes.windll.kernel32
    kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                       wintypes.LPVOID, wintypes.DWORD,
                                       wintypes.LPVOID, wintypes.DWORD,
                                       ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel.DeviceIoControl.restype = wintypes.BOOL
    returned = wintypes.DWORD()
    handle = msvcrt.get_osfhandle(stream.fileno())
    if not kernel.DeviceIoControl(handle, FSCTL_SET_SPARSE, None, 0,
                                  None, 0, ctypes.byref(returned), None):
        raise ctypes.WinError()


def deallocate_zeros(stream, logical_size: int) -> None:
    """Punch the newly extended zero range; CRT truncate may allocate it."""
    kernel = ctypes.windll.kernel32
    bounds = (ctypes.c_int64 * 2)(0, logical_size)
    returned = wintypes.DWORD()
    handle = msvcrt.get_osfhandle(stream.fileno())
    if not kernel.DeviceIoControl(handle, FSCTL_SET_ZERO_DATA, ctypes.byref(bounds),
                                  ctypes.sizeof(bounds), None, 0,
                                  ctypes.byref(returned), None):
        raise ctypes.WinError()


def checked_paths(evidence: dict) -> tuple[Path, Path]:
    expected = "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch"
    if evidence.get("sandbox_patch_root_suffix") != expected:
        raise ValueError("Evidence points at another scratch patch root")
    source = (ROOT / evidence["core_chunk_store"]["path"]).resolve(strict=True)
    if source != STORE_SOURCE.resolve(strict=True):
        raise ValueError("Evidence points at another installed chunk store")
    if PATCH_STAGED.resolve() != (SANDBOX / expected / "core").resolve():
        raise ValueError("Scratch store escaped the private player")
    return source, STORE_STAGED


def verify_bootstrap() -> None:
    rows = json.loads(BOOTSTRAP.read_text(encoding="utf-8"))
    checked = 0
    for row in rows:
        source = Path(row["source"])
        copy = Path(row["copy"])
        if not source.is_relative_to(PATCH_SOURCE) or not copy.is_relative_to(PATCH_STAGED):
            continue
        if not source.is_file() or not copy.is_file():
            raise ValueError(f"Missing bootstrap pair: {copy}")
        if sha(source) != row["sha256"] or sha(copy) != row["sha256"]:
            raise ValueError(f"Changed bootstrap pair: {copy}")
        checked += 1
    if checked != 4:
        raise ValueError(f"Expected four pre-staged bootstrap files, got {checked}")


def selected_chunks(evidence: dict, names: list[str]) -> tuple[list[dict], dict[str, list[str]]]:
    bundles = evidence.get("verified_bundles")
    if bundles is None:
        bundles = evidence["naga"]["verified_bundles"]
    if not names:
        names = sorted(evidence.get("bundle_scope", bundles))
    by_offset = {}
    selected_bundles = {}
    for name in names:
        bundle = bundles.get(name)
        if not bundle or bundle.get("source") != "patch_chunk_store" or not bundle.get("chunks"):
            raise ValueError(f"No source-verified patch chunks for bundle: {name}")
        if not bundle.get("verified_decoded", {}).get("decodedSha256"):
            raise ValueError(f"No decoded-body verification for bundle: {name}")
        selected_bundles[name] = []
        for chunk in bundle["chunks"]:
            # One physical chunk may appear at different logical bundle offsets.
            item = {key: chunk[key] for key in ("hash", "store_offset", "compressed_bytes",
                                                  "compressed_sha256", "decoded_bytes")}
            offset, length = item["store_offset"], item["compressed_bytes"]
            if offset < 0 or length < 1:
                raise ValueError(f"Invalid chunk bounds for {name}")
            prior = by_offset.get(offset)
            if prior is not None and prior != item:
                raise ValueError(f"Conflicting chunk at offset {offset}")
            by_offset[offset] = item
            selected_bundles[name].append(item["hash"])
    chunks = sorted(by_offset.values(), key=lambda item: item["store_offset"])
    if any(a["store_offset"] + a["compressed_bytes"] > b["store_offset"]
           for a, b in zip(chunks, chunks[1:])):
        raise ValueError("Selected source chunks overlap")
    return chunks, selected_bundles


def verify_chunk_index(chunks: list[dict], expected_index_sha: str) -> None:
    if sha(INDEX_SOURCE) != expected_index_sha:
        raise ValueError("Installed chunk index differs from evidence")
    if INDEX_STAGED.exists():
        if sha(INDEX_STAGED) != expected_index_sha:
            raise ValueError("Scratch chunk index differs from source")
    else:
        INDEX_STAGED.parent.mkdir(parents=True, exist_ok=True)
        partial = INDEX_STAGED.with_name(INDEX_STAGED.name + ".partial")
        if partial.exists():
            raise ValueError("Unresolved partial scratch index exists")
        shutil.copy2(INDEX_SOURCE, partial)
        if sha(partial) != expected_index_sha:
            raise ValueError("Copied chunk index differs from source")
        partial.replace(INDEX_STAGED)
    sys.path.insert(0, str(ROOT / "transfer"))
    from chunk_index import decode_index
    index = decode_index(INDEX_SOURCE.read_bytes())
    for chunk in chunks:
        expected = (chunk["store_offset"], chunk["compressed_bytes"])
        if index.get(bytes.fromhex(chunk["hash"])) != expected:
            raise ValueError(f"Stale chunk index mapping: {chunk['hash']}")


def verify_existing(receipt: dict, expected_index_sha: str, logical_size: int) -> list[dict]:
    if receipt.get("schema_version") not in (1, 2) or receipt.get("index_sha256") != expected_index_sha:
        raise ValueError("Existing scratch receipt has a different schema or index")
    if receipt.get("logical_bytes") != logical_size or receipt.get("store_path") != str(STORE_STAGED):
        raise ValueError("Existing scratch store has different source/bounds")
    if not STORE_STAGED.is_file() or STORE_STAGED.stat().st_size != logical_size:
        raise ValueError("Existing scratch store is absent or wrong length")
    if os.path.samefile(STORE_STAGED, STORE_SOURCE):
        raise ValueError("Scratch store is the installed source")
    if not attrs(STORE_STAGED) & SPARSE_ATTRIBUTE:
        raise ValueError("Existing scratch store is not sparse")
    if receipt.get("schema_version") == 2 and receipt.get("header") != {
            "offset": 0, "length": HEADER_BYTES, "sha256": HEADER_SHA256}:
        raise ValueError("Existing scratch receipt has a different header")
    verify_header(STORE_STAGED, source_header(), allow_empty=receipt["schema_version"] == 1)
    rows = receipt.get("chunks")
    if not isinstance(rows, list):
        raise ValueError("Existing scratch receipt has no chunks")
    with STORE_STAGED.open("rb") as target, STORE_SOURCE.open("rb") as source:
        for row in rows:
            offset, length = row["store_offset"], row["compressed_bytes"]
            source.seek(offset)
            target.seek(offset)
            original, staged = source.read(length), target.read(length)
            digest = row["compressed_sha256"]
            if hashlib.sha256(original).hexdigest() != digest or staged != original:
                raise ValueError(f"Previously staged chunk changed: {offset}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--bundle", action="append", default=[],
                        help="One source-verified bundle to add; defaults to the three Naga bundles")
    args = parser.parse_args()
    evidence_path = args.evidence.resolve(strict=True)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("status") != "static_catalog_mapping_only":
        raise ValueError("Resource evidence status is not the verified static map")
    if evidence.get("catalog_sha256") and sha(PATCH_SOURCE / "catalog.ndb") != evidence["catalog_sha256"]:
        raise ValueError("Installed patch catalog differs from Kraken evidence")
    source, target = checked_paths(evidence)
    verify_bootstrap()
    logical_size = evidence["core_chunk_store"]["logical_bytes"]
    if source.stat().st_size != logical_size:
        raise ValueError("Installed chunk store size changed")
    expected_index_sha = next(row["sha256"] for row in evidence["core_bootstrap_files"]
                              if row["path"].endswith("/chunk/store.cdb.idx"))
    desired, selected_bundles = selected_chunks(evidence, args.bundle)
    if any(row["store_offset"] + row["compressed_bytes"] > logical_size for row in desired):
        raise ValueError("Selected chunk extends beyond source store")
    verify_chunk_index(desired, expected_index_sha)
    header = source_header()
    if RECEIPT.exists():
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        existing = verify_existing(receipt, expected_index_sha, logical_size)
    elif target.exists():
        raise ValueError("Scratch store exists without a verifiable receipt")
    else:
        receipt = None
        existing = []
    existing_by_offset = {row["store_offset"]: row for row in existing}
    for row in desired:
        prior = existing_by_offset.get(row["store_offset"])
        if prior and any(prior[key] != row[key] for key in
                         ("hash", "compressed_bytes", "compressed_sha256")):
            raise ValueError(f"Existing chunk conflicts with new evidence: {row['store_offset']}")
        if any(row["store_offset"] < old["store_offset"] + old["compressed_bytes"] and
               old["store_offset"] < row["store_offset"] + row["compressed_bytes"]
               for old in existing if old["store_offset"] != row["store_offset"]):
            raise ValueError(f"New chunk overlaps existing receipt: {row['store_offset']}")
    additions = [row for row in desired if row["store_offset"] not in existing_by_offset]
    header_ready = receipt is not None and verify_header(
        target, header, allow_empty=receipt["schema_version"] == 1)
    # Preserve the old receipt before changing a store it authenticated.
    if receipt is not None and receipt["schema_version"] == 1:
        if PRE_HEADER_RECEIPT.exists():
            if PRE_HEADER_RECEIPT.read_bytes() != RECEIPT.read_bytes():
                raise ValueError("Existing pre-header receipt backup differs")
        else:
            shutil.copy2(RECEIPT, PRE_HEADER_RECEIPT)
    previous_receipt = None
    if receipt is not None and additions:
        previous_sha = sha(RECEIPT)
        previous_receipt = RECEIPT.with_name(f"resource-chunks-before-{previous_sha[:12]}.json")
        if previous_receipt.exists():
            if sha(previous_receipt) != previous_sha:
                raise ValueError("Existing chunk receipt backup differs")
        else:
            shutil.copy2(RECEIPT, previous_receipt)
    created = False
    partial = target.with_name(target.name + ".partial")
    if additions and receipt is None:
        if partial.exists():
            raise ValueError("Unresolved partial scratch store exists")
        with partial.open("x+b") as stream:
            set_sparse(stream)
            if not attrs(partial) & SPARSE_ATTRIBUTE:
                raise ValueError("Filesystem did not mark scratch store sparse")
            stream.truncate(logical_size)
            deallocate_zeros(stream, logical_size)
            stream.flush()
            os.fsync(stream.fileno())
        verify_sparse_allocation(partial, logical_size, [])
        created = True
        write_path = partial
    elif additions:
        write_path = target
    else:
        write_path = None
    if additions or not header_ready:
        if write_path is None:
            write_path = target
        with source.open("rb") as original, write_path.open("r+b") as staged:
            for row in additions:
                offset, length = row["store_offset"], row["compressed_bytes"]
                original.seek(offset)
                data = original.read(length)
                if len(data) != length or hashlib.sha256(data).hexdigest() != row["compressed_sha256"]:
                    raise ValueError(f"Source chunk differs from evidence: {offset}")
                staged.seek(offset)
                staged.write(data)
            if not header_ready:
                staged.seek(0)
                staged.write(header)
            staged.flush()
            os.fsync(staged.fileno())
        with write_path.open("rb") as staged:
            for row in additions:
                staged.seek(row["store_offset"])
                if hashlib.sha256(staged.read(row["compressed_bytes"])).hexdigest() != row["compressed_sha256"]:
                    raise ValueError(f"Staged chunk differs from source: {row['store_offset']}")
        if not attrs(write_path) & SPARSE_ATTRIBUTE:
            raise ValueError("Scratch store lost sparse attribute")
        verify_header(write_path, header)
        if created:
            write_path.replace(target)
    if not target.is_file() or target.stat().st_size != logical_size:
        raise ValueError("Scratch chunk store length is wrong")
    all_chunks = existing + additions
    physical, ranges = verify_sparse_allocation(target, logical_size, all_chunks, require_header=True)
    if not additions and receipt is not None and header_ready and receipt["schema_version"] == 2:
        print(json.dumps({"status": "verified_existing", "chunks": len(existing),
                          "logical_bytes": logical_size, "allocated_bytes": physical}))
        return
    digest = sha(evidence_path)
    staged_chunks = sorted(existing + [dict(row, evidence_sha256=digest) for row in additions],
                           key=lambda row: row["store_offset"])
    bundles = dict(receipt.get("bundles", {})) if receipt else {}
    bundles.update(selected_bundles)
    report = {"schema_version": 2, "status": "source_verified_sparse_chunks",
              "source_store_path": str(source), "store_path": str(target),
              "index_path": str(INDEX_STAGED), "index_sha256": expected_index_sha,
              "logical_bytes": logical_size, "allocation_size_bytes": physical,
              "compressed_file_size_bytes": allocated_bytes(target),
              "allocated_ranges": [{"offset": offset, "length": length} for offset, length in ranges],
              "sparse_attribute": True,
              "header": {"offset": 0, "length": HEADER_BYTES, "sha256": HEADER_SHA256},
              "previous_receipt": {"path": str(previous_receipt), "sha256": previous_sha}
              if previous_receipt else receipt.get("previous_receipt") if receipt else None,
              "chunks": staged_chunks, "bundles": bundles,
              "bootstrap_manifest_sha256": sha(BOOTSTRAP)}
    receipt_partial = RECEIPT.with_name(RECEIPT.name + ".partial")
    if receipt_partial.exists():
        raise ValueError("Unresolved partial chunk receipt exists")
    receipt_partial.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    receipt_partial.replace(RECEIPT)
    print(json.dumps({"status": report["status"], "new_chunks": len(additions),
                      "chunks": len(staged_chunks), "logical_bytes": logical_size,
                      "allocated_bytes": physical, "receipt": str(RECEIPT)}))


if __name__ == "__main__":
    main()

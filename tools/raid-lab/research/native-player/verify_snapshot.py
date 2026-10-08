"""Verify copied source bytes; optionally run isolated mock contract tests.

No installed game, native player, catalog, patch store, or private trial is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
INDEX = HERE / "source-index.json"
PYTHON_TESTS = (
    "test_mechanics_request.py",
    "test_mechanics_encounter_requests.py",
    "test_verify_tactical_trial.py",
    "test_verify_boss_tactical_trial.py",
)
NODE_TESTS = (
    "test_qte_policy.js",
    "test_cover_policy.js",
    "test_threat_observer.js",
)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def safe_relative(raw: object) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw or ":" in raw:
        raise ValueError(f"Unsafe path in source index: {raw!r}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"Unsafe path in source index: {raw!r}")
    return Path(*pure.parts)


def verify() -> tuple[dict, list[tuple[Path, Path]]]:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    if index.get("schemaVersion") != 1 or index.get("kind") != "research_source_snapshot":
        raise ValueError("Unexpected source-index schema")
    rows = index.get("files")
    if not isinstance(rows, list) or len(rows) != 74:
        raise ValueError("Snapshot source file count changed")
    seen_snapshot, seen_original, mapped = set(), set(), []
    for row in rows:
        relative = safe_relative(row.get("snapshotPath"))
        original = safe_relative(row.get("sourceWorkspaceRelativePath"))
        if relative in seen_snapshot or original in seen_original:
            raise ValueError("Duplicate snapshot or original source path")
        seen_snapshot.add(relative)
        seen_original.add(original)
        target = (HERE / relative).resolve(strict=True)
        if not target.is_relative_to(HERE) or not target.is_file() or target.is_symlink():
            raise ValueError(f"Source path escaped snapshot: {relative}")
        expected_hash, expected_size = row.get("sha256"), row.get("bytes")
        if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
            raise ValueError(f"Invalid hash for {relative}")
        if type(expected_size) is not int or expected_size < 0 or target.stat().st_size != expected_size:
            raise ValueError(f"Size mismatch for {relative}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"Hash mismatch for {relative}")
        mapped.append((target, original))
    packaging = index.get("packagingFiles")
    packaging_names = {"README.md", ".gitignore", ".gitattributes", "verify_snapshot.py"}
    if not isinstance(packaging, list) or {row.get("snapshotPath") for row in packaging} != packaging_names:
        raise ValueError("Snapshot packaging manifest changed")
    for row in packaging:
        name = row["snapshotPath"]
        target = HERE / name
        if (row.get("kind") != "authored_snapshot_packaging_not_copied_source" or
                target.is_symlink() or not target.is_file() or
                type(row.get("bytes")) is not int or target.stat().st_size != row["bytes"] or
                not isinstance(row.get("sha256"), str) or
                hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]):
            raise ValueError(f"Packaging file mismatch: {name}")
    expected_files = seen_snapshot | {Path(name) for name in
                                      ("README.md", "source-index.json", ".gitignore",
                                       ".gitattributes", "verify_snapshot.py")}
    actual_files = {path.relative_to(HERE) for path in HERE.rglob("*") if path.is_file()}
    if actual_files != expected_files:
        raise ValueError(f"Snapshot file set changed: extra={sorted(actual_files - expected_files)}, "
                         f"missing={sorted(expected_files - actual_files)}")
    return index, mapped


def run_contracts(mapped: list[tuple[Path, Path]]) -> None:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for the three optional policy contracts")
    with TemporaryDirectory(prefix="raid-lab-source-snapshot-") as directory:
        temp = Path(directory).resolve()
        for source, relative in mapped:
            target = (temp / relative).resolve()
            if not target.is_relative_to(temp):
                raise ValueError("Reconstructed source escaped temporary directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        work = temp / "tools/raid-lab/native-player"
        for name in PYTHON_TESTS:
            subprocess.run([sys.executable, "-m", "unittest", "-v", name.removesuffix(".py")],
                           cwd=work, check=True)
        for name in NODE_TESTS:
            subprocess.run([node, name], cwd=work, check=True)
    print(f"PASS: {len(PYTHON_TESTS)} Python mock suites and {len(NODE_TESTS)} Node policy contracts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", action="store_true",
                        help="reconstruct copied paths in a temporary directory and run mock contracts")
    args = parser.parse_args()
    index, mapped = verify()
    print(f"PASS: {len(mapped)} copied source files, "
          f"{sum(row['bytes'] for row in index['files'])} bytes, SHA-256/size/file-set verified")
    if args.tests:
        run_contracts(mapped)


if __name__ == "__main__":
    main()

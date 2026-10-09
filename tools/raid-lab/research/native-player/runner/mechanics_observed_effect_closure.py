"""Prepare and stage an exact native-observed monster effect catalog closure.

The caller supplies a native verification report and an exact installed asset
key. Only failed bundle requests in that report and that key's original
Addressables dependencies enter the evidence. Staging targets the private
scratch player and requires its current receipt SHA-256.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import UnityPy
import zstandard

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mechanics_profile_assets import (ARCHIVE, CLIENT_SHA, CORE, REGISTRY, ROOT,
                                     database, decode_body, sha, verify_bundle)
from mechanics_encounter_assets import selected_entry

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index

SANDBOX = ROOT / "tools/raid-lab/private/native-player-20261008a"
RESOURCE_RECEIPT = SANDBOX / "resource-chunks.json"
FAILED = re.compile(r"key='([^']+\.bundle)'", re.IGNORECASE)


def observed_bundles(verification: Path) -> list[str]:
    report = json.loads(verification.read_text(encoding="utf-8"))
    found = set()
    for item in report.get("errors", []):
        message = item.get("error", item.get("detail", ""))
        if "Chunk decompression failed" in message:
            found.update(FAILED.findall(message))
    if not found:
        raise ValueError("No exact native failed-bundle keys in verification")
    return sorted(found)


def prepare(profile_id: str, catalog_key: str, verification: Path,
            base_path: Path, output: Path) -> None:
    output = output.resolve()
    if output.exists() or not output.is_relative_to(HERE.resolve()):
        raise ValueError("Output must be a new native-player research JSON")
    if sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll") != CLIENT_SHA:
        raise ValueError("Installed client changed")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if (base.get("profile", {}).get("id") != profile_id or
            base.get("source", {}).get("registry_sha256") != sha(REGISTRY)):
        raise ValueError("Base monster closure is not current profile")
    observed = observed_bundles(verification)
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    entry = selected_entry(catalog, catalog_key, quality=0)
    if entry["assetType"] != "UnityEngine.GameObject" or not set(observed).issubset(entry["bundles"]):
        raise ValueError("Observed failed bundles do not share exact GameObject catalog closure")
    if len([name for name in entry["bundles"] if name.startswith("effect-spot-monster_library_assets_")]) != 1:
        raise ValueError("Observed effect has no unique original GameObject bundle")
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source_store = CORE / "chunk/store.cdb"
    verified, builtins = {}, {}
    with source_store.open("rb") as stream:
        for name in entry["bundles"]:
            row = verify_bundle(patch, index, name, source_store, stream,
                                zstandard.ZstdDecompressor())
            (verified if row["source"] == "patch_chunk_store" else builtins)[name] = row
    effect_bundle = next(name for name in entry["bundles"]
                         if name.startswith("effect-spot-monster_library_assets_"))
    if effect_bundle not in verified:
        raise ValueError("Original effect bundle has no verified source chunks")
    payload = decode_body(verified, effect_bundle, source_store)
    env = UnityPy.load(io.BytesIO(payload))
    if entry["internalId"] not in env.container:
        raise ValueError("Catalog internalId absent from decoded original effect bundle")
    asset = env.container[entry["internalId"]]
    if asset.type.name != "GameObject":
        raise ValueError("Catalog effect asset is not a GameObject")
    asset_name = asset.read_typetree().get("m_Name")
    if asset_name != catalog_key:
        raise ValueError("Decoded original effect GameObject name differs from catalog key")
    result = {"schema_version": 1, "status": "static_catalog_mapping_only",
              "scope": "native-observed GameObject and exact original Addressables dependencies",
              "profile": base["profile"],
              "source": {"client_sha256": CLIENT_SHA,
                         "registry_sha256": sha(REGISTRY),
                         "archive_sha256": sha(ARCHIVE),
                         "base_monster_closure_path": str(base_path),
                         "base_monster_closure_sha256": sha(base_path),
                         "native_verification_path": str(verification),
                         "native_verification_sha256": sha(verification),
                         "patch_catalog_sha256": sha(patch_path),
                         "addressables_catalog_sha256": sha(raw_path),
                         "chunk_index_sha256": sha(index_path)},
              "observed_failed_bundles": observed,
              "asset_entry": entry,
              "decoded_asset": {"bundle": effect_bundle,
                                "container_key": entry["internalId"],
                                "type": asset.type.name, "name": asset_name},
              "client_sha256": CLIENT_SHA,
              "catalog_sha256": sha(patch_path), "index_sha256": sha(index_path),
              "sandbox_patch_root_suffix": base["sandbox_patch_root_suffix"],
              "core_chunk_store": base["core_chunk_store"],
              "core_bootstrap_files": base["core_bootstrap_files"],
              "bundle_scope": sorted(verified), "verified_bundles": verified,
              "built_in_bundles": builtins,
              "limits": ["Audio bundle is an original Addressables dependency only; no playback path is restored.",
                         "Only exact observed effect and its catalog dependency graph are included.",
                         "This does not prove native combat or future dynamic resource completeness."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "observed": observed, "patch_bundles": len(verified),
                      "builtins": len(builtins)}))


def stage(profile_id: str, evidence_path: Path, verification: Path,
          base_path: Path, stage_receipt: Path, expected_before: str) -> None:
    if stage_receipt.exists() or not stage_receipt.resolve().is_relative_to(SANDBOX.resolve()):
        raise ValueError("Stage receipt exists or escapes private scratch")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if (evidence.get("profile", {}).get("id") != profile_id or
            evidence["source"]["registry_sha256"] != sha(REGISTRY) or
            evidence["source"]["base_monster_closure_sha256"] != sha(base_path) or
            evidence["source"]["native_verification_sha256"] != sha(verification) or
            evidence["observed_failed_bundles"] != observed_bundles(verification)):
        raise ValueError("Effect evidence differs from current source/native observation")
    before = sha(RESOURCE_RECEIPT)
    if before != expected_before.lower():
        raise ValueError("Scratch receipt differs from exact expected pre-stage state")
    command = [sys.executable, str(HERE / "stage_resource_chunks.py"),
               "--evidence", str(evidence_path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    receipt = json.loads(RESOURCE_RECEIPT.read_text(encoding="utf-8"))
    for name, row in evidence["verified_bundles"].items():
        if receipt["bundles"].get(name) != [chunk["hash"] for chunk in row["chunks"]]:
            raise ValueError(f"Staged receipt omitted source-bound bundle: {name}")
    report = {"schema_version": 1, "status": "source_bound_observed_effect_staged",
              "profile_id": profile_id, "catalog_key": evidence["asset_entry"]["key"],
              "source_evidence_path": str(evidence_path),
              "source_evidence_sha256": sha(evidence_path),
              "before_resource_receipt_sha256": before,
              "after_resource_receipt_sha256": sha(RESOURCE_RECEIPT),
              "previous_receipt": receipt["previous_receipt"],
              "staging_command": command,
              "staging_result": completed.stdout.strip(),
              "limit": "Source-bound sparse chunks only; native combat unverified."}
    stage_receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage_receipt": str(stage_receipt), "sha256": sha(stage_receipt),
                      "resource_receipt_sha256": sha(RESOURCE_RECEIPT)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_id")
    parser.add_argument("--catalog-key", required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--base-closure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage-receipt", type=Path)
    parser.add_argument("--expected-before-receipt-sha256")
    args = parser.parse_args()
    if args.stage_receipt:
        if not args.expected_before_receipt_sha256:
            raise ValueError("Stage requires exact expected prior resource receipt SHA")
        stage(args.profile_id, args.output, args.verification, args.base_closure,
              args.stage_receipt, args.expected_before_receipt_sha256)
    else:
        prepare(args.profile_id, args.catalog_key, args.verification,
                args.base_closure, args.output)


if __name__ == "__main__":
    main()

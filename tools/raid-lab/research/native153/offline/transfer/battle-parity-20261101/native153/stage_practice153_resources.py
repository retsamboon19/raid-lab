"""Stage source-selected current practice asset closure into private sparse store.

Exact wave/model fields supply keys. Selected serialized AssetReference GUIDs are
followed, capped at128 assets. Original missing optional numeric effect keys are
recorded, never replaced with invented aliases. No native process is started.
"""
import hashlib
import json
import os
from pathlib import Path
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
from extract_practice_geometry153 import asset_rows, sha
from build_logged_bundle_evidence import database, key_bundles, verify_bundle
from chunk_index import decode_index
from mechanics_geometry_source import extract_objects


def refs(value, path=""):
    out = []
    if isinstance(value, dict):
        if value.get("m_AssetGUID"):
            out.append({"field": path, "guid": value["m_AssetGUID"]})
        for key, child in value.items():
            out.extend(refs(child, path + "." + key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.extend(refs(child, path + "[" + str(index) + "]"))
    return out


def main():
    output = SANDBOX / "practice-mechanical-resources1.json"
    supplement_path = HERE / "practice-additional-geometry-source.json"
    if output.exists() or supplement_path.exists():
        raise FileExistsError("Preserve source/staging receipts")
    raw = CORE / "raw/6a46ed93faa7c6fd01f1aa66253becc7.db"
    catalog, patch = database(raw), database(CORE / "catalog.ndb")
    index = decode_index((CORE / "chunk/store.cdb.idx").read_bytes())
    wave = json.loads((HERE / "practice-wave-source.json").read_text())["waveRow"]
    monsters = json.loads((HERE / "practice-monsters-source.json").read_text())
    roots = {wave["PointData"], wave["PointDataFly"], wave["BackgroundName"],
             *[w["WavePath"] for w in wave["WaveData"] if w["WavePath"]]}
    roots.update("SpotMonster/" + m["MonPrefab"] for m in monsters["models"])
    map_candidates = {"SpotMonsterMap/" + m["MonPrefab"] + "_map" for m in monsters["models"]}
    roots.update("ExternalBehavior/spot/" + m["SpotAi"] for m in monsters["monsters"])
    additions = {"ingame_root": "dd9e13d8e49f62f43b3bf66041b895df",
                 "aim_ui_ref": "5adcb72651300194487f5d42daa0cf56",
                 "character_controller": "0664939859296d2458a288ef0f48d206",
                 "projectile_controller": "0b644f07bd233ed48b06b2fca232d580",
                 "dynamic_controller": "f4d6edc2e0264294c9e4376a207b86ce",
                 "skill_director": "84a4ec251afe42241983764e0c1ec5c8"}
    roots.update(additions.values())
    numeric_effect_keys = {"ScriptableData/Effect/Monster/SpotEffect/" + str(m["Id"])
                           for m in monsters["monsters"]}
    numeric_effect_keys.update("ScriptableData/Effect/Monster/SpotSkill/" + str(s["SkillId"])
                              for m in monsters["monsters"] for s in m["SkillData"] if s["SkillId"])
    missing = []
    for key in sorted(numeric_effect_keys | map_candidates):
        if asset_rows(catalog, key):
            roots.add(key)
        else:
            missing.append(key)
    verified, payloads, entries, serialized, references, extra_geometry = {}, {}, {}, [], [], {}
    environments = {}
    source_store = CORE / "chunk/store.cdb"
    decoder = zstandard.ZstdDecompressor()
    pending = list(sorted(roots))
    done = set()
    text_assets = []
    with source_store.open("rb") as source:
        def body(name):
            if name not in verified:
                verified[name] = verify_bundle(patch, index, name, source_store, source, decoder)
            if name not in payloads:
                row = verified[name]
                if row["source"] == "installed_builtin":
                    payloads[name] = Path(row["path"]).read_bytes()
                else:
                    chunks = []
                    for ch in row["chunks"]:
                        source.seek(ch["store_offset"])
                        chunks.append(decoder.decompress(source.read(ch["compressed_bytes"])))
                    payloads[name] = b"".join(chunks)
            return payloads[name]

        while pending:
            key = pending.pop(0)
            if key in done:
                continue
            done.add(key)
            if len(done) > 128:
                raise ValueError("Stop bounded selected-asset reference closure at128")
            rows, names = key_bundles(catalog, key)
            entries[key] = rows
            for name in names:
                if name not in verified:
                    verified[name] = verify_bundle(patch, index, name, source_store, source, decoder)
            for selected in asset_rows(catalog, key):
                # Direct dependency containers must include the original internalId.
                direct = [r[0] for r in catalog.execute('''select i.internal_id from key_entries ke
                    join entries e on e.rowid=ke.entry_rowid join internal_ids i on i.rowid=e.internal_id_rowid
                    where ke.key_rowid=?''', (selected["dependency_rowid"],)) if r[0].endswith(".bundle")]
                matches = []
                for name in direct:
                    data = body(name)
                    if name not in environments:
                        environments[name] = UnityPy.load(data)
                    env = environments[name]
                    objects = {o.path_id: o for o in env.objects}
                    # Parse the original AssetBundle map directly. UnityPy's aggregate
                    # env.container mutates its CAB registry while resolving dependencies.
                    # The selected native target must be a local object in this bundle.
                    target_ids = [row[1]["asset"]["m_PathID"] for obj in objects.values()
                                  if obj.type.name == "AssetBundle"
                                  for row in obj.read_typetree().get("m_Container", [])
                                  if row[0] == selected["internal_id"] and row[1]["asset"]["m_FileID"] == 0]
                    if target_ids:
                        if len(target_ids) != 1 or target_ids[0] not in objects:
                            raise ValueError("Ambiguous original local container target")
                        matches.append((name, data, env, objects[target_ids[0]]))
                if len(matches) != 1:
                    raise ValueError("Original asset internalId not uniquely present " + key)
                name, data, env, target_obj = matches[0]
                objects = {o.path_id: o for o in env.objects}
                targets = ([target_obj] if target_obj.type.name != "GameObject" else
                           [o for o in env.objects if o.type.name == "MonoBehaviour"])
                asset_refs = []
                for obj in targets:
                    if obj.type.name == "TextAsset":
                        typed = obj.read()
                        content = typed.m_Script
                        content = content.encode("utf-8", "surrogateescape") if isinstance(content, str) else bytes(content)
                        text_assets.append({"catalog_key": key, "internal_id": selected["internal_id"],
                                            "name": typed.m_Name, "bytes": len(content),
                                            "sha256": hashlib.sha256(content).hexdigest(),
                                            "text": content.decode("utf-8")})
                    elif obj.type.name == "MonoBehaviour":
                        fields = obj.read_typetree()
                        script_ref = fields.get("m_Script", {})
                        script_obj = objects.get(script_ref.get("m_PathID")) if not script_ref.get("m_FileID") else None
                        script = script_obj.read_typetree() if script_obj else None
                        found = refs(fields)
                        asset_refs.extend(found)
                        serialized.append({"catalog_key": key, "internal_id": selected["internal_id"],
                                           "bundle": name, "path_id": obj.path_id,
                                           "script": script, "fields": fields, "asset_references": found})
                for ref in asset_refs:
                    ref_rows = asset_rows(catalog, ref["guid"])
                    if not ref_rows:
                        raise ValueError("Original selected AssetReference absent " + str(ref))
                    references.append({"from_key": key, **ref, "asset_rows": ref_rows})
                    if ref["guid"] not in done and ref["guid"] not in pending:
                        pending.append(ref["guid"])
                for role, guid in additions.items():
                    if key == guid:
                        extra_geometry[role] = {"catalog_key": key, "selected_asset": selected,
                                                "bundle_name": name, "decoded_sha256": hashlib.sha256(data).hexdigest(),
                                                **extract_objects(data, role)}
        chunks = {ch["store_offset"]: ch for b in verified.values() if b["source"] == "patch_chunk_store" for ch in b["chunks"]}
        copied = skipped = 0
        with (TARGET / "chunk/store.cdb").open("r+b") as target:
            for offset, ch in sorted(chunks.items()):
                target.seek(offset)
                if hashlib.sha256(target.read(ch["compressed_bytes"])).hexdigest() == ch["compressed_sha256"]:
                    skipped += 1
                    continue
                source.seek(offset)
                packed = source.read(ch["compressed_bytes"])
                if hashlib.sha256(packed).hexdigest() != ch["compressed_sha256"]:
                    raise ValueError("Verified source changed")
                target.seek(offset)
                target.write(packed)
                copied += 1
            target.flush()
            os.fsync(target.fileno())
        with (TARGET / "chunk/store.cdb").open("rb") as target:
            for offset, ch in chunks.items():
                target.seek(offset)
                if hashlib.sha256(target.read(ch["compressed_bytes"])).hexdigest() != ch["compressed_sha256"]:
                    raise ValueError("Copied chunk readback differs")
    for row in verified.values():
        if row["source"] == "installed_builtin":
            path = SANDBOX / "NIKKE/NIKKE/game" / Path(row["path"]).relative_to(ROOT / "NIKKE/NIKKE/game")
            if sha(path) != row["sha256"]:
                raise ValueError("Staged builtin differs")
    provenance = {"clientSha256": json.loads((HERE / "practice-theme-source.json").read_text())["clientSha256"],
                  "catalogSha256": sha(CORE / "catalog.ndb"), "rawCatalogSha256": sha(raw),
                  "indexSha256": sha(CORE / "chunk/store.cdb.idx"),
                  "waveReceiptSha256": sha(HERE / "practice-wave-source.json"),
                  "monsterReceiptSha256": sha(HERE / "practice-monsters-source.json")}
    supplement = {"schemaVersion": 1, "source": provenance, "bundles": extra_geometry,
                  "nativeLoaded": False, "battleStarted": False}
    supplement_path.write_text(json.dumps(supplement, indent=2) + "\n")
    result = {"schemaVersion": 1, "source": provenance, "originalRootKeys": sorted(roots),
              "entries": entries, "verifiedBundles": verified, "serializedAssets": serialized,
              "originalTextAssets": text_assets, "serializedAssetReferences": references,
              "absentDerivedOptionalKeys": missing, "copiedNewChunks": copied,
              "existingChunksReadbackOnly": skipped, "totalVerifiedChunks": len(chunks),
              "compressedBytes": sum(c["compressed_bytes"] for c in chunks.values()),
              "additionalGeometryReceiptSha256": sha(supplement_path),
              "nativeLoaded": False, "battleStarted": False,
              "limits": ["Absent numeric effect keys do not prove absence of an original dynamic default loader.",
                         "Derived SpotMonsterMap keys are staged only when present; no map alias is invented.",
                         "No original skill-default key is guessed or substituted.",
                         "Full catalog closures retain original transitively bundled bytes, including incidental cosmetic data.",
                         "Dynamic runtime-selected keys not referenced by these original assets remain unproven."]}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"path": str(output), "sha256": sha(output), "assets": len(done), "bundles": len(verified),
                      "newChunks": copied, "reusedChunks": skipped, "bytes": result["compressedBytes"]}))


if __name__ == "__main__":
    main()

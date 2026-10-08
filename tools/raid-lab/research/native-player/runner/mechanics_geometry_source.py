"""Extract source-bound serialized geometry for the synthetic Kraken mechanics trial.

Reads only installed patch catalog/chunks and retained wave-table evidence. Does not
stage bundles, launch Unity, or synthesize runtime camera/aim coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import UnityPy
import zstandard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/core"
WAVES = ROOT / "tools/raid-lab/private/special-tables/InterceptWaves.json"
CURRENT_TABLES = ROOT / "tools/raid-lab/private/native-current-tables-2df7134a.zip"
DEFAULT_OUTPUT = HERE / "mechanics-geometry-source.json"

sys.path.insert(0, str(HERE))
from build_logged_bundle_evidence import database, key_bundles

sys.path.insert(0, str(ROOT / "transfer"))
from chunk_index import decode_index

KEYS = {
    "spot_camera": ("SpotCameraControl", "spotpresentationbase_assets_spotcameracontrol_1fa9271810742a80a6706a17a6471efa.bundle"),
    "ui_aim": ("UIAimControll", "spotpresentationbase_assets_uiaimcontroll_ad5876c5b78759f73d1e61ed545e1d1c.bundle"),
    "character_map": ("SpotCharacterMap", "spotpresentationbase_assets_spotcharactermap_8b92b5fb6d036a016a1a0f45069523f3.bundle"),
    "auto_camera": ("AutoModeCameraControl", "spotpresentationbase_assets_automodecameracontrol_bb4567869113aa10675190027f26030b.bundle"),
    "spot_setting": ("SpotSetting", "scriptabledata-spotsetting_assets_spotsetting_8b6498278a79093ff55e30d57f2903b1.bundle"),
    "ui_canvas_control": ("UICanvasControl", "spotpresentationbase_assets_uicanvascontrol_c104524f915540d7135395c4c22216e6.bundle"),
    "overlay_canvas": ("Canvas(Screen Space - Overlay)", "spotpresentationbase_assets_canvas(screenspace-overlay)_c718872bf3dcc98f66d499570bdcf30e.bundle"),
    "kraken_background_hd": ("sbg_oceanbbg004_001", "spotbackground(hd)_assets_sbg_oceanbbg004_001_72f9fb058e5abceb2ee382b9d7c35236.bundle"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ptr_id(value: object) -> int | None:
    if isinstance(value, dict) and value.get("m_FileID") == 0:
        return value.get("m_PathID")
    return None


def select_component_fields(class_name: str, data: dict) -> dict:
    if class_name == "SpotSetting":
        names = ("UseAutoModeCamera", "AimVerticalFov", "AimHorizontalFov",
                 "AimSensitive", "AimCameraSensitive", "AimPositionInitOffsetHeight",
                 *(f"AimStartPosition{i}" for i in range(1, 6)))
    elif class_name == "SpotSingleMap":
        names = ("Cover1", "Cover2", "Cover3", "Cover4", "Cover5",
                 "LensSettings", "UseOverlay", "rootCover", "rootGround")
    elif class_name == "CinemachineVirtualCamera":
        names = ("m_Priority", "m_LookAt", "m_Follow", "m_Lens", "m_ComponentOwner")
    elif class_name == "SpotCharacterMap":
        names = ("CharacterPosParent", "_characterPosObjList", "CameraPosObjList",
                 "_cameraList", "ShootingZone", "IsLockedCamRotate")
    elif class_name == "SpotCharacterMapCamera":
        names = ("AimCamera", "HideCamera")
    elif class_name == "SpotCameraControl":
        names = ("_spotCamera", "_shakes")
    elif class_name == "UIAimControll":
        names = ("_temp", "TestGameAim", "AimSpeed", "MinRange", "AimLevel",
                 "_AimUIRef", "_prefabUIAim", "_uiThemeType")
    elif class_name == "UIAim":
        names = ("_GameAim", "_indicatorElement", "_canvasGroup")
    elif class_name == "AutoModeCameraController":
        names = tuple(k for k in data if "camera" in k.lower() or "aim" in k.lower())
    elif class_name == "UICanvasControl":
        names = tuple(k for k in data if k.endswith("Ref"))
    elif class_name in ("CanvasScaler", "SpotCanvasScalerMatchSetter", "UISpotCanvas"):
        names = tuple(k for k in data if not k.startswith("m_") or k in
                      ("m_UiScaleMode", "m_ReferenceResolution", "m_ScreenMatchMode",
                       "m_MatchWidthOrHeight", "m_ScaleFactor", "m_ReferencePixelsPerUnit"))
    else:
        names = ()
    return {name: data[name] for name in names if name in data}


def include_object(bundle_role: str, name: str) -> bool:
    if bundle_role == "kraken_background_hd":
        low = name.lower()
        return (low in {"camera_position", "aim_position", "character_position",
                        "hide_position", "cover", "cover_1", "cover_2", "cover_3",
                        "cover_4", "cover_5", "sbg_oceanbbg004_001"})
    return True


def extract_objects(payload: bytes, role: str) -> dict:
    env = UnityPy.load(io.BytesIO(payload))
    objects = {obj.path_id: obj for obj in env.objects}
    names = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            names[obj.path_id] = obj.read_typetree().get("m_Name", "")
    transform_to_go = {}
    for obj in env.objects:
        if obj.type.name in ("Transform", "RectTransform"):
            data = obj.read_typetree()
            transform_to_go[obj.path_id] = ptr_id(data.get("m_GameObject"))
    game_objects = []
    components = []
    for obj in env.objects:
        typ = obj.type.name
        if typ == "GameObject":
            data = obj.read_typetree()
            name = data.get("m_Name", "")
            if not include_object(role, name):
                continue
            component_ids = [ptr_id(row.get("component")) for row in data.get("m_Component", [])]
            transform = next((objects[cid] for cid in component_ids
                              if cid in objects and objects[cid].type.name in
                              ("Transform", "RectTransform")), None)
            row = {"path_id": obj.path_id, "name": name, "component_path_ids": component_ids}
            if transform is not None:
                t = transform.read_typetree()
                parent_id = ptr_id(t.get("m_Father"))
                row["transform"] = {
                    "path_id": transform.path_id, "type": transform.type.name,
                    "parent_transform_path_id": parent_id,
                    "parent_game_object_path_id": transform_to_go.get(parent_id),
                    "parent_name": names.get(transform_to_go.get(parent_id)),
                    "local_position": t.get("m_LocalPosition"),
                    "local_rotation": t.get("m_LocalRotation"),
                    "local_scale": t.get("m_LocalScale"),
                }
                if transform.type.name == "RectTransform":
                    row["transform"].update({k: t.get(k) for k in
                        ("m_AnchorMin", "m_AnchorMax", "m_AnchoredPosition",
                         "m_SizeDelta", "m_Pivot")})
            game_objects.append(row)
        elif typ == "Canvas":
            data = obj.read_typetree()
            components.append({"path_id": obj.path_id, "type": "Canvas",
                               "game_object_path_id": ptr_id(data.get("m_GameObject")),
                               "game_object_name": names.get(ptr_id(data.get("m_GameObject"))),
                               "fields": {k: data.get(k) for k in
                                 ("m_RenderMode", "m_Camera", "m_PlaneDistance",
                                  "m_TargetDisplay", "m_OverrideSorting")}})
        elif typ == "Camera":
            data = obj.read_typetree()
            components.append({"path_id": obj.path_id, "type": "Camera",
                               "game_object_path_id": ptr_id(data.get("m_GameObject")),
                               "game_object_name": names.get(ptr_id(data.get("m_GameObject"))),
                               "fields": {k: data.get(k) for k in
                                 ("m_projectionMatrixMode", "m_GateFitMode", "m_SensorSize",
                                  "m_LensShift", "m_FocalLength", "m_NormalizedViewPortRect",
                                  "near clip plane", "far clip plane", "field of view",
                                  "orthographic", "orthographic size", "m_TargetDisplay")}})
        elif typ == "MonoBehaviour":
            data = obj.read_typetree()
            script = objects.get(ptr_id(data.get("m_Script")))
            if script is None or script.type.name != "MonoScript":
                continue
            script_data = script.read_typetree()
            class_name = script_data.get("m_ClassName", "")
            fields = select_component_fields(class_name, data)
            if fields:
                components.append({"path_id": obj.path_id, "type": class_name,
                                   "game_object_path_id": ptr_id(data.get("m_GameObject")),
                                   "game_object_name": names.get(ptr_id(data.get("m_GameObject"))),
                                   "fields": fields})
    return {"game_objects": game_objects, "components": components}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite existing geometry evidence: {output}")
    patch_path = CORE / "catalog.ndb"
    patch = database(patch_path)
    raw_hash, raw_ext = patch.execute(
        "select hash,extension from files_rawtype where key='catalog.db'").fetchone()
    raw_path = CORE / "raw" / (raw_hash.hex() + raw_ext)
    catalog = database(raw_path)
    index_path = CORE / "chunk/store.cdb.idx"
    index = decode_index(index_path.read_bytes())
    source = CORE / "chunk/store.cdb"
    decoder = zstandard.ZstdDecompressor()
    bundles = {}
    with source.open("rb") as stream:
        for role, (key, name) in KEYS.items():
            entries, closure = key_bundles(catalog, key)
            if name not in closure:
                raise ValueError(f"Selected bundle is not a dependency of {key}: {name}")
            row = patch.execute("select file_id from files_chunktype where key=?", (name,)).fetchone()
            if row is None:
                raise ValueError(f"Bundle is absent from installed patch catalog: {name}")
            payload = bytearray()
            chunk_receipts = []
            for chunk_hash, packed_size, decoded_size, bundle_offset in patch.execute(
                """select c.hash,c.compressed_size,c.original_size,m.file_offset
                   from chunk_file_map m join chunks c on c.chunk_id=m.chunk_id
                   where m.file_id=? order by m.file_offset""", row):
                position, length = index[chunk_hash]
                if length != packed_size or bundle_offset != len(payload):
                    raise ValueError(f"Invalid chunk bounds/order: {name}")
                stream.seek(position)
                packed = stream.read(length)
                decoded = decoder.decompress(packed)
                if len(packed) != length or len(decoded) != decoded_size:
                    raise ValueError(f"Invalid installed chunk: {name}")
                payload.extend(decoded)
                chunk_receipts.append({"hash": chunk_hash.hex(), "store_offset": position,
                                       "compressed_bytes": length,
                                       "compressed_sha256": digest(packed),
                                       "decoded_bytes": decoded_size})
            if not payload.startswith(b"UnityFS"):
                raise ValueError(f"Decoded bundle is not UnityFS: {name}")
            bundles[role] = {"catalog_key": key, "catalog_entries": entries,
                             "bundle_name": name, "decoded_bytes": len(payload),
                             "decoded_sha256": digest(payload), "chunks": chunk_receipts,
                             **extract_objects(bytes(payload), role)}
    waves = json.loads(WAVES.read_text(encoding="utf-8"))
    row = next((x for x in waves if x.get("StageId") == 6302009), None)
    if row is None or row.get("BackgroundName") != "sbg_oceanbbg004_001":
        raise ValueError("Historical Wave 6302009 does not bind selected background")
    with zipfile.ZipFile(CURRENT_TABLES) as archive:
        current_entry = archive.read("WaveDataTable.wave_Intercept_001.mpk")
    result = {
        "schema_version": 1, "status": "serialized_source_geometry_only",
        "installed_client_sha256": sha(ROOT / "NIKKE/NIKKE/game/GameAssembly.dll"),
        "source": {"patch_catalog_sha256": sha(patch_path),
                   "addressables_catalog_sha256": sha(raw_path),
                   "chunk_index_sha256": sha(index_path),
                   "wave_json_path": str(WAVES), "wave_json_sha256": sha(WAVES),
                   "current_table_archive_path": str(CURRENT_TABLES),
                   "current_table_archive_sha256": sha(CURRENT_TABLES),
                   "current_wave_entry_sha256": digest(current_entry)},
        "wave_6302009_historical_extracted_row": {
            k: row.get(k) for k in ("StageId", "GroupId", "SpotMod", "BattleTime",
                                   "PointData", "PointDataFly", "BackgroundName", "Theme")},
        "wave_row_limit": "Wave row is a retained earlier table extraction; current wave MPK bytes are hashed but this script does not decode that row. Trial 43 loaded Wave 6302009 in the installed client.",
        "bundles": bundles,
        "limits": ["Serialized local transforms are not final Unity world positions after map/camera methods run.",
                   "No screen size, safe area, canvas scale, target camera pose or per-tick aim state is inferred.",
                   "No Unity scene, rendering, player or DLL is launched."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "sha256": sha(output),
                      "bundles": len(bundles),
                      "game_objects": sum(len(x["game_objects"]) for x in bundles.values())}))


if __name__ == "__main__":
    main()

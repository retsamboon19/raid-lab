"""Create the source-bound practice loading adapter; no original assets edited."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    receipt_path = HERE / 'practice-geometry-source.json'
    receipt_sha = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    assert receipt_sha == 'ff3d69914a3735a7bd9de5493e687af30b8ef4b9ad35845e7446c19533435449'
    source = (HERE / 'runtime-review2/mechanics_geometry_runtime.js').read_text()
    start = source.index('  const source =')
    end = source.index('  if (!present(management)', start)
    source = source[:start] + '''  const source = globalThis.MECHANICS_GEOMETRY_SOURCE;
  const receipt = globalThis.MECHANICS_GEOMETRY_SOURCE_SHA256;
  const client = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2";
  const present = x => x != null && !x.isNull();
  const requireRef = (x, name) => { if (!present(x)) throw new Error(name + " is null"); return x; };
  const call = (method, instance = null, args = []) => invokeChecked(method, instance, args);
  if (!source || source.installed_client_sha256!==client ||
      receipt!=="''' + receipt_sha + '''" || source.theme_mode!==9 || source.theme_key!==0 ||
      source.bundles.practice_background_hd.catalog_key!=="sbg_tower_001")
    throw new Error("Exact153 normal ShootingRange geometry source binding changed");
  const backgroundKey="sbg_tower_001";
''' + source[end:]
    source = source.replace('commonGeometryReceiptSha256:encounterGeometry?source.source.common_geometry_sha256:receipt,',
                            'commonGeometryReceiptSha256:receipt,')
    source = source.replace('const bundleRoles = ["ui_canvas_control",',
                            'const bundleRoles = ["ingame_root", "ui_canvas_control",')
    start = source.index('  // Exact Intercept.asset')
    end = source.index('  const addressables =', start)
    source = source[:start] + '''  // Resolve each selected mechanical object from this exact practice theme.
  // This first loading adapter registers eight controls. Other mechanically
  // unresolved presentations are an explicit remaining parity requirement.
  function themeParent(key) {
    const rows=source.hierarchy.filter(layer=>layer.parent_asset.primary_key===key);
    if (rows.length!==1 || rows[0].parent_asset.asset_type!=="UnityEngine.GameObject")
      throw new Error("Missing/ambiguous original practice parent "+key);
    return rows[0];
  }
  const ingameLayer=themeParent("IngameObject"), prefabLayer=themeParent("PrefabControl");
  function themeChild(layer,key) {
    const matches=layer.children.flatMap(child=>child.asset_rows
      .filter(row=>row.primary_key===key && row.asset_type==="UnityEngine.GameObject")
      .map(row=>({key:child.asset_guid,id:row.internal_id,parent:layer.parent_guid})));
    if (matches.length!==1) throw new Error("Missing/ambiguous original practice child "+key);
    return matches[0];
  }
  const supplementalAssets = {
    ingame_root:{key:ingameLayer.parent_guid,id:ingameLayer.parent_asset.internal_id},
    prefab_root:{key:prefabLayer.parent_guid,id:prefabLayer.parent_asset.internal_id},
    monster_controller:themeChild(prefabLayer,"MonsterObjectController"),
    summon_controller:themeChild(prefabLayer,"SummonPrefabController"),
    qte_controller:themeChild(prefabLayer,"QuickTimeEventPrefabController")
  };
  for (const role of ["ui_canvas_control","character_map","spot_camera","auto_camera"]) {
    const row=source.bundles[role];
    const nativeChild=themeChild(ingameLayer,row.catalog_key);
    if (nativeChild.id!==row.selected_asset.internal_id)
      throw new Error("Practice theme child differs from serialized source "+role);
  }
  const aimLayer=source.hierarchy.find(layer=>layer.parent_guid===
    source.bundles.camera_one_canvas.selected_asset.internal_id);
  const aimChild=themeChild(aimLayer,source.bundles.ui_aim.catalog_key);
  if (aimChild.id!==source.bundles.ui_aim.selected_asset.internal_id)
    throw new Error("Practice aim control theme selection differs");
''' + source[end:]
    source = source.replace('    if (canvasRefs[role]) parent = state.instances.ui_canvas_control;',
                            '''    // Theme ParentObject instances are direct children of PresentationRoot.
    // UICanvasControl discovers the originals through the GUID registry.
    if (["ui_canvas_control","character_map","spot_camera","auto_camera"].includes(role))
      parent = state.instances.ingame_root;''')
    source = source.replace('function startMechanicsGeometryRuntime(', 'function startPracticeGeometryRuntime(')
    source = source.replace('function finishMechanicsGeometryRuntime(', 'function finishPracticeGeometryRuntime(')
    source = source.replace('sceneLoadedByHelper: false,\n        sourceReceiptSha256: receipt',
                            'sceneLoadedByHelper: false, fullMechanicalCoverageVerified:false,\n        sourceReceiptSha256: receipt')
    source = source[source.index('function startPracticeGeometryRuntime'):]
    source = '''// Current153 original ShootingRange geometry loading candidate.
// Source-bound mechanical subset, not a complete combat coverage claim.
// Original native InstantiateAsync/registration/OnLoad/camera/aim methods run.
// Required globals: Il2Cpp, invokeChecked, intArg, onMain, source receipt.
''' + source
    path = HERE / 'practice_geometry.js'
    with path.open('x', encoding='utf-8') as sink:
        sink.write(source)
    print(json.dumps({'output': str(path), 'sourceReceiptSha256': receipt_sha,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()

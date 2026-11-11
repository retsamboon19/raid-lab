"""Select original presentation assets for a native encounter, without a player."""
from pathlib import Path
import copy
import hashlib
import json

HERE=Path(__file__).resolve().parent
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def loaded_map_name(encounter):
    if encounter['id']!='anomaly:2':return encounter['backgroundName']
    proof=read(HERE/'interception-map-identities153.json')
    records=[r for r in proof['records'] if r['encounterId']==encounter['id']]
    if len(records)!=2 or any(r['backgroundKey']!=encounter['backgroundName'] for r in records):
        raise ValueError('Exact original Indivilia map prefab identities required')
    chain=proof['indiviliaLoadedMapComponentChain']
    phase=next(r for r in chain if 'phaseMaps' in r['data'])
    first=next(r['Map']['m_PathID'] for r in phase['data']['phaseMaps'] if r['Phase']==1)
    child=next(r for r in chain if r['pathId']==str(first))
    if not all(k in child['data'] for k in ('rootCover','Cover1','Cover5','LensSettings')):
        raise ValueError('Original phase-one map component is not the source battle map')
    name=child['gameObjectName']
    if not all(any(g['name']==name for g in r['gameObjects']) for r in records):
        raise ValueError('Original HD/SD phase-one map identity disagrees')
    return name

def prepare_geometry(release,encounter):
    original=read(release.directory/'frozen/frozen-geometryInput.json')
    bindings=read(HERE/'theme-bindings153.json')
    if digest(HERE/'theme-catalog153.json')!=bindings['themeCatalogueSha256']:
        raise ValueError('Original theme catalogue changed')
    names={1:'Campaign',4:'Defense',7:'Intercept',9:'ShootingRange',10:'BaseDefense',
           16:'SoloRaid_Common',17:'SoloRaid_Trial',24:'SoloRaid_Museum',25:'SoloRaid_Museum_Nolimit'}
    name=names.get(encounter['processType'])
    if name is None or name not in bindings['themes']:
        raise ValueError('Original presentation selection is not mapped for this process')
    theme=bindings['themes'][name]
    key=encounter['transporter']['<UITheme>k__BackingField']
    selected=theme['variants'].get(str(key),theme['variants']['0'])
    if set(selected['differences'])-{'UIAimControll'}:
        raise ValueError('Encounter requires different original mechanical presentation objects')
    loaded=loaded_map_name(encounter)
    result=copy.deepcopy(original)
    result.update(theme_mode=encounter['processType'],theme_key=key,hierarchy=selected['hierarchy'],
        encounterId=encounter['id'],backgroundKey=encounter['backgroundName'],loadedMapName=loaded)
    result['bundles'].pop('practice_background_hd',None)
    if 'UIAimControll' in selected['differences']:
        override=read(HERE/'aim-ce004-source153.json')
        children=[asset for layer in selected['hierarchy'] for child in layer['children'] for asset in child['asset_rows']
                  if asset['primary_key']==override['catalog_key']]
        if len(children)!=1 or children[0]['internal_id']!=override['selected_asset']['internal_id']:
            raise ValueError('Original aim override does not match the selected theme')
        result['bundles']['ui_aim']=override
    evidence={'encounterId':encounter['id'],'processType':encounter['processType'],'uiTheme':key,
        'backgroundKey':encounter['backgroundName'],'loadedMapName':loaded,'loadedMapIdentityReceiptSha256':digest(HERE/'interception-map-identities153.json'),'themeAssetKey':theme['assetKey'],
        'themeAssetId':theme['assetId'],'themeBundleSha256':theme['bundleSha256'],
        'themeBindingsSha256':digest(HERE/'theme-bindings153.json'),
        'commonMechanicalPrefabsVerified':True,'originalAimVariant':result['bundles']['ui_aim']['catalog_key'],
        'originalSerializedReferencesRetained':True}
    return result,evidence

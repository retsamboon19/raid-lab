"""Stage only exact observed real-character skeleton closure from current signed DP.

No native launch, aliases, fallback replacement, or installed-source mutation.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from extract_practice_geometry153 import asset_rows
from build_logged_bundle_evidence import database, key_bundles, verify_bundle
from chunk_index import decode_index
from copy_complete153_store import ensure_closed, record_stat, private_path
import zstandard

SANDBOX = ROOT / 'tools/raid-lab/private/native-player153-20261101'
SOURCE = ROOT / 'NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/dp'
TARGET = SANDBOX / 'profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/dp'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    output = SANDBOX / 'practice-dp-skeleton-resources1.json'
    if output.exists() or TARGET.exists():
        raise FileExistsError('Preserve existing DP resource staging')
    private_path(TARGET)
    ensure_closed(44952)
    archive = SANDBOX / 'practice-output9'
    verification = archive / 'verification.json'
    if sha(verification) != '944d2ed52e4f2dde420db4d61cfbdbd1c7c8ed65bd1bb8958009aa1e4038f45f':
        raise ValueError('Actual original skeleton-key observation differs')
    events = [json.loads(line) for line in (archive / 'scene-events.jsonl').read_text().splitlines()]
    selected = [row for row in events if row.get('status') == 'original_skeleton_addresses_returned' and row['resourceId'] != 999]
    if len(selected) != 5 or [(r['resourceId'], r['costumeIndex']) for r in selected] != [(17,0),(412,0),(101,1),(191,2),(222,1)]:
        raise ValueError('Require the five exact actual source-selected builds')
    patch_path = SOURCE / 'catalog.ndb'
    if sha(patch_path) != '84cf9893fe520720cadf79a64f90f627a7afee4cbed1313d4487487ed17df7ba':
        raise ValueError('Current deployment-bound DP catalog differs')
    patch = database(patch_path)
    raw_files = {key: digest.hex()+extension for key, digest, extension in patch.execute('select key,hash,extension from files_rawtype')}
    if raw_files != {'catalog.db':'1ef703c16ab7d7257f314ba6bc366bd6.db', 'catalog.db.nds':'66183ba529546795fa387933ecdc3e4b.nds'}:
        raise ValueError('Current DP original raw catalog mapping differs')
    raw_path = SOURCE / 'raw' / raw_files['catalog.db']
    catalog = database(raw_path)
    index_path = SOURCE / 'chunk/store.cdb.idx'
    index = decode_index(index_path.read_bytes())
    store = SOURCE / 'chunk/store.cdb'
    before = record_stat(store)
    names, keys = set(), {}
    for row in selected:
        for role in ('AimSkeleton','CoverSkeleton'):
            key = row[role]
            rows = asset_rows(catalog, key)
            if len(rows) != 1 or rows[0]['asset_type'] != 'Spine.Unity.SkeletonDataAsset' or rows[0]['quality'] != 1:
                raise ValueError('Exact original real-character skeleton key/type/quality differs')
            entries, closure = key_bundles(catalog, key)
            keys[key] = {'role':role,'resourceId':row['resourceId'],'costumeIndex':row['costumeIndex'], 'assetRows':rows,'catalogEntries':entries,'bundles':sorted(closure)}
            names.update(closure)
    if len(names) > 128:
        raise ValueError('Exact ten-key resource closure exceeds bounded bundle count')
    decoder = zstandard.ZstdDecompressor()
    with store.open('rb') as stream:
        verified = {name:verify_bundle(patch,index,name,store,stream,decoder)for name in sorted(names)}
    chunks = {}
    for bundle in verified.values():
        for chunk in bundle.get('chunks',[]):
            key=chunk['store_offset']
            if key in chunks and chunks[key] != chunk:
                raise ValueError('Conflicting original DP chunk witness')
            chunks[key]=chunk
    compressed = sum(c['compressed_bytes'] for c in chunks.values())
    if len(chunks)>8192 or compressed>1024**3:
        raise ValueError('Exact selected resource closure exceeds1GiB/8192chunks')
    TARGET.mkdir(parents=True)
    copied = []
    for relative in ('catalog.ndb','catalog.ndb.nds','raw/'+raw_files['catalog.db'],'raw/'+raw_files['catalog.db.nds'],'chunk/store.cdb.idx'):
        src,dst=SOURCE/relative,TARGET/relative
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst)
        digest=sha(src)
        if sha(dst)!=digest:raise ValueError('Copied original signed DP input differs')
        copied.append({'relative':relative,'bytes':src.stat().st_size,'sha256':digest})
    target_store=TARGET/'chunk/store.cdb'
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(target_store),0xC0000000,0,None,1,0x80,None)
    if handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        returned=wintypes.DWORD()
        if not kernel.DeviceIoControl(handle,0x900C4,None,0,None,0,ctypes.byref(returned),None):raise ctypes.WinError(ctypes.get_last_error())
    finally:kernel.CloseHandle(handle)
    with store.open('rb') as source,target_store.open('r+b') as target:
        target.truncate(before['bytes'])
        header=source.read(256);target.write(header)
        for offset,c in sorted(chunks.items()):
            source.seek(offset);data=source.read(c['compressed_bytes'])
            if hashlib.sha256(data).hexdigest()!=c['compressed_sha256']:raise ValueError('Original DP chunk changed before copy')
            target.seek(offset);target.write(data)
    with target_store.open('rb')as target:
        if hashlib.sha256(target.read(256)).hexdigest()!=hashlib.sha256(header).hexdigest():raise ValueError('Original DP header differs')
        for offset,c in chunks.items():
            target.seek(offset)
            if hashlib.sha256(target.read(c['compressed_bytes'])).hexdigest()!=c['compressed_sha256']:raise ValueError('Staged DP chunk readback differs')
    after=record_stat(store)
    if after!=before:raise ValueError('Read-only original DP store changed')
    result={'schemaVersion':1,'resourceGroup':'dp','clientSha256':'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
        'sourceObservationVerificationSha256':sha(verification),'sourceCatalog':str(raw_path),'sourceCatalogSha256':sha(raw_path),
        'sourcePatchCatalogSha256':sha(patch_path),'targetGroupPath':str(TARGET),'copiedCatalogFiles':copied,
        'headerSha256':hashlib.sha256(header).hexdigest(),'sourceStore':str(store),'sourceStoreBefore':before,'sourceStoreAfter':after,
        'sourceReadOnly':True,'hardlinksUsed':False,'exactRealSkeletonKeys':keys,'verifiedBundles':verified,
        'uniqueChunks':len(chunks),'compressedBytes':compressed,'targetStoreStat':record_stat(target_store),
        'status':'passed','nativeCatalogRegistrationProven':False,'nativeLoadProven':False,'fallbackAliasesCreated':False,
        'scope':'Only ten actual observed real-character aim/cover HD keys and original catalog dependency closure; no battle/no installed writes'}
    output.open('x').write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'path':str(output),'sha256':sha(output),'keys':len(keys),'bundles':len(verified),'chunks':len(chunks),'compressedBytes':compressed,'nativeLaunched':False}))


if __name__=='__main__':main()

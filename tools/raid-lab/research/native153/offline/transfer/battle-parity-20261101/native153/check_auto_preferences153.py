"""Read only four exact named normal/private registry values for main11 witnesses."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import winreg

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SANDBOX=ROOT/'tools/raid-lab/private/native-player153-20261101'
BASELINE=HERE/'auto-preferences-before-main11.json'
BASELINE_SHA='64b8b0a8f9ddbdc78d46942a1530d867b589b9930b1edfcb263c458a400ea46f'
ISOLATION=HERE/'playerprefs-isolation-audit.json'
ISOLATION_SHA='149ecd1c37f6b56d7503f0ce04eb110fbe566e67ab0f1798963a809b3ad670fd'
NAMES=('SpotAutoAimMode_h3061544532','SpotAutoSkillMode_h2941636992')
PATHS={'normal':r'Software\com.proximabeta\NIKKE',
       'private':r'Software\RaidLabNativeSandbox\native-player153-20261101\Software\com.proximabeta\NIKKE'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_exact_values():
    # This parent-side witness must not run inside a redirected game/guard process.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
    if kernel.GetModuleHandleW('OfflineNetwork.dll'):raise RuntimeError('Registry witness must run outside the guarded child')
    rows={}
    for scope,path in PATHS.items():
        values={name:{'exists':False}for name in NAMES}
        try:
            # KEY_QUERY_VALUE only. No enumeration, creation, set, deletion or Save.
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_QUERY_VALUE)as key:
                for name in NAMES:
                    try:
                        value,kind=winreg.QueryValueEx(key,name)
                        values[name]={'exists':True,'registryType':kind,'value':value.hex()if isinstance(value,bytes)else value}
                    except FileNotFoundError:pass
            exists=True
        except FileNotFoundError:exists=False
        rows[scope]={'registryPath':'HKCU\\'+path,'keyExists':exists,'values':values}
    return rows


def validate_before(rows):
    reasons=[]
    for name in NAMES:
        if rows['normal']['values'][name]!={'exists':True,'registryType':winreg.REG_DWORD,'value':1}:
            reasons.append('normal_baseline_differs:'+name)
        if rows['private']['values'][name]!={'exists':False}:
            reasons.append('private_before_main11_no_longer_absent:'+name)
    if not all(r['keyExists']for r in rows.values()):reasons.append('expected_normal_or_private_game_key_missing')
    return reasons


def validate_after(before,after):
    reasons=[]
    if after['normal']!=before['normal']:reasons.append('normal_preferences_changed')
    for name in NAMES:
        if after['private']['values'][name]!={'exists':True,'registryType':winreg.REG_DWORD,'value':1}:
            reasons.append('private_expected_dword1_not_observed:'+name)
    if not after['private']['keyExists']:reasons.append('private_game_key_missing')
    return reasons


def main(phase,plan_sha256,player_pid=None):
    if not re.fullmatch('[a-f0-9]{64}',plan_sha256):raise ValueError('Exact frozen main11 plan SHA required')
    plan_path=SANDBOX/'practice-plan11.json'
    if json.loads(plan_path.read_text())['plan_sha256']!=plan_sha256:raise ValueError('Frozen main11 plan differs')
    if sha(BASELINE)!=BASELINE_SHA or sha(ISOLATION)!=ISOLATION_SHA:raise ValueError('Accepted baseline/isolation proof changed')
    isolation=json.loads(ISOLATION.read_text())
    for path,digest in isolation['bindings'].items():
        if sha(Path(path))!=digest:raise ValueError('Accepted private guard input changed')
    if phase=='post'and(player_pid is None or player_pid<=0):raise ValueError('Post witness requires the actual private player PID')
    output=SANDBOX/('practice11-auto-preferences-'+phase+'.json')
    if output.exists():raise FileExistsError('Preserve original preference witness')
    before_path=SANDBOX/'practice11-auto-preferences-pre.json'
    before=None;dead_child=None
    if phase=='post':
        from copy_complete153_store import ensure_closed
        dead_child=ensure_closed(player_pid)
        before=json.loads(before_path.read_text())
        if before['status']!='passed'or before['phase']!='pre'or before['planSha256']!=plan_sha256 or before['baselineSnapshotSha256']!=BASELINE_SHA or before['isolationProofSha256']!=ISOLATION_SHA:
            raise ValueError('Exact passing pre-witness for main11 required')
    rows=read_exact_values()
    failures=validate_before(rows)if phase=='pre'else validate_after(before['rows'],rows)
    report={'schemaVersion':1,'status':'failed'if failures else'passed','phase':phase,'candidateIndex':11,
        'scope':'Only four exact named registry values; current observation, not historical reference capture',
        'observedAtUtc':datetime.now(timezone.utc).isoformat(),'planSha256':plan_sha256,'rows':rows,'failures':failures,
        'baselineSnapshotSha256':BASELINE_SHA,'isolationProofSha256':ISOLATION_SHA,'guardBindingsUnchanged':True,
        'helperSourceSha256':sha(Path(__file__)),'writesPerformed':False,'registryEnumerationPerformed':False,
        'nativePreferenceApiInvoked':False,'normalAccountOrOtherValuesRead':False,'deadChild':dead_child,
        'normalTwoPreferencesUnchanged':rows['normal']==before['rows']['normal']if before else None,
        'specificPrivateDword1PersistenceVerified':phase=='post'and not failures,
        'preWitnessSha256':sha(before_path)if before else None}
    output.open('x').write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'path':str(output),'sha256':sha(output),'status':report['status'],'phase':phase,'failures':failures}))
    return 1 if failures else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['pre','post'],required=True)
    parser.add_argument('--plan-sha256',required=True);parser.add_argument('--player-pid',type=int)
    args=parser.parse_args();raise SystemExit(main(args.phase,args.plan_sha256,args.player_pid))

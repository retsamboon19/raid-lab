"""Read-only four-value continuity witness after the established main11 inputs."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from check_auto_preferences153 import HERE,SANDBOX,ISOLATION,ISOLATION_SHA,sha,read_exact_values

BASELINE=SANDBOX/'practice-output11/practice11-auto-preferences-post.json'
BASELINE_SHA='1fcd38c07f9ad25b85405899231ced0d19d7d9ba5ffd5baed322525c82b5681c'
BASELINE_VERIFICATION=SANDBOX/'practice-output11/verification.json'
BASELINE_VERIFICATION_SHA='1c580da3ebf5b58c4ab9b6f49fca9994ded600242ae1d44f2ae4a4dd8790ff3b'
READER=HERE/'check_auto_preferences153.py'
READER_SHA='587a40b57ef365111112f754a8c8f30f3d9783c80114f89e086f5bc1c5b62b0d'


def compare_continuity(expected,actual):
    return [scope+'_preferences_differ_from_established_private_inputs'for scope in ('normal','private')if actual[scope]!=expected[scope]]


def main(index,phase,plan_sha256,player_pid=None):
    if not 12<=index<=22 or not re.fullmatch('[a-f0-9]{64}',plan_sha256):raise ValueError('Exact subsequent main12..22 frozen plan required')
    if json.loads((SANDBOX/('practice-plan'+str(index)+'.json')).read_text())['plan_sha256']!=plan_sha256:
        raise ValueError('Frozen subsequent plan differs')
    for path,digest in [(BASELINE,BASELINE_SHA),(BASELINE_VERIFICATION,BASELINE_VERIFICATION_SHA),(READER,READER_SHA),(ISOLATION,ISOLATION_SHA)]:
        if sha(path)!=digest:raise ValueError('Established private preference/control source changed')
    baseline=json.loads(BASELINE.read_text());verification=json.loads(BASELINE_VERIFICATION.read_text())
    if baseline['status']!='passed'or not baseline['normalTwoPreferencesUnchanged']or not baseline['specificPrivateDword1PersistenceVerified']or \
       not verification['requiredPreferenceStorageControlsPassed']or verification['autoPreferenceWitnesses']['post']['sha256']!=BASELINE_SHA:
        raise ValueError('Main11 specific preference control is not established')
    for path,digest in json.loads(ISOLATION.read_text())['bindings'].items():
        if sha(Path(path))!=digest:raise ValueError('Accepted guard binding changed')
    if phase=='post'and(player_pid is None or player_pid<=0):raise ValueError('Actual closed child PID required')
    stem='practice'+str(index)+'-auto-preferences-';output=SANDBOX/(stem+phase+'.json')
    if output.exists():raise FileExistsError('Preserve original subsequent preference witness')
    before=None;before_path=SANDBOX/(stem+'pre.json');dead=None
    if phase=='post':
        from copy_complete153_store import ensure_closed
        dead=ensure_closed(player_pid);before=json.loads(before_path.read_text())
        if before['phase']!='pre'or before['status']!='passed'or before['candidateIndex']!=index or before['planSha256']!=plan_sha256 or \
           before['continuityBaselinePostSha256']!=BASELINE_SHA or before['helperSourceSha256']!=sha(Path(__file__)):
            raise ValueError('Exact passing subsequent pre-witness required')
    rows=read_exact_values();failures=compare_continuity(baseline['rows'],rows)
    if before:failures+=compare_continuity(before['rows'],rows)
    report={'schemaVersion':1,'status':'failed'if failures else'passed','phase':phase,'candidateIndex':index,'planSha256':plan_sha256,
        'scope':'Four exact current preference values; main11-established private1/1 continuity, not historical capture',
        'observedAtUtc':datetime.now(timezone.utc).isoformat(),'rows':rows,'failures':failures,
        'continuityBaselinePostSha256':BASELINE_SHA,'continuityBaselineVerificationSha256':BASELINE_VERIFICATION_SHA,
        'isolationProofSha256':ISOLATION_SHA,'guardBindingsUnchanged':True,'helperSourceSha256':sha(Path(__file__)),
        'exactReaderSourceSha256':READER_SHA,'writesPerformed':False,'registryEnumerationPerformed':False,
        'nativePreferenceApiInvoked':False,'normalAccountOrOtherValuesRead':False,'deadChild':dead,
        'normalTwoPreferencesUnchanged':rows['normal']==before['rows']['normal']if before else None,
        'specificPrivateDword1PersistenceVerified':phase=='post'and not failures,'preWitnessSha256':sha(before_path)if before else None,
        'privateAbsentPreconditionReused':False}
    output.open('x').write(json.dumps(report,indent=2)+'\n');print(json.dumps({'path':str(output),'sha256':sha(output),'status':report['status'],'failures':failures}))
    return 1 if failures else 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate-index',type=int,required=True)
    p.add_argument('--phase',choices=['pre','post'],required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--player-pid',type=int)
    a=p.parse_args();raise SystemExit(main(a.candidate_index,a.phase,a.plan_sha256,a.player_pid))

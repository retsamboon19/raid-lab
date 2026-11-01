"""Prepare source-only integration7 after explicit archived21 ACK; no staging/native."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIOR_SHA='1dec8c991be9233d13ebd904adb884ae00fb1e9e5a05f00f0993351e49265cdc'
CONTINUITY22_SHA='a9d56a45fa89e8fb164baffc40e4e86f2dd30b970a586287cc9c9f48240705c7'
BOUNDS22_SHA='7168e4830e179d35e7b79a307dee671a78f33820a1cc823cd8bc851cb817490a'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(archive21_sha256):
 if not re.fullmatch('[a-f0-9]{64}',archive21_sha256):raise ValueError('Explicit archived21 verification SHA required')
 archive=ROOT/'tools/raid-lab/private/native-player153-20261101/practice-output21/verification.json'
 if not archive.is_file() or sha(archive)!=archive21_sha256:raise ValueError('Wait for exact immutable21 archive ACK')
 verification=json.loads(archive.read_text())
 if verification['timedOut'] or verification['exitCode']!=0 or not all(verification['frozenSourceInputsUnchanged'].values()):raise ValueError('Original21 archive/input invariants differ')
 prior=HERE/'practice-overlay-rng-integration6.json'
 if sha(prior)!=PRIOR_SHA:raise ValueError('Preserve original integration6')
 old=json.loads(prior.read_text())
 changed={'check_auto_preferences_continuity153.py':CONTINUITY22_SHA,'test_stage_matched_reference_selection.py':BOUNDS22_SHA}
 reused={k:v for k,v in old['sourceHashes'].items() if k not in changed}
 for name,digest in {**reused,**changed}.items():
  if sha(HERE/name)!=digest:raise ValueError('Exact unchanged/planned source differs: '+name)
 output=HERE/'practice-overlay-rng-integration7.json'
 if output.exists():raise FileExistsError('Preserve immutable integration7')
 names=list(old['sourceHashes'])+['practice-overlay-rng-integration6.json','build_practice22_integration153.py','test_stage_practice22_transition.py','practice22-bounded-preparation-plan.json']
 before={name:sha(HERE/name) for name in names}
 commands=[[sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p',name,'-v'] for name in ['test_stage_matched_reference_selection.py','test_stage_practice22_transition.py']]
 commands.append([sys.executable,'-m','py_compile',str(HERE/'stage_practice153.py'),str(HERE/'check_auto_preferences_continuity153.py'),str(Path(__file__).resolve())])
 results=[]
 for command in commands:
  run=subprocess.run(command,capture_output=True,text=True,timeout=45);row={'argv':command,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr};results.append(row)
  if run.returncode:raise RuntimeError(json.dumps(row))
 if before!={name:sha(HERE/name) for name in names}:raise ValueError('Source changed while checking22')
 report={'schemaVersion':1,'scope':'Candidate22 bound extension for original reference3 only; runtime/native algorithms unchanged',
 'sourceHashes':before,'commands':results,'inputsUnchanged':True,'nativeRunPerformed':False,'candidateFrozen':False,
 'priorEvidencePreserved':{'path':str(prior),'sha256':PRIOR_SHA,'rewritten':False},
 'archived21':{'path':str(archive),'sha256':archive21_sha256,'status':verification['status'],'allFrozenInputsUnchanged':True},
 'unchangedPassingEvidenceReused':{'receiptSha256':PRIOR_SHA,'sourceHashes':reused,'priorCommandsNotRerun':True},
 'changes':{'candidateMaximum':22,'referenceRun':3,'continuityBoundOnly':True,'existingBoundsTestUpdated':True,'runtimeJsChanges':False,'selectorSourceChanges':False,'formulaOrRngWrites':False},
 'preparedProofTransition':{'candidate':22,'proofFromSha256':PRIOR_SHA,'builderFromSha256':'96887efb0fa77ad63d028da90c8f0604fa4656eeef2945ab83712e5cf93f2d56','builderToSha256':before['build_practice22_integration153.py'],'explicitReviewedHashesRequired':True,'generalJsonOrPythonReviewAllowed':False},
 'stagerNote':'Final stager is independently reviewed and frozen; omitted from this receipt to avoid source/proof hash cycles.'}
 with output.open('x',encoding='utf8') as sink:json.dump(report,sink,indent=2);sink.write('\n')
 print(json.dumps({'path':str(output),'sha256':sha(output),'commandsPassed':len(results),'nativeRunPerformed':False}))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive21-sha256',required=True)
 args=parser.parse_args();main(args.archive21_sha256)

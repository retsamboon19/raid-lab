"""Candidate17 typed EventId/archiver repair checks; preserve prior integration4."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 output=HERE/'practice-overlay-rng-integration5.json'
 if output.exists():raise FileExistsError('Preserve immutable integration5 proof')
 old_path=HERE/'practice-overlay-rng-integration4.json'
 if sha(old_path)!='3e0d4d9710d2cd22bf3941323ef82ddb298d9610e0f5c3db32121589d4bf55f9':raise ValueError('Historical integration4 differs')
 old=json.loads(old_path.read_text())
 if any(row['exitCode'] for row in old['commands']):raise ValueError('Prior passing source/mock receipt differs')
 changed_expected={'practice_overlay_bootstrap.js':'e0d1986acdad8141609f0bbff2199d360f604396303bbe6f62402ba22b10c444',
  'test_practice_overlay_bootstrap.js':'cf2ad5d621f696cf925274c617c061cfc0ea97b80b7e9ed664a1f777c3dc2086',
  'archive_practice153.py':'2dbfd56e1ba2c4d65768113653ea2f44c0a72af1c9af73f4473bb2bbc2ff6619'}
 mutable=set(changed_expected)|{'build_overlay_integration153.py'}
 reused={name:digest for name,digest in old['sourceHashes'].items() if name not in mutable}
 for name,digest in {**reused,**changed_expected}.items():
  if sha(HERE/name)!=digest:raise ValueError('Exact unchanged/reviewed source differs: '+name)
 extra={'test_archive_frozen_aliases153.py':'289322d4cfcbda0c438e304207874c134fbab5f34ff24c4ed5dde10a94dc1c28'}
 for name,digest in extra.items():
  if sha(HERE/name)!=digest:raise ValueError('Reviewed changed archiver test differs')
 names=list(old['sourceHashes'])+['practice-overlay-rng-integration4.json','test_archive_frozen_aliases153.py','test_overlay_prepared_proof_transition.py']
 before={name:sha(HERE/name) for name in names}
 verification=ROOT/'tools/raid-lab/private/native-player153-20261101/practice-output16/verification.json'
 if sha(verification)!='0a91a45e8d5451fe3e3d5ce19af420f32769cc2cac2fefd0b1a2bd8d3bfb66cc':raise ValueError('Preserved failed16 verification differs')
 commands=[['node','--check',str(HERE/'practice_overlay_bootstrap.js')],['node',str(HERE/'test_practice_overlay_bootstrap.js')],
  [sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_overlay_prepared_proof_transition.py','-v'],
  [sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_archive_frozen_aliases153.py','-v'],
  [sys.executable,'-m','py_compile',str(HERE/'stage_practice153.py'),str(HERE/'archive_practice153.py'),str(HERE/'build_overlay_integration153.py')]]
 results=[]
 for command in commands:
  run=subprocess.run(command,capture_output=True,text=True,timeout=30)
  row={'argv':command,'exitCode':run.returncode,'stdout':run.stdout,'stderr':run.stderr};results.append(row)
  if run.returncode:raise RuntimeError(json.dumps(row))
 if before!={name:sha(HERE/name) for name in names}:raise ValueError('Source changed while checking repair')
 report={'schemaVersion':1,'scope':'Candidate17 EventId signature-owned class resolution and exact frozen archive aliases; changed source/mock checks only',
  'sourceHashes':before,'commands':results,'inputsUnchanged':True,'nativeRunPerformed':False,'candidateFrozen':False,
  'priorEvidencePreserved':{'path':str(old_path),'sha256':sha(old_path),'rewritten':False,'scope':'Integration4 is historical candidate16 source/mock evidence, not proof EventId resolved natively'},
  'unchangedPassingEvidenceReused':{'receiptSha256':sha(old_path),'sourceHashes':reused,'priorCommandsNotRerun':True,'noNewNativeSuccessClaim':True},
  'failed16Preserved':{'verificationPath':str(verification),'sha256':sha(verification),'actualStatus':'failed','battleExecuted':False,'cause':'EventId looked up in the wrong assembly; mock repeated that incorrect assembly assumption'},
  'preparedProofTransition':{'candidate':17,'proofFromSha256':sha(old_path),'builderFromSha256':old['sourceHashes']['build_overlay_integration153.py'],'builderToSha256':before['build_overlay_integration153.py'],'explicitReviewedHashesRequired':True,'generalJsonOrPythonReviewAllowed':False,'unchangedExactCurrentTargetMayContinueAfter17':True},
  'behavior':'EventId derives from verified Find parameters2/3; same class handle, exact type and4B value layout required. Original table arguments/Show/Hide/flag/clock/fullRNG gates unchanged. Archiver deduplicates only exact same-key/path/hash aliases within one fresh invocation.',
  'stagerNote':'Final stager is independently bound by reviewed plan. Its proof literal is filled after this receipt to avoid hash cycles; final targeted admission/resource checks are recorded separately.'}
 with output.open('x',encoding='utf8') as sink:json.dump(report,sink,indent=2);sink.write('\n')
 print(json.dumps({'path':str(output),'sha256':sha(output),'commandsPassed':len(results),'reusedUnchangedSourceHashes':len(reused),'nativeRunPerformed':False}))
if __name__=='__main__':main()

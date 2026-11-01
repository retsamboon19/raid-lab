"""Candidate19 busy-main retry source checks; preserve all prior evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 output=HERE/"practice-overlay-rng-integration6.json"
 if output.exists():raise FileExistsError("Preserve immutable integration6 proof")
 prior=HERE/"practice-overlay-rng-integration5.json"
 if sha(prior)!="8a91162460156088884174b07e63e4910a25e99e0177a551da4df9a550d32e72":raise ValueError("Historical integration5 differs")
 old=json.loads(prior.read_text())
 if any(row["exitCode"] for row in old["commands"]):raise ValueError("Prior passing source receipt differs")
 changed={"practice_overlay_bootstrap.js":"e013e7f207f6f6355d2a68f38722b35f9a62049b69909cd18b58def3662d8b5b","test_practice_overlay_bootstrap.js":"99b3ecfe75de1fb2e4917625b6be6924d981fb758e1c43686163e81d0bd0f252"}
 added={"practice_localization.js":"6d26af5d439d4d1dce86e6e1a7242ae8ca46aea3746f61f576cc8a4bf0d4ab14","test_practice_localization.js":"653097ec9343fe538dedab3acaac954f90c367c055d999573a8ff0e6e0b4d208",
  "practice-localization-source19.json":"967e08d23f701589daa96ffb9478dbb3c0bf01122b29c3e750d6738925fda5c6",
  "practice-main-queue-backpressure-repair1.json":"ddb21f24cda4408b021c988ad687b299c7f887510fbbfd442ddffc7a3d3f5742",
  "check_auto_preferences_continuity153.py":"f7b532ba3e9b5c9393aac244ccbf98eaf168da688a8bc1a391af6ccf2da44412",
  "test_stage_matched_reference_selection.py":"6c29acdbd38a948a88ccea8cd2b15b3d00d6ce879c5734b2f4f0cee620beb6c6",
  "test_stage_localization153.py":"6fd381c24aa7b98a3d73dde33c174ba7c3ea21098d5e3a7163205ae45c2b0a2a"}
 reused={name:digest for name,digest in old["sourceHashes"].items() if name not in changed}
 for name,digest in {**reused,**changed,**added}.items():
  if sha(HERE/name)!=digest:raise ValueError("Exact reviewed source differs: "+name)
 names=list(dict.fromkeys([*old["sourceHashes"],*added,"practice-overlay-rng-integration5.json",
  "practice-localization-source153.json","test_stage_practice19_transition.py","build_practice19_integration153.py"]))
 before={name:sha(HERE/name) for name in names}
 failed=ROOT/"tools/raid-lab/private/native-player153-20261101/practice-output18/verification.json"
 if sha(failed)!="d33f4d13e099c88d45ea4c1ca2cf8e441f1216854e43a84f0935fa4b6970594b":raise ValueError("Frozen failure18 differs")
 commands=[["node","--check",str(HERE/"practice_overlay_bootstrap.js")],["node",str(HERE/"test_practice_overlay_bootstrap.js")],
  ["node","--check",str(HERE/"practice_localization.js")],["node",str(HERE/"test_practice_localization.js")]]
 for test in ("test_stage_practice19_transition.py","test_stage_matched_reference_selection.py","test_stage_localization153.py"):
  commands.append([sys.executable,"-B","-m","unittest","discover","-s",str(HERE),"-p",test,"-v"])
 commands.append([sys.executable,"-m","py_compile",str(HERE/"stage_practice153.py"),str(HERE/"check_auto_preferences_continuity153.py"),str(Path(__file__).resolve())])
 results=[]
 for command in commands:
  run=subprocess.run(command,capture_output=True,text=True,timeout=45)
  row={"argv":command,"exitCode":run.returncode,"stdout":run.stdout,"stderr":run.stderr};results.append(row)
  if run.returncode:raise RuntimeError(json.dumps(row))
 if before!={name:sha(HERE/name) for name in names}:raise ValueError("Source changed during focused checks")
 report={"schemaVersion":1,"scope":"Candidate19 pendingMain backpressure retry and exact proof/bounds admission; no native execution",
  "sourceHashes":before,"commands":results,"inputsUnchanged":True,"nativeRunPerformed":False,"candidateFrozen":False,
  "priorEvidencePreserved":{"path":str(prior),"sha256":sha(prior),"rewritten":False},
  "unchangedPassingEvidenceReused":{"receiptSha256":sha(prior),"sourceHashes":reused,"priorCommandsNotRerun":True,"noNewNativeSuccessClaim":True},
  "failed18Preserved":{"verificationPath":str(failed),"sha256":sha(failed),"actualStatus":"failed","battleExecuted":False,
   "cause":"onMain false denotes pendingMain occupancy, not queue rejection; original locale initialization passed"},
  "preparedProofTransition":{"candidate":19,"proofFromSha256":sha(prior),"builderFromSha256":old["sourceHashes"]["build_overlay_integration153.py"],
   "builderToSha256":before["build_practice19_integration153.py"],"localeFromSha256":before["practice-localization-source153.json"],
   "localeToSha256":before["practice-localization-source19.json"],"explicitReviewedHashesRequired":True,"generalJsonOrPythonReviewAllowed":False,
   "same26LocaleDependencyNamesRequired":True,"onlyExactModuleAndTestAliasesMayChange":True,"unchangedExactCurrentTargetMayContinueAfter19":True},
  "behavior":"False schedules a bounded retry without new native ticks; native exceptions/first async fault remain fatal. Candidate/continuity bounds extend only to21; reference selector and original shared RNG gates unchanged.",
  "stagerNote":"Final stager hash is separately reviewed. Integration proof literal is filled after this create-new receipt to avoid a hash cycle; final read-only guards are checked afterward."}
 with output.open("x",encoding="utf8") as sink:json.dump(report,sink,indent=2);sink.write("\n")
 print(json.dumps({"path":str(output),"sha256":sha(output),"commandsPassed":len(results),"nativeRunPerformed":False}))
if __name__=="__main__":main()

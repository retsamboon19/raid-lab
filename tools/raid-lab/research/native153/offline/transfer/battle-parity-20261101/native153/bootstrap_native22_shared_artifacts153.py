"""Root-run, write-once shared-artifact ledger bootstrap after closed native22.

Preparation/import never executes a player. --check-only observes; --write creates
only native-service/shared-artifacts.json under the canonical exclusive lease.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
S=ROOT/"tools/raid-lab/private/native-player153-20261101"
GAME=S/"NIKKE/NIKKE/game"
SERVICE=S/"native-service"
LEDGER=SERVICE/"shared-artifacts.json"
BROKER=ROOT/"tools/raid-lab/native_practice_job.py"
BROKER_SHA="969a954f4599e495ff9c98fd5dce0a870a2187ec76a905315b14798d00aaf0ec"
LEASE=ROOT/"tools/raid-lab/native_runner_lease.py"
LEASE_SHA="a019f95b599fa1194dcd59b36d0bfb05530829e60d7c85e025437a991b3d37ca"
FINAL_INDEX=22
FINAL_SHA="7144fcb693f65794aac192e7746b9c3f4f2c2338b1f32b88d8d02cd01bc997b7"
HEX=re.compile(r"[a-f0-9]{64}\Z")
PACKET=re.compile(r"practice([1-9][0-9]*)-original-result\.(?:pb|json)\Z")

def sha(path):
 with Path(path).open("rb")as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def module(path,digest,name):
 if sha(path)!=digest:raise ValueError("Exact reviewed broker/lease source required")
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value

def build_ledger(broker,expected_final_sha,*,sandbox=S,game=GAME):
 """File-only preflight: bounded archives1..22; no process or ledger writes."""
 if not isinstance(expected_final_sha,str)or not HEX.fullmatch(expected_final_sha)or expected_final_sha!=FINAL_SHA:raise ValueError("Exact closed native22 verification SHA256 required")
 sandbox=broker.no_links(sandbox);game=broker.no_links(game)
 if game!=sandbox/"NIKKE/NIKKE/game":raise ValueError("Exact canonical shared game path required")
 final=broker.bound(sandbox/"practice-output22/verification.json",expected_final_sha)
 final_record=broker.read_json(final)
 if final_record.get("status")not in ("passed","failed")or type(final_record.get("actualPlayerPid"))is not int or final_record["actualPlayerPid"]<=0 or \
    type(final_record.get("exitCode"))is not int or final_record.get("originalPacketFilename")!="practice22-original-result.pb":
  raise ValueError("Actual completed native22 archive with child/result identity required")
 current=broker.shared_files(game)
 if broker.SLOT not in current or any(name not in current for name in broker.LOGS):raise ValueError("Final closed diagnostic script and all three logs must be present")
 cache={FINAL_INDEX:(final,expected_final_sha,final_record)}
 def archived(index):
  if index not in cache:
   path=sandbox/("practice-output"+str(index))/"verification.json"
   if not path.is_file():return None
   path=broker.bound(path);digest=sha(path);record=broker.read_json(path)
   if record.get("status")not in ("passed","failed"):return None
   cache[index]=(path,digest,record)
  return cache[index]
 artifacts={};matched=[]
 for name,source in sorted(current.items()):
  if name==broker.SLOT:archive_name="scene-probe.js";indices=range(FINAL_INDEX,0,-1)
  elif name in broker.LOGS:archive_name=name;indices=range(FINAL_INDEX,0,-1)
  else:
   parsed=PACKET.fullmatch(name)
   if parsed is None or not 1<=int(parsed[1])<=FINAL_INDEX:raise ValueError("Unknown shared output basename preserved: "+name)
   archive_name=name;indices=(int(parsed[1]),)
  digest=sha(source);entry=None;selected=None
  for index in indices:
   candidate=archived(index)
   if candidate is None:continue
   verification,verification_sha,record=candidate
   archive=sandbox/("practice-output"+str(index))/archive_name
   if record.get("artifacts",{}).get(archive_name)!=digest or not archive.is_file():continue
   possible={"sha256":digest,"archivePath":str(archive),"verificationPath":str(verification),"verificationSha256":verification_sha}
   broker.archived_entry(possible,source)
   entry=possible;selected=index;break
  if entry is None:raise ValueError("No exact existing verified archive for shared artifact; preserve and supply archive: "+name)
  artifacts[name]=entry;matched.append({"sharedName":name,"archiveIndex":selected,"sha256":digest})
 # SLOT/logs must be final22 bytes, not stale output from an older closed trial.
 for name in (broker.SLOT,*broker.LOGS):
  if next(row["archiveIndex"]for row in matched if row["sharedName"]==name)!=FINAL_INDEX:raise ValueError("Final22 shared script/log is stale or lacks matching final22 archive: "+name)
 return {"schemaVersion":1,"source":"closed_native22_bootstrap","finalDiagnosticIndex":FINAL_INDEX,
  "finalDiagnosticVerificationPath":str(final),"finalDiagnosticVerificationSha256":expected_final_sha,
  "finalDiagnosticStatus":final_record["status"],"artifacts":artifacts,
  "bootstrapSourceSha256":sha(Path(__file__)),"brokerSourceSha256":BROKER_SHA,"leaseSourceSha256":LEASE_SHA,
  "originalArchivesRewritten":False,"sharedArtifactsModified":False,"nativeRunPerformed":False},matched

def bootstrap(expected_final_sha,*,write=False):
 broker=module(BROKER,BROKER_SHA,"native22_ledger_broker")
 lease=module(LEASE,LEASE_SHA,"native22_ledger_lease")
 broker.no_links(SERVICE)
 with lease.NativeRunnerLease(SERVICE/"runner.lock"):
  broker.no_private_player()
  if LEDGER.exists():raise FileExistsError("Existing authoritative ledger preserved; bootstrap never replaces it")
  if any((GAME/broker.SLOT).parent.glob("native-service-*.tmp"))or any(SERVICE.glob("shared-artifacts-*.tmp")):raise ValueError("Unfinished shared transaction preserved; review before bootstrap")
  value,matched=build_ledger(broker,expected_final_sha)
  broker.no_private_player()
  if sha(BROKER)!=BROKER_SHA or sha(LEASE)!=LEASE_SHA:raise ValueError("Broker/lease changed during preflight")
  for name,entry in value["artifacts"].items():broker.archived_entry(entry,broker.bound(GAME/name))
  if write:
   # Broker fresh_json uses exclusive x mode; no replacement/delete/cleanup.
   broker.fresh_json(LEDGER,value)
   if broker.read_json(LEDGER)!=value:raise ValueError("Fresh ledger readback differs; preserve for review")
   for name,entry in value["artifacts"].items():broker.archived_entry(entry,broker.bound(GAME/name))
  return {"status":"shared_ledger_created"if write else"shared_ledger_preflight_passed","ledgerPath":str(LEDGER),
   "ledgerSha256":sha(LEDGER)if write else None,"ledgerWritten":write,"matchedArtifacts":matched,
   "exclusiveCanonicalLeaseHeld":True,"privatePlayerAbsent":True,"finalNative22VerificationSha256":expected_final_sha,
   "archivesRewritten":False,"sharedArtifactsModified":False,"nativeRunPerformed":False}

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--native22-verification-sha256",required=True)
 modes=parser.add_mutually_exclusive_group(required=True);modes.add_argument("--check-only",action="store_true");modes.add_argument("--write",action="store_true");args=parser.parse_args()
 print(json.dumps(bootstrap(args.native22_verification_sha256,write=args.write)))

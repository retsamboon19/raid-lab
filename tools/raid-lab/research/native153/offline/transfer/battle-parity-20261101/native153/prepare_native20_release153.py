"""Prepare immutable native20 local release; never run a player or enable the app."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
S=ROOT/"tools/raid-lab/private/native-player153-20261101"
ARCHIVE=S/"practice-output20"
RID="native153-fire90-run1-v20-20261101"
DEST=S/"native-service/releases"/RID
REPORT=HERE/"native20-release-preparation1.json"
VERIFICATION_SHA="0500de21ed0945d073c3e167c53beec195eb7d0b815e3c91c29789c731a55784"
BROKER=ROOT/"tools/raid-lab/native_practice_job.py"
BROKER_SHA="969a954f4599e495ff9c98fd5dce0a870a2187ec76a905315b14798d00aaf0ec"
ADAPTER_REGISTRY=Path("I:/Raid Lab/tools/raid-lab/private/native-practice-releases.json")
HOST_PINS={"hostSha256":"d0ea48a3a8e30045a957da6a82bc37ef4c65e4377bfe4625cefc437633720328","leaseSha256":"a019f95b599fa1194dcd59b36d0bfb05530829e60d7c85e025437a991b3d37ca","harnessSha256":"891e5652cb1d9c5d4faf46aa9ceff49cb7ad52b2b10e846d24e643b56d055a78"}

def sha(path):
 with Path(path).open("rb")as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def plain(path):
 path=Path(path).absolute();current=Path(path.anchor)
 for part in path.parts[1:]:
  current/=part
  if current.is_symlink()or(hasattr(os.path,"isjunction")and os.path.isjunction(current)):raise ValueError("Release paths may not traverse links")
 return path.resolve()

def write_new(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("x",encoding="utf8",newline="\n")as sink:json.dump(value,sink,indent=2);sink.write("\n")

def original_inputs():
 if sha(plain(ARCHIVE/"verification.json"))!=VERIFICATION_SHA or sha(plain(BROKER))!=BROKER_SHA:raise ValueError("Exact native20/broker evidence required")
 v=json.loads((ARCHIVE/"verification.json").read_text());st=json.loads((ARCHIVE/"staging.json").read_text())
 if v["status"]!="passed"or not all(v[key]is True for key in ("completeBattle","requiredFullSharedRngStateVerified","originalPacketExportVerified","requiredPreferenceStorageControlsPassed")):raise ValueError("Passed original native20 gates required")
 if sha(ARCHIVE/"staging.json")!=v["artifacts"]["staging.json"]:raise ValueError("Native20 staging changed")
 frozen={};maps={}
 for group in ("sources","resourceReceipts"):
  maps[group]={}
  for key,item in st[group].items():
   if not key or any(c in key for c in ("/","\\",":")):raise ValueError("Original source key must be one filename component")
   name="frozen-"+key+Path(item["path"]).suffix
   if name in frozen and frozen[name]!=item["sha256"]:raise ValueError("Native20 alias hashes differ")
   if not (ARCHIVE/name).is_file()or v["artifacts"].get(name)!=item["sha256"]or sha(ARCHIVE/name)!=item["sha256"]:raise ValueError("Archived native20 source bytes differ: "+key)
   frozen[name]=item["sha256"];maps[group][key]="frozen/"+name
 if len(frozen)!=399 or len(st["sources"])!=385 or len(st["resourceReceipts"])!=15:raise ValueError("Exact native20 archive scope required")
 return v,st,frozen,maps

def prepare():
 if ADAPTER_REGISTRY.exists():raise FileExistsError("Keep app release registry absent during preparation")
 if plain(DEST).exists()or REPORT.exists():raise FileExistsError("Preserve prior release/preparation evidence")
 v,st,frozen,maps=original_inputs()
 plain(DEST).mkdir(parents=True,exist_ok=False)
 inventory={}
 def copy_original(source,relative,digest):
  source=plain(source);target=plain(DEST/relative)
  if not target.is_relative_to(plain(DEST))or target==plain(DEST):raise ValueError("Release copy target escaped")
  if not source.is_file()or source.stat().st_nlink!=1 or sha(source)!=digest:raise ValueError("Separate exact source copy required")
  target.parent.mkdir(parents=True,exist_ok=True)
  with source.open("rb")as incoming,target.open("xb")as outgoing:shutil.copyfileobj(incoming,outgoing,1048576)
  if sha(target)!=digest or sha(source)!=digest or target.stat().st_nlink!=1 or os.path.samefile(source,target):raise ValueError("Independent release copy readback differs")
  inventory[relative]=digest
 def add_json(relative,value):
  write_new(DEST/relative,value);inventory[relative]=sha(DEST/relative)
 for name,digest in frozen.items():copy_original(ARCHIVE/name,"frozen/"+name,digest)
 controls={"bundle/scene-probe.js":"scene-probe.js","controls/native20-config.json":"config.json","validation/native20-staging.json":"staging.json","validation/native20-verification.json":"verification.json","validation/practice20-original-result.pb":"practice20-original-result.pb","validation/practice20-independent-packet-decode.json":"practice20-independent-packet-decode.json","controls/native20-resource-verifier.py":"frozen-stager.py"}
 for relative,name in controls.items():
  digest=VERIFICATION_SHA if name=="verification.json"else v["artifacts"][name]
  copy_original(ARCHIVE/name,relative,digest)
 copy_original(Path(__file__),"provenance/prepare_native20_release153.py",sha(Path(__file__)))
 decoder_keys={"archive_decode.py":"packetArchiveDecoderSource","Program.cs":"packetDecoderSource","PacketDecoder.csproj":"packetDecoderProject","build_and_check.py":"packetDecoderBuildSource"}
 for name,key in decoder_keys.items():copy_original(DEST/maps["sources"][key],"decoder/"+name,st["sources"][key]["sha256"])
 decoder_artifacts={"PacketDecoder.dll":"packetDecoderArtifactPacketDecoder_dll","PacketDecoder.runtimeconfig.json":"packetDecoderArtifactPacketDecoder_runtimeconfig_json","PacketDecoder.deps.json":"packetDecoderArtifactPacketDecoder_deps_json","EpinelPS.dll":"packetDecoderArtifactEpinelPS_dll","Google.Protobuf.dll":"packetDecoderArtifactGoogle_Protobuf_dll"}
 for name,key in decoder_artifacts.items():copy_original(DEST/maps["sources"][key],"decoder/bin/Release/net10.0/"+name,st["sources"][key]["sha256"])
 old_build=json.loads((DEST/maps["sources"]["packetDecoderBuildReceipt"]).read_text());relocated=copy.deepcopy(old_build)
 for group in ("sourceInputs","artifacts"):
  for name,item in relocated[group].items():item["path"]=str(DEST/"decoder"/("bin/Release/net10.0/"if group=="artifacts"else"")/name)
 add_json("decoder/published-build-controls.json",relocated)
 template=copy.deepcopy(st)
 for group in ("sources","resourceReceipts"):
  for key,item in template[group].items():item["path"]=str(DEST/maps[group][key])
 template["sources"]["packetDecoderBuildReceipt"]={"path":str(DEST/"decoder/published-build-controls.json"),"sha256":inventory["decoder/published-build-controls.json"]}
 add_json("controls/service-staging-template.json",template)
 required={}
 for item in st["sources"].values():
  path=Path(item["path"]).resolve()
  if path.is_relative_to(S/"NIKKE/NIKKE/game"):
   relative=path.relative_to(S).as_posix()
   if relative in required and required[relative]!=item["sha256"]:raise ValueError("Runtime aliases differ")
   required[relative]=item["sha256"]
 if len(required)!=83:raise ValueError("All83 original game-data dependencies required")
 provenance=json.loads((ARCHIVE/"current-tables-provenance.json").read_text())
 required["current-tables.zip"]=provenance["sha256"]
 required["current-tables-provenance.json"]=v["artifacts"]["current-tables-provenance.json"]
 required["NIKKE/NIKKE/game/nikke_Data/il2cpp_data/Metadata/global-metadata.dat"]=hashlib.sha256(b"").hexdigest()
 native={"receiptFile":"validation/native20-verification.json","receiptSha256":VERIFICATION_SHA,"stagingFile":"validation/native20-staging.json","stagingSha256":v["artifacts"]["staging.json"],"packetFile":"validation/practice20-original-result.pb","packetSha256":v["originalPacketArtifact"]["sha256"],"decoderFile":"validation/practice20-independent-packet-decode.json","decoderSha256":v["artifacts"]["practice20-independent-packet-decode.json"]}
 manifest={"schemaVersion":1,"approved":True,"releaseId":RID,"engine":"original153","fixtureId":"captured-fire90-run1","inputSourceSha256":"9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7","clientSha256":"d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2","resultSchema":"native-practice-v1","packetBasename":"practice20-original-result.pb","files":inventory,"fixtureFile":maps["sources"]["fixtureInput"],"rngExpectedFile":maps["sources"]["rngExpectedInput"],"bundleFile":"bundle/scene-probe.js","configTemplateFile":"controls/native20-config.json","stagingTemplateFile":"controls/service-staging-template.json","resourceVerifierFile":"controls/native20-resource-verifier.py","preferenceReaderFile":maps["sources"]["autoPreferencesWitnessSource"],"preferenceBaselineFile":maps["sources"]["autoPreferencesEstablishedPostWitness"],"isolationProofFile":maps["sources"]["autoPreferencesIsolationProof"],"rngArchiveGateFile":maps["sources"]["rngArchiveGateSource"],"decoderModuleFile":"decoder/archive_decode.py","decoderBuildReceiptFile":"decoder/published-build-controls.json","decoderOriginalBuildReceiptFile":maps["sources"]["packetDecoderBuildReceipt"],"nativeValidation":native,"runtime":{**HOST_PINS,"requiredFiles":required},"operationsPrerequisites":{"diagnosticLaunchersUseSameLease":True,"authoritativeSharedArtifactLedgerRequiredBeforeFirstJob":True},"initialSharedArtifacts":{},"limits":["Prepared local fixed run1 release only; app registry intentionally absent","Original native20 validation passes; fresh broker/HTTP job not yet run","Root must bind latest closed diagnostic shared artifacts in service/shared-artifacts.json under the canonical lease before first broker job","No exact reference parity, arbitrary team/build or actor/Unity RNG certification"]}
 write_new(DEST/"manifest.json",manifest)
 if len(inventory)!=418 or len(required)!=86:raise ValueError("Exact prepared release file/runtime scope differs")
 spec=importlib.util.spec_from_file_location("native20_release_broker_check",BROKER);broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)
 release=broker.load_release(DEST/"manifest.json",sha(DEST/"manifest.json"))
 broker.verify_staging(release,template);broker.verify_inventory(release)
 for group in ("sourceInputs","artifacts"):
  if {k:v["sha256"]for k,v in old_build[group].items()}!={k:v["sha256"]for k,v in relocated[group].items()}:raise ValueError("Decoder relocation changed byte equivalence")
 if ADAPTER_REGISTRY.exists():raise ValueError("App registry appeared during preparation")
 report={"schemaVersion":1,"status":"prepared_admission_checks_passed","releaseId":RID,"manifestPath":str(DEST/"manifest.json"),"manifestSha256":sha(DEST/"manifest.json"),"builderSourceSha256":sha(Path(__file__)),"brokerSha256":BROKER_SHA,"nativeValidationSha256":VERIFICATION_SHA,"inventoryFiles":len(inventory),"runtimeRequiredFiles":len(required),"originalGameDataRuntimeFiles":83,"localeRuntimeFiles":63,"sourceKeys":385,"resourceReceiptKeys":15,"allFrozenFilesCopiedFromNative20Archive":True,"allReleaseCopiesIndependentAndReadbackVerified":True,"composedBundleUnchanged":True,"configTemplateUnchanged":True,"originalDecoderSourcesArtifactsByteEquivalent":True,"brokerLoadReleasePassed":True,"brokerVerifyStagingPassed":True,"brokerVerifyInventoryPassed":True,"appRegistryAbsent":True,"nativeRunPerformed":False,"httpJobPerformed":False,"sharedArtifactsOrRegistryWritten":False,"sharedArtifactLedgerPreconditionPending":True,"releaseConsumerEnabled":False}
 write_new(REPORT,report)
 return report

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--prepare",action="store_true",required=True);parser.parse_args();print(json.dumps(prepare()))

"""Add exact current153 SAUS Locale_*.lsc/signature closure to private lss only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SANDBOX=ROOT/"tools/raid-lab/private/native-player153-20261101"
BASE_HELPER=HERE/"stage_local_locale153.py"
BASE_HELPER_SHA="081ff464819a55710e1bdd1f6c2cabcba737491f021a3b648b32d3aef6c5e908"
BASE_RECEIPT=SANDBOX/"local-locale153-fixture1.json"
BASE_RECEIPT_SHA="c5de388f70c877553f7adeef916dca1a8778ae2808a58db3cdaf506b09e07688"
PROOF=HERE/"practice-locale-table-closure-source153.json"
PROOF_SHA="9cef725daf5479187e7a61b469cbf04d62031d1a045497f0ce4caaa00f92479f"
RECEIPT=SANDBOX/"local-locale153-table-closure1.json"
FAILED=SANDBOX/"practice-output19/verification.json"
FAILED_SHA="262fc7b4b9ed9e56b8bfee78209f43d7c58b1599d166f3f907558ec91398ce14"
DEAD_PID=40408
DECODE=ROOT/"transfer/decode_nkdb.py"
DECODE_SHA="0595cc2895b8e8c428576fda7110c9ad4a4ee129a4e9cefea45eab0d7ee44357"
HASH_HELPER=ROOT/"event-selector/first-anniversary/asset_tools/catalog_signing.py"
HASH_HELPER_SHA="51c6f2d743ce0f4443e3d81fb7bf6436e5f4805b956cdf2db13763b35822b825"

def sha(path):
 with Path(path).open("rb")as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def load(path,digest,name):
 if sha(path)!=digest:raise ValueError("Exact reviewed dependency differs: "+name)
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def base_inputs():
 base=load(BASE_HELPER,BASE_HELPER_SHA,"locale_closure_base153")
 if sha(base.no_links(BASE_RECEIPT))!=BASE_RECEIPT_SHA or sha(base.no_links(FAILED))!=FAILED_SHA:raise ValueError("Preserved base fixture/native19 evidence differs")
 evidence,plan=base.prepare()
 if len(plan)!=5 or any(not row["existingIdenticalCopy"]for row in plan):raise ValueError("Unchanged base5 must exist before additive closure")
 return base,evidence,plan

def enumerate_originals():
 base,evidence,base_plan=base_inputs()
 decoder=load(DECODE,DECODE_SHA,"locale_closure_decode153")
 hasher=load(HASH_HELPER,HASH_HELPER_SHA,"locale_closure_content_hash153")
 def database(path):
  conn=sqlite3.connect(":memory:");conn.deserialize(decoder.decode(path.read_bytes()))
  if conn.execute("pragma integrity_check").fetchone()[0]!="ok":raise ValueError("Known SAUS catalog integrity differs")
  return conn
 patch=database(Path(evidence["catalogs"]["patch"]["path"]))
 catalog=database(Path(evidence["catalogs"]["asset"]["path"]))
 try:
  tables=catalog.execute("select a.Key,f.RelativePath,f.Hash,f.Size from AssetEntity a join FileInfoEntity f on f.Id=a.FileId where f.RelativePath glob 'Locale_*.lsc' order by f.RelativePath").fetchall()
  if len(tables)!=30 or len({r[0]for r in tables})!=30:raise ValueError("Exact30 current153 catalog locale tables required")
  all_locale_paths={r[0]for r in catalog.execute("select RelativePath from FileInfoEntity where RelativePath glob 'Locale_*'")}
  expected_paths={name+suffix for _,name,_,_ in tables for suffix in ("",".nds")}
  if all_locale_paths!=expected_paths:raise ValueError("Known catalog has unaccounted original Locale_* entries")
  header=(ROOT/"NIKKE/NIKKE/game/nikke_Data/StreamingAssets/lss/Locale_BeforeInstall.lsc.nds").read_bytes()[:32]
  rows=[]
  for table,relative,_,_ in tables:
   if not re.fullmatch(r"Locale_[A-Za-z0-9]+",table)or relative!=table+".lsc":raise ValueError("Canonical locale table naming differs")
   for key,logical in ((table,relative),(relative,relative+".nds")):
    found=catalog.execute("select f.RelativePath,f.Hash,f.Size from AssetEntity a join FileInfoEntity f on f.Id=a.FileId where a.Key=?",(key,)).fetchall()
    if len(found)!=1 or found[0][0]!=logical:raise ValueError("Exact original locale/signature catalog mapping required")
    name,content,size=found[0]
    raw=patch.execute("select hash,extension,size from files_rawtype where key=?",(logical,)).fetchall()
    if len(raw)!=1 or raw[0][2]!=size:raise ValueError("Exact raw locale catalog mapping required")
    source=base.no_links(base.SOURCE/(raw[0][0].hex()+raw[0][1]));target=base.no_links(base.DEST/logical)
    data=source.read_bytes()
    if len(data)!=size or hasher.content_hash(data)!=content:raise ValueError("Original locale/signature content differs: "+key)
    if logical.endswith(".nds")and(len(data)!=96 or data[:32]!=header):raise ValueError("Original locale publisher signature/header differs")
    rows.append({"assetKey":key,"logicalPath":logical,"sourcePath":str(source),"privateRelativePath":logical,"privateTarget":str(target),"bytes":size,"sha256":hashlib.sha256(data).hexdigest(),"catalogContentHash":content.hex(),"catalogContentHashVerified":True,"signatureBytesPreserved":logical.endswith(".nds")})
 finally:patch.close();catalog.close()
 return base,evidence,base_plan,rows

def build_source_proof():
 base,evidence,plan,rows=enumerate_originals()
 by_path={row["privateRelativePath"]:row for row in rows}
 for row in plan:
  if row["privateRelativePath"]in by_path:
   prior=by_path[row["privateRelativePath"]]
   if (prior["bytes"],prior["sha256"])!=(row["bytes"],row["sha256"]):raise ValueError("Base5 and full closure overlap differs")
 extras=[{key:row[key]for key in ("assetKey","sourcePath","privateRelativePath","privateTarget","bytes","sha256")}for row in plan if row["privateRelativePath"]not in by_path]
 return {"schemaVersion":1,"status":"current153_complete_known_saus_locale_table_closure_verified","clientSha256":evidence["clientSha256"],"installedVersion":evidence["installedVersion"],"catalogs":evidence["catalogs"],"deploymentEvidence":evidence["deploymentEvidence"],"baseFixture":{"proofSha256":base.PROOF_SHA,"helperSha256":BASE_HELPER_SHA,"receiptPath":str(BASE_RECEIPT),"receiptSha256":BASE_RECEIPT_SHA,"files":5,"unchanged":True},"failedNative19":{"path":str(FAILED),"sha256":FAILED_SHA,"actualPlayerPid":DEAD_PID,"status":"failed","cause":"Original UpdateTick requested missing Locale_Monster after original OnStart/full shared RNG and playing controls passed"},"dependencies":{str(DECODE):DECODE_SHA,str(HASH_HELPER):HASH_HELPER_SHA},"localeTables":30,"localeTableAndSignatureFiles":60,"localeTableAndSignatureBytes":sum(r["bytes"]for r in rows),"assets":rows,"unchangedBaseExtras":extras,"unionFiles":len(rows)+len(extras),"unionBytes":sum(r["bytes"]for r in rows+extras),"catalogLocaleEntrySetComplete":True,"selectedLanguageChanged":False,"sourceFilesModified":False,"nativeRunPerformed":False,"nativeLocalRegistrationVerified":False,"nativeSignatureAcceptanceVerifiedForAddedTables":False,"scope":"All Locale_*.lsc tables and exact .nds entries in the already-known current153 SAUS catalog, plus unchanged base5 en font closure; no other localized asset tables/fonts included"}

def prepare():
 base,evidence,base_plan=base_inputs()
 if sha(base.no_links(PROOF))!=PROOF_SHA:raise ValueError("Exact complete original locale closure proof required")
 proof=json.loads(PROOF.read_text(encoding="utf8"))
 if build_source_proof()!=proof:raise ValueError("Current source/catalog closure no longer matches frozen proof")
 rows=proof["assets"]+proof["unchangedBaseExtras"];plan=[]
 if len(rows)!=63 or len({row["privateRelativePath"].casefold()for row in rows})!=63:raise ValueError("Exact63 independent canonical closure targets required")
 for row in rows:
  source=base.no_links(row["sourcePath"]);target=base.no_links(base.DEST/row["privateRelativePath"])
  if source.parent!=base.no_links(base.SOURCE)or str(target)!=row["privateTarget"]or not target.is_relative_to(base.no_links(base.DEST)):raise ValueError("Locale closure source/target escaped scope")
  exists=target.exists()
  if exists and(not target.is_file()or target.stat().st_nlink!=1 or target.stat().st_size!=row["bytes"]or sha(target)!=row["sha256"]or os.path.samefile(source,target)):raise FileExistsError("Conflicting original locale target preserved: "+str(target))
  partial=base.no_links(target.with_name(target.name+".locale-closure153.partial"))
  if partial.exists():raise FileExistsError("Existing closure partial preserved")
  plan.append({**row,"source":source,"target":target,"partial":partial,"existingIdenticalCopy":exists})
 return proof,plan

def verify_staged():
 proof,plan=prepare()
 if any(not row["existingIdenticalCopy"]for row in plan):raise ValueError("Complete original locale closure not staged")
 if not RECEIPT.is_file():raise ValueError("Completed additive locale closure receipt required")
 receipt=json.loads(RECEIPT.read_text(encoding="utf8"))
 if receipt["status"]!="original153_complete_locale_table_closure_staged"or receipt["sourceProofSha256"]!=PROOF_SHA or receipt["helperSourceSha256"]!=sha(Path(__file__))or receipt["baseFixtureReceiptSha256"]!=BASE_RECEIPT_SHA or len(receipt["copies"])!=63:raise ValueError("Completed additive locale closure receipt differs")
 for row,saved in zip(plan,receipt["copies"]):
  if (saved["target"],saved["sha256"],saved["bytes"])!=(str(row["target"]),row["sha256"],row["bytes"]):raise ValueError("Complete locale copy receipt differs")
 return proof,plan,receipt

def stage():
 if os.name!="nt":raise RuntimeError("Private Windows clone only")
 base,_,_=base_inputs();lease=load(base.LEASE,base.LEASE_SHA,"locale_closure_shared_lease153")
 with lease.NativeRunnerLease(base.no_links(SANDBOX/"native-service/runner.lock")):
  if RECEIPT.exists():raise FileExistsError("Preserve additive locale closure receipt")
  base.DEAD_PID=DEAD_PID;closed=base.confirm_closed()
  proof,plan=prepare();copies=[]
  for row in plan:
   source,target,partial=row["source"],row["target"],row["partial"]
   if not row["existingIdenticalCopy"]:
    with source.open("rb")as incoming,partial.open("xb")as outgoing:shutil.copyfileobj(incoming,outgoing,1048576)
    if sha(source)!=row["sha256"]or sha(partial)!=row["sha256"]or partial.stat().st_size!=row["bytes"]:raise ValueError("Original locale closure copy readback differs; partial preserved")
    os.rename(partial,target)
   if sha(target)!=row["sha256"]or target.stat().st_nlink!=1 or os.path.samefile(source,target):raise ValueError("Independent exact locale copy required")
   copies.append({"assetKey":row["assetKey"],"source":str(source),"target":str(target),"sha256":row["sha256"],"bytes":row["bytes"],"existingIdenticalCopy":row["existingIdenticalCopy"]})
  report={"schemaVersion":1,"status":"original153_complete_locale_table_closure_staged","sourceProofPath":str(PROOF),"sourceProofSha256":PROOF_SHA,"helperSourceSha256":sha(Path(__file__)),"baseFixtureReceiptSha256":BASE_RECEIPT_SHA,"leaseSourceSha256":base.LEASE_SHA,"exclusiveLeaseHeld":True,"knownChildClosed":closed,"localeTables":30,"localeTableAndSignatureFiles":60,"unionFiles":63,"unionBytes":proof["unionBytes"],"newFilesCopied":sum(not r["existingIdenticalCopy"]for r in plan),"copies":copies,"installedFilesWritten":False,"catalogsRewritten":False,"signatureBytesChanged":False,"nativeRunPerformed":False,"nativeInitializerInvoked":False,"nativeLocalRegistrationVerified":False}
  with RECEIPT.open("x",encoding="utf8",newline="\n")as sink:json.dump(report,sink,indent=2);sink.write("\n")
  return report

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True);group.add_argument("--check-only",action="store_true");group.add_argument("--copy",action="store_true");args=parser.parse_args()
 if args.check_only:
  proof,plan=prepare();print(json.dumps({"status":"verified_copy_plan","files":len(plan),"existingMatching":sum(row["existingIdenticalCopy"]for row in plan),"unionBytes":proof["unionBytes"],"nativeRunPerformed":False}))
 else:
  result=stage();print(json.dumps({"receipt":str(RECEIPT),"sha256":sha(RECEIPT),"newFilesCopied":result["newFilesCopied"],"unionFiles":63,"unionBytes":result["unionBytes"],"nativeRunPerformed":False}))

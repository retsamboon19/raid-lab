"""Select source-mapped original153 encounters; no combat emulation or formula."""
from __future__ import annotations
import copy
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

HERE=Path(__file__).resolve().parent
CATALOGUE=HERE/"encounter-catalog153.json"
SOURCE=HERE/"encounter-source153.json"
SETTINGS={"encounter_id","control_policy","fixed_level","level","content_mode","boss_id","duration","playstyle","bunny_mode","weekly_buff_id","random_seed","native_viewport","native_speed_multiplier","native_event_prefilter","native_frame_profile","native_frame_profile_warmup_seconds","native_coherent_capture","native_render_interval","native_full_validation","native_js_runtime","native_startup_skip","native_clean_profile","native_unity_scope_profile","native_profiler_recorders","native_playerloop_timing","native_lateupdate_owners","native_fx_quality","native_postprocess_flags","execution_profile"}

@lru_cache(maxsize=1)
def _catalogue():
    data=json.loads(CATALOGUE.read_text(encoding="utf-8"))
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    if data.get("schemaVersion")!=1 or data.get("engine")!="original153" or source.get("catalogSha256")!=hashlib.sha256(CATALOGUE.read_bytes()).hexdigest():
        raise ValueError("Original153 encounter catalogue source binding differs.")
    return data


def catalog():
    data=_catalogue()
    fields=("id","bossId","contentMode","name","timeLimit","waveId","processType","unitLevel","selectable","reason")
    entries=[]
    for row in data["encounters"]:
        public={key:copy.deepcopy(row[key]) for key in fields if key in row}
        if row["contentMode"]=="museum":
            unique={option["BuffId"]:option["skillId"] for option in row["context"]["weeklyBuffOptions"]}
            public["weeklyBuffOptions"]=[{"id":buff,"name":"Original weekly buff #"+str(buff),"skillId":skill} for buff,skill in sorted(unique.items())]
        entries.append(public)
    return {"schemaVersion":1,"engine":"original153","defaultEncounterId":"practice:1","sourceOnly":True,"nativeRunPerformed":False,"modes":copy.deepcopy(data["modes"]),"coverage":copy.deepcopy(data["coverage"]),"encounters":entries}


def select_encounter(settings):
    if not isinstance(settings,dict):
        raise ValueError("Native encounter settings must be an object.")
    unknown=set(settings)-SETTINGS
    if unknown:
        raise ValueError("Unsupported native encounter controls or enemy overrides: "+", ".join(sorted(unknown)))
    if "native_speed_multiplier" in settings:
        speed=settings["native_speed_multiplier"]
        if type(speed) not in (int,float) or speed not in (1,1.5,2,6):
            raise ValueError("Experimental native speed must be1,1.5,2or6; default is1.")
    if "native_lateupdate_owners" in settings:
        if type(settings["native_lateupdate_owners"]) is not bool or (settings["native_lateupdate_owners"] and not (settings.get("native_frame_profile") is True and settings.get("native_clean_profile") is True)):
            raise ValueError("Original LateUpdate owner profiler requires explicit clean diagnostic profile.")
    if "native_playerloop_timing" in settings:
        if type(settings["native_playerloop_timing"]) is not bool or (settings["native_playerloop_timing"] and not (settings.get("native_frame_profile") is True and settings.get("native_clean_profile") is True)):
            raise ValueError("Original PlayerLoop timers require explicit clean diagnostic profile.")
    if "native_profiler_recorders" in settings:
        if type(settings["native_profiler_recorders"]) is not bool or (settings["native_profiler_recorders"] and not (settings.get("native_frame_profile") is True and settings.get("native_clean_profile") is True)):
            raise ValueError("Original profiler recorders require explicit clean diagnostic profile.")
    if "native_unity_scope_profile" in settings:
        if type(settings["native_unity_scope_profile"]) is not bool or (settings["native_unity_scope_profile"] and not (settings.get("native_frame_profile") is True and settings.get("native_clean_profile") is True)):
            raise ValueError("Native Unity CPU scopes require explicit clean diagnostic profile.")
    if "native_clean_profile" in settings:
        if type(settings["native_clean_profile"]) is not bool or (settings["native_clean_profile"] and settings.get("native_frame_profile") is not True):
            raise ValueError("Clean performance profile requires explicit native profile opt-in.")
    if "native_startup_skip" in settings:
        if type(settings["native_startup_skip"]) is not bool or (settings["native_startup_skip"] and settings.get("native_frame_profile") is not True):
            raise ValueError("Original startup skip requires explicit diagnostic profile opt-in.")
    if "native_js_runtime" in settings:
        runtime=settings["native_js_runtime"]
        if runtime not in ("default","v8") or (runtime=="v8" and settings.get("native_frame_profile") is not True):
            raise ValueError("V8 runtime requires explicit diagnostic profile opt-in.")
    if "native_full_validation" in settings:
        if type(settings["native_full_validation"]) is not bool or (settings["native_full_validation"] and not (settings.get("native_frame_profile") is True and settings.get("native_coherent_capture") is True)):
            raise ValueError("Full validation requires opt-in coherentcapture and frameprofile.")
    if "execution_profile" in settings and settings["execution_profile"] not in ("standard","accelerated60-preview"):
        raise ValueError("Unsupported native execution profile.")
    if "native_postprocess_flags" in settings:
        value=settings["native_postprocess_flags"]
        if type(value) is not int or value!=0 or settings.get("native_fx_quality")!=0 or settings.get("native_frame_profile") is not True or settings.get("native_full_validation") is not True:
            raise ValueError("Post-process flags0 requires the explicit minimum-FX full diagnostic profile.")
    if "native_fx_quality" in settings:
        if type(settings["native_fx_quality"]) is not int or settings["native_fx_quality"]!=0 or settings.get("native_frame_profile") is not True:
            raise ValueError("Minimum original FX quality requires explicit diagnostic opt-in.")
    if "native_render_interval" in settings:
        interval=settings["native_render_interval"]
        if type(interval) is not int or interval not in (1,4,8) or (interval!=1 and settings.get("native_frame_profile") is not True):
            raise ValueError("Render cadence requires1/4/8 and bounded diagnostic profile forreducedcadence.")
    if "native_coherent_capture" in settings:
        if type(settings["native_coherent_capture"]) is not bool:
            raise ValueError("Diagnostic coherent capture opt-in must be boolean.")
        if settings["native_coherent_capture"] and settings.get("native_frame_profile") is not True:
            raise ValueError("Coherent capture is diagnostic-only and requires bounded frame profile.")
    if "native_frame_profile_warmup_seconds" in settings:
        warmup=settings["native_frame_profile_warmup_seconds"]
        if type(warmup) not in (int,float) or warmup not in (0,6.5) or settings.get("native_frame_profile") is not True:
            raise ValueError("Diagnostic warmup requires profile and0or6.5native seconds.")
    if "native_frame_profile" in settings:
        if type(settings["native_frame_profile"]) is not bool:
            raise ValueError("Native frame profile opt-in must be boolean.")
        if settings["native_frame_profile"] and (settings.get("native_speed_multiplier",1)!=1 or settings.get("native_event_prefilter") is not True):
            raise ValueError("Frame profiling requires1x and native event prefilter enabled.")
    if "native_event_prefilter" in settings and type(settings["native_event_prefilter"]) is not bool:
        raise ValueError("Native event prefilter opt-in must be boolean.")
    if "native_viewport" in settings:
        viewport=settings["native_viewport"]
        if not isinstance(viewport,dict) or set(viewport)!={"width","height"} or any(
                type(viewport[key]) is not int or not 64<=viewport[key]<=16384 for key in ("width","height")):
            raise ValueError("Original native viewport requires integer width/height in64..16384.")
    if "random_seed" in settings:
        seed=settings["random_seed"]
        if type(seed) is not int or not 1<=seed<=2147483647:
            raise ValueError("Original native random seed must be a positive Int32.")
    encounter_id=settings.get("encounter_id")
    if encounter_id is None:
        # Backwards-compatible original Fire90 entry used before the complete
        # catalogue. Other categories require an explicit original variant.
        if settings.get("content_mode")!="practice" or settings.get("boss_id")!="training" or settings.get("duration")!=90:
            raise ValueError("Choose an exact original encounter variant (encounter_id); a generic boss or campaign objective cannot select its actual stage.")
        encounter_id="practice:1"
    if not isinstance(encounter_id,str):
        raise ValueError("Original encounter ID must be a string.")
    matches=[row for row in _catalogue()["encounters"] if row["id"]==encounter_id]
    if len(matches)!=1:
        raise ValueError("Unknown original153 encounter variant.")
    selected=copy.deepcopy(matches[0])
    if not selected["selectable"]:
        raise ValueError(selected["reason"])
    for key,target in (("content_mode","contentMode"),("boss_id","bossId"),("duration","timeLimit")):
        if key in settings and settings[key]!=selected[target]:
            raise ValueError(f"{key} conflicts with the selected original encounter variant.")
    if settings.get("playstyle","auto")!="auto" or settings.get("bunny_mode","stance")!="stance":
        raise ValueError("Assisted firing and custom bunny opening charge holds require connected original native controls.")
    control=settings.get("control_policy","auto")
    if control not in ("auto","qte-parts-cover"):
        raise ValueError("Unknown native control policy.")
    if settings.get("execution_profile")=="accelerated60-preview" and (selected["waveId"] not in (6302006,6302009) or selected["contentMode"]!="anomaly" or control!="qte-parts-cover"):
        raise ValueError("Accelerated preview currently supports Mirror Container and Kraken with improved targeting.")
    if "native_postprocess_flags" in settings and selected["waveId"]!=6302006:
        raise ValueError("Post-process diagnostic currently supports the original Mirror Container encounter.")
    selected["controlPolicy"]=control
    weekly=settings.get("weekly_buff_id",0)
    if type(weekly) is not int or weekly<0:
        raise ValueError("Weekly buff selection must be an original integer buff ID or zero.")
    if selected["contentMode"]=="museum":
        options={row["BuffId"]:row["skillId"] for row in selected["context"]["weeklyBuffOptions"]}
        if weekly and weekly not in options:
            raise ValueError("The selected weekly buff is not an original option for this Museum stage.")
        selected["context"].update(selectedWeeklyBuffId=weekly,selectedWeeklyBuffSkillId=options[weekly] if weekly else 0,currentRotationClaimed=False)
    elif "weekly_buff_id" in settings:
        raise ValueError("Weekly buffs apply only to an original Museum encounter.")
    if "fixed_level" in settings or "level" in settings:
        if selected["contentMode"]!="practice":
            raise ValueError("Unit level overrides are only available for own-build practice; other modes retain their original fixed, own or capped level policy.")
        fixed=settings.get("fixed_level",False)
        if type(fixed) is not bool:
            raise ValueError("Fixed-level selection must be true or false.")
        if fixed:
            level=settings.get("level")
            if type(level) not in (int,float) or not math.isfinite(level) or int(level)!=level or not 1<=level<=1000:
                raise ValueError("Practice fixed level must be an integer from1 to1000.")
            selected["unitLevel"]={"mode":"fixed","value":int(level)}
    selected["catalogSha256"]=hashlib.sha256(CATALOGUE.read_bytes()).hexdigest()
    selected["sourceReceiptSha256"]=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    selected["nativeRunPerformed"]=False
    return selected

"""Create separate153 adapters from preserved original algorithms. No native calls."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / 'tools/raid-lab/native-player'
CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
OLD_CLIENT = '2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02'
OLD_METHODS = {0x063B5D20:'ammo',0x063B7740:'weapon',0x0821F520:'camera',0x0644B7E0:'auto',
 0x0645A1A0:'tagCtor',0x0645A0B0:'tagSend',0x0644BB70:'coverCtor',0x06510EE0:'eventSend',
 0x064A6A60:'down',0x064A6B40:'up',0x064A6CE0:'move',0x08269CB0:'unityAlive',
 0x08263110:'transform',0x0827A100:'position',0x082D6B80:'colliderEnabled',
 0x0638B4C0:'hp',0x0638B880:'maxHp',0x06380910:'partHp',0x06380A30:'partMaxHp',
 0x063809F0:'partActive',0x06375950:'qteOrder',0x06375ED0:'qteSuccess',
 0x0614BAF0:'dispatch',0x063BDC00:'fireProjectile',0x06142DB0:'projectileCreate'}
VARS={'management.class':'NK.Spot.SpotManagement','team.class':'NK.Spot.Context.Player.TeamContext',
 'character':'NK.Spot.Model.Character.SpotCharacter','entity':'NK.Spot.Model.Common.SpotEntity',
 'entityInfo':'NK.Spot.Logic.Character.SpotEntityInfo','info':'NK.Spot.Logic.Character.SpotEntityInfo',
 'eventBase':'NK.Spot.Common.SpotEvent','original':'NK.Spot.Common.SpotEvent',
 'monsterContextClass':'NK.Spot.Context.Monster.MonsterContext','monster':'NK.Spot.Model.Monster.SpotMonster',
 'parts':'NK.Spot.Model.Monster.SpotMonsterPartsData.PartsData','qteContextClass':'NK.Spot.Context.QuickTimeEventContext',
 'presetClass':'NK.Spot.Model.QuickTimeEvent.SpotQuickTimePreset','qteColliderClass':'NK.Spot.Model.QuickTimeEvent.SpotQuickTimeCollider',
 'monsterData':'NK.Spot.Monster.Model.MonsterData','monsterStatic':'NK.StaticData.StaticDataLayer.StaticInfo.MonsterStaticInfo',
 'monsterCondition':'NK.Spot.Model.Monster.SpotMonsterCondition','data':'NK.Spot.Event.Projectile.ProjectileData',
 'attack':'NK.Spot.Event.Monster.MonsterAttackEvent','create':'NK.Spot.Event.Projectile.ProjectileCreateEvent',
 'spawn':'NK.Spot.Event.Projectile.ProjectileSpawnEvent','despawn':'NK.Spot.Event.Projectile.ProjectileDespawnEvent',
 'damage':'NK.Spot.Event.Common.OnEntityGetDamageEvent','coverDamage':'NK.Spot.Event.Character.CoverTakeDamageEvent'}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    binding = json.loads((HERE/'tactical-binding.json').read_text())
    methods, classes = binding['methods'], binding['classes']
    inputs, outputs, changed_fields = {}, {}, []
    def copy(name, edit):
        source = OLD/name; text = source.read_text(); inputs[str(source.relative_to(ROOT))] = sha(source)
        result = '// Prepared current153-only adapter; no native validation claim. Historical input remains preserved.\n'+edit(text)
        target = HERE/name
        if target.exists():
            if target.read_text()!=result:raise FileExistsError('Preserve differing prepared source: '+name)
        else:
            with target.open('x',encoding='utf8') as out:out.write(result)
        outputs[name] = sha(target)
    def addresses(text):
        for old,key in OLD_METHODS.items():
            text = re.sub(r'0x'+format(old,'08X'), '0x'+format(methods[key]['rva'],'08X'), text, flags=re.I)
        return text.replace(OLD_CLIENT,CLIENT)
    def fields(text):
        def substitute(match):
            var,name,old = match.group(1),match.group(2),int(match.group(3),16)
            cls = VARS[var]
            spec = classes.get(cls)
            if not spec:raise ValueError('Missing selected class field metadata: '+cls)
            selected=[r for r in spec['fields']if r['name']==name]
            if len(selected)!=1:raise ValueError('Missing exact field: '+cls+'.'+name)
            new=selected[0]['offset']
            if new!=old:changed_fields.append({'class':cls,'field':name,'oldOffset':old,'newOffset':new})
            return '['+var+',"'+name+'",'+hex(new)+']'
        return re.sub(r'\[('+ '|'.join(re.escape(k)for k in VARS)+r'),"([^"]+)",(0x[0-9a-fA-F]+)\]',substitute,text)
    def actions(text):
        text=addresses(text)
        a=text.index('    if (!method.virtualAddress.equals(game.base.add(rva)))')
        b=text.index('    return method;',a)
        text=text[:a]+'    requireKraken153Method(method,rva);\n'+text[b:]
        text=text.replace('const getAuto = teamClass.method("get_IsAutoModeAim", 0);',f'const getAuto = exact(teamClass.method("get_IsAutoModeAim", 0),{methods["autoRead"]["rva"]},"autoRead");')
        text=text.replace('const getCover = teamClass.method("get_IsForcedCover", 0);',f'const getCover = exact(teamClass.method("get_IsForcedCover", 0),{methods["coverRead"]["rva"]},"coverRead");')
        text=text.replace('const getInputType = driverClass.method("get_InputType", 0);',f'const getInputType = exact(driverClass.method("get_InputType", 0),{methods["inputRead"]["rva"]},"inputRead");')
        # Action layout guards use their actual fresh declaring classes.
        text=text.replace('if (field.offset !== offset)','if (field.offset !== offset)')
        start=text.index('  for (const [field, offset] of')
        end=text.index('  const aimEnum',start)
        action_fields=[('teamClass','_isAutoModeAim'),('teamClass','_isForcedCover'),('teamClass','_focusedCharacter'),
                       ('driverClass','_inputType'),('driverClass','LockMoveAim'),('driverClass','LocKIunput')]
        text=text[:start]+''.join(f'  requireKraken153Field({c},{json.dumps(n)});\n'for c,n in action_fields)+text[end:]
        text=text.replace('if (aimEnum !== 0)', 'requireKraken153Enum(autoType,"Aim",aimEnum);\n  if (aimEnum !== 0)')
        text=text.replace('return { snapshot, setAutoAim, focus, aimWorld, press, release, setCover };',
                          'return { snapshot, setAutoAim, focus, aimWorld, press, release, setCover, pointer };')
        return text
    def observer(text):
        text=fields(addresses(text))
        start=text.index('    if (!method.virtualAddress.equals(game.base.add(rva)))')
        end=text.index('    return method;',start)
        text=text[:start]+'    requireKraken153Method(method,rva);\n'+text[end:]
        start=text.index('    if (klass.field(name).offset !== offset)')
        end=text.index('\n  };',start)
        text=text[:start]+'    requireKraken153Field(klass,name,offset);'+text[end:]
        text=text.replace('const id=number(klass.field(name).value);','const id=number(klass.field(name).value);\n      requireKraken153Enum(klass,name,id);')
        # Kraken has no Mirror part-break controller. Retain only its exercised
        # event/state roots; unrelated missing roots must not block this mode.
        start=text.index('    ["NK.Spot.Event.Monster.MonsterBreakableTimeStartEvent"')
        end=text.index('    ["NK.Spot.Event.Monster.MonsterAttackEvent"',start)
        text=text[:start]+text[end:]
        line='    ["NK.Spot.Event.Monster.MonsterChoiceSkillEvent","MonsterSelectChoiceSkill",[["CasterInfo",0x40],["EndAtRemainCount",0x48],["DurationTime",0x4C]]],\n'
        text=text.replace(line,'')
        start=text.index('  const endReasonMap=enumMap(')
        end=text.index('  let fault=',start)
        text=text[:start]+'  const endReasonMap=new Map(); // No Mirror-only break event roots in Kraken.\n'+text[end:]
        return text
    def threat(text):
        text=fields(addresses(text))
        start=text.index('    if (!method.virtualAddress.equals(game.base.add(rva)))')
        end=text.index('\n  };',start)
        text=text[:start]+'    requireKraken153Method(method,rva);'+text[end:]
        start=text.index('    if (klass.field(name).offset!==offset)')
        end=text.index('\n  };',start)
        text=text[:start]+'    requireKraken153Field(klass,name,offset);'+text[end:]
        return text
    copy('mechanics_tactical_actions.js',actions)
    copy('mechanics_tactical_observer.js',observer)
    copy('mechanics_threat_observer.js',threat)
    copy('mechanics_qte_policy.js',lambda t:t)  # Algorithm byte-equivalent after header.
    def cover(text):
        start=text.index('function mechanicsVerifiedCoverRules()')
        return text[:start]+'''function mechanicsVerifiedCoverRules() {
  const source=globalThis.KRAKEN153_AUTHORED_RULE;
  const sha=globalThis.KRAKEN153_AUTHORED_RULE_SHA256;
  if (!source || source.clientSha256!=="'''+CLIENT+'''" ||
      sha!=="2880621c6edb7145a390d0db68f57f272ae6f165e9f03e42d32bf36c7c0de844" || source.waveId!==6302009 ||
      source.monsterTableId!==1520040153 || source.coverTrigger?.behaviorNodeId!==230 ||
      source.coverTrigger?.monsterSkillId!==532033 || source.qte?.groupId!==212 ||
      JSON.stringify(source.qte.breakIds)!=="[21201,21203,21205,21207,21209,21211,21213]" ||
      JSON.stringify(source.qte.counterIds)!=="[21202,21204,21206,21208,21210,21212,21214]")
    throw Error("Exact current153 authored Kraken rule proof required");
  return [{id:"kraken-intercept-shot02-followup",waveId:source.waveId,
    monsterTableId:String(source.monsterTableId),attackNodeId:source.coverTrigger.behaviorNodeId,
    projectileSkillId:source.coverTrigger.monsterSkillId,reactionTicks:3,
    releaseCondition:"Idle",requireCasting:true,
    source:{clientSha256:source.clientSha256,authoredSourceSha256:sha,
      nativeTrials:[],current153NativeValidated:false,
      scope:"Current153 authored rule; native protection and resumption remain pending"}}];
}
'''
    copy('mechanics_cover_policy.js',cover)
    report={'schemaVersion':1,'clientSha256':CLIENT,'historicalInputs':inputs,'outputs':outputs,
            'changedFieldOffsets':changed_fields,'runtimeTrialPerformed':False,
            'scope':'Fresh153 declarations/prefixes; QTE algorithm unchanged, cover algorithm unchanged before rule factory; removed unrelated Mirror event dependencies only.'}
    with(HERE/'module-port-source.json').open('x',encoding='utf8')as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'modules':len(outputs),'changedFields':changed_fields}))


if __name__=='__main__':main()

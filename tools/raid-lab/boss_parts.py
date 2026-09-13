"""Finite boss-part state, with separate player destruction and self-destruction."""
import math
import struct

def part_max_hp(stat,monster,part,main_part=None):
    """Client PartsData construction: body HP and finite part HP are separate stats."""
    # PartsData::.ctor 0x61bbd30 chooses stat type 7 for finite non-main
    # parts; CalcMonsterStatEnhance 0x5f5ced0 maps 7 to LevelBrokenHp
    # (0x5f5cf91). Main and zero-ratio linked parts use type 0/LevelHp.
    linked=not part['IsMainPart'] and part['HpRatio']==0
    base=stat['LevelHp' if part['IsMainPart'] or linked else 'LevelBrokenHp']
    ratio=(main_part or {}).get('HpRatio',10000) if linked else part['HpRatio']
    value=base*(monster['HpRatio']/10000)*(ratio/10000)
    # CommonUtil.DoubleToLong 0x5fa8ea0 rounds to five decimal places,
    # adds 0.5 for positive HP, then truncates to an integer.
    return math.floor(round(value,5)+.5)


def part_break_damage(stat,monster,part,main_part=None):
    """Separate main-body HP loss on a player-caused part break, not weapon damage."""
    # PartsData::.ctor 0x61bc05f-0x61bc0bb constructs the MAIN part's
    # BrokenHp with stat 7/LevelBrokenHp and monster/main-part HP ratios.
    # SpotMonsterStatus::UpdateStatus 0x61cc7a5-0x61cc7d6 preserves that
    # value, independent of the finite part's HP and the body's LevelHp.
    main=main_part or (part if part.get('IsMainPart') else {})
    broken_hp=math.floor(round(stat['LevelBrokenHp']*(monster['HpRatio']/10000)
                               *(main.get('HpRatio',10000)/10000),5)+.5)
    f32=lambda value:struct.unpack('<f',struct.pack('<f',float(value)))[0]
    # PartsData::.ctor 0x61bc365-0x61bc381 performs two float32 *0.01f
    # operations; replacing them with /10000 in double changes large bonuses.
    ratio=f32(f32(f32(part['DamageHpRatio'])*f32(.01))*f32(.01))
    # MonsterAttackLogic::SetDamage 0x621651d-0x621655a multiplies by
    # float32(main BrokenHp), then CommonUtil::FloatToLong 0x5fa91c0:
    # round(double(value), 5, ToEven), add signed 0.5, truncate.
    value=f32(f32(broken_hp)*ratio)
    return math.trunc(round(value,5)+(.5 if value>0 else -.5))

class BossParts:
    def __init__(self):self.parts={};self.events=[]
    def spawn(self,ident,hp,time,attack_at=None):
        if not math.isfinite(hp) or hp<=0:raise ValueError('Part HP must be positive')
        if attack_at is not None and attack_at<time:raise ValueError('Part attack precedes spawn')
        self.parts[ident]={'hp':hp,'max_hp':hp,'spawned':time,'attack_at':attack_at,
                           'status':'alive','attack_cancelled':False,'attack_committed':False}
        self.events.append({'time':time,'event':'part spawned','part':ident,'hp':hp})
    def damage(self,ident,amount,time):
        if not math.isfinite(amount) or amount<0:raise ValueError('Invalid part damage')
        part=self.parts[ident]
        if part['status']!='alive':return 0
        dealt=min(amount,part['hp']);part['hp']-=dealt
        if part['hp']==0:
            part['status']='destroyed';part['attack_cancelled']=not part['attack_committed']
            part['destroyed_at']=time
            self.events.append({'time':time,'event':'part destroyed by squad','part':ident})
        return dealt
    def self_destruct(self,ident,time):
        part=self.parts[ident]
        if part['status']!='alive':return
        part['hp']=0;part['status']='self-destructed'
        self.events.append({'time':time,'event':'part self-destructed','part':ident})
    def due_attacks(self,time):
        attacks=[]
        for ident,part in self.parts.items():
            deadline=part['attack_at']
            if part['status']=='alive' and deadline is not None and time>=deadline:
                attacks.append(ident);part['attack_at']=None;part['attack_committed']=True
                self.events.append({'time':time,'event':'part attack committed','part':ident})
        return attacks
    def alive(self,ident):return self.parts.get(ident,{}).get('status')=='alive'

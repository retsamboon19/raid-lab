import unittest
from types import SimpleNamespace
import core
from calculator.buff_manager import BuffManager
from raid_boss_combat import RaidBossRuntime
from mother_whale_combat import MotherWhaleRuntime, CORE
from kraken_combat import KrakenRuntime
from mechanics import EncounterRuntime


def bind(r,mermaid=False):
    names=[core.NAME_MAP[n] for n in (('little mermaid','scarlet') if mermaid else ('liter','scarlet'))]
    chars=[core.spec.build_char(n,core.default_build(),no_layer=True) for n in names]
    b=BuffManager(chars,{});b.battle_start(0)
    r.bind(b,chars,{n:SimpleNamespace(base_atk=100*(i+1),weapon_type='AR',fire_rate=12,charge_time_base=1,reloading_until=0) for i,n in enumerate(names)})
    return b,names


class AimTests(unittest.TestCase):
    def test_only_controller_targets_part_outside_full_burst(self):
        for r in (RaidBossRuntime([],30,key='museum-crystal-chamber'),MotherWhaleRuntime([],30),KrakenRuntime([],30)):
            b,names=bind(r);r.frame={};controlled=names[1];ai=names[0]
            if isinstance(r,MotherWhaleRuntime):
                self.assertEqual(r.select_target(ai),('body',None));self.assertEqual(r.select_target(controlled),('part',CORE))
                r.frame={'full_burst':True};self.assertEqual(r.select_target(ai),('part',CORE))
            else:
                self.assertIsNone(r.select_part(ai));self.assertIsNotNone(r.select_part(controlled))
                r.frame={'full_burst':True};self.assertIsNotNone(r.select_part(ai))

    def test_siren_focus_works_without_controlling_or_bursting_siren(self):
        r=MotherWhaleRuntime([],30);b,names=bind(r,True);r.frame={}
        self.assertEqual(r.aim_controller,names[1])
        self.assertEqual(r.select_target(names[0]),('part',CORE))
        # Removing or expiring the effect stops redirected allied fire.
        effect=next(a for a in b._active if a.effect.get('stat')=='focus_fire')
        effect.expires_at=1;r.time=1
        self.assertEqual(r.select_target(names[0]),('body',None))

    def test_recommendation_override_is_used_by_actual_targeting(self):
        r=MotherWhaleRuntime([],30);r.aim_controller_override=core.NAME_MAP['liter'];b,names=bind(r)
        self.assertEqual(r.select_target(names[0]),('part',CORE));self.assertEqual(r.select_target(names[1]),('body',None))
        r.record_part_aim(CORE,names[0],100)
        self.assertEqual(r.report()['control_plan'][0]['unit'],names[0])

    def test_qte_obeys_same_focus_rule(self):
        r=MotherWhaleRuntime([],30);b,names=bind(r,True)
        q=EncounterRuntime([dict(kind='qte',start=0,duration=10,targets=[dict(hp=100)],controller=names[1],full_burst_follow=True)])
        q.bm=b;q.advance(0,{})
        self.assertIsNotNone(q.target(names[0],'SMG','Wind'))
        b._active=[a for a in b._active if a.effect.get('stat')!='focus_fire']
        self.assertIsNone(q.target(names[0],'SMG','Wind'))
        q.frame['full_burst']=True;self.assertIsNotNone(q.target(names[0],'SMG','Wind'))


if __name__=='__main__':unittest.main()

import copy
import unittest
from types import SimpleNamespace
import core
import encounters
from calculator.buff_manager import BuffManager
from special_interception import SpecialInterceptionRuntime, SPECIAL_KEYS

def runtime(key='gravedigger',duration=180,bind=False,**kwargs):
    r=SpecialInterceptionRuntime([],duration,key='special-'+key,**kwargs)
    if bind:
        names=[core.NAME_MAP[n] for n in ('liter','centi','drake','sugar','helm')]
        chars=[core.spec.build_char(n,core.default_build(),no_layer=True) for n in names]
        bm=BuffManager(chars,{'hp':dict.fromkeys(names,1e9),'hp_pct':dict.fromkeys(names,100.),
            'base_stats':{n:{'hp':1e9,'atk':1000,'def':0} for n in names}})
        bm.battle_start(0)
        r.bind(bm,chars,{n:SimpleNamespace(base_atk=1000,weapon_type='AR',fire_rate=12,charge_time_base=1,reloading_until=0) for n in names})
    return r

def hit(r,damage,caster='unit'):
    return r.resolve(caster,'철갑','AR',{'is_normal_atk':True},lambda **kw:dict(damage=damage,is_crit=False),{'enemy_def':0})['damage']

def run(r,shoot=False):
    for i in range(int(r.duration*60)+1):
        r.advance(i/60,{'full_burst':True})
        if r.stopped:break
        if shoot and r.active:hit(r,1e8)
    return r.report()

class SpecialTests(unittest.TestCase):
    def test_correct_ex_variants_levels_and_elements(self):
        expected={'alteisen':(3520010133,'Fire'),'gravedigger':(3520020143,'Iron'),
            'blacksmith':(1520030113,'Water'),'chatterbox':(1520020113,'Water'),'modernia':(3520040153,'Wind')}
        for key,(mid,weakness) in expected.items():
            s=core.validate_settings({'boss_id':'special-'+key,'content_mode':'special'})
            r=encounters.config(s,180)['encounter_runtime']
            self.assertIsInstance(r,SpecialInterceptionRuntime)
            self.assertEqual(r.data['wave']['monster_id'],mid)
            self.assertEqual(s['level'],200)
            self.assertEqual(s['encounter']['weakness'],weakness)
            self.assertFalse(s['element_locked'])
            self.assertEqual(s['teams'],1)

    def test_all_five_execute_and_receive_attacks(self):
        for key in SPECIAL_KEYS:
            with self.subTest(key=key):
                r=runtime(key.removeprefix('special-'),bind=True)
                p=run(r)
                self.assertTrue(p['incoming'])
                self.assertGreater(len(p['events']),10)
                self.assertTrue(p['stop_reason'] or p['simulated_until']>=179.9)
                self.assertFalse(p['full_fight_verified'])

    def test_every_boss_qte_passes_only_with_real_hits(self):
        for key in SPECIAL_KEYS:
            for shooting in (True,False):
                r=runtime(key.removeprefix('special-'),duration=15)
                skill=next(s for s in r.skills.values() if s['BreakObject'])
                q=r.ordinary_qte(skill,0,3)
                # Isolate the check from boss policy and ensure body DPS is irrelevant.
                r.tree.advance=lambda t:'running'
                for i in range(181):
                    r.advance(i/60,{'full_burst':True})
                    if shooting and r.active:hit(r,1e7)
                self.assertEqual(r.states[q]['status'],'passed' if shooting else 'failed')
                self.assertEqual(r.damage,0)

    def test_zero_damage_cannot_pass(self):
        r=runtime(duration=10);r.tree.advance=lambda t:'running';q=r.ordinary_qte(r.skills[6],0,2)
        for i in range(121):
            r.advance(i/60,{});hit(r,0)
        self.assertEqual(r.states[q]['status'],'failed')

    def test_gravedigger_three_phases_and_failure_pressure(self):
        r=runtime();driver=r.tree
        driver.gravedigger();self.assertEqual(driver.queue[0][0],[6])
        driver.queue=[];driver.running=[];r.damage=17026001
        driver.gravedigger();self.assertEqual(driver.phase,2)
        self.assertIn((driver.queue or [( [9],{})])[0][0][0],(9,10))
        r.damage=32798001;driver.queue=[];driver.running=[];driver.gravedigger()
        self.assertEqual(driver.phase,3);self.assertEqual(driver.pressure,1)
        q=r.ordinary_qte(r.skills[9],0,3);r.states[q]['status']='failed';driver.last_qte=q
        driver.running=[];driver.queue=[];driver.gravedigger()
        self.assertTrue(driver.running[0][0]['_bypass_cover'])
        self.assertEqual(driver.running[0][0]['SkillAniNumberTypemSkillAniNumber'],'Shot_5')

    def test_gravedigger_success_prevents_drill(self):
        r=runtime();p=run(r,shoot=True)
        self.assertTrue(p['checks']);self.assertTrue(all(c['status']=='passed' for c in p['checks']))
        self.assertFalse(any(e['event']=='drill retaliation' for e in p['events']))

    def test_phase_three_drill_ignores_full_cover(self):
        r=runtime(bind=True,auto_cover=False);n=next(iter(r.squad));before=r.bm.state['hp'][n]
        r.covered={n};cover=r.cover[n]
        r.receive_attack(r.skills[5],{'_locked_targets':[n],'_bypass_cover':True})
        self.assertLess(r.bm.state['hp'][n],before);self.assertEqual(r.cover[n],cover)

    def test_finite_cover_uses_encounter_level(self):
        r=runtime(bind=True);n=next(iter(r.squad))
        self.assertEqual(r.cover[n],11400)
        self.assertEqual(r.cover_def[n],110)
        r.receive_attack(r.skills[4],{'_locked_targets':[n]})
        r.covered={n};r.receive_attack(r.skills[4],{'_locked_targets':[n]})
        self.assertEqual(r.cover[n],0)

    def test_projectiles_need_hp_damage_and_never_score_as_boss(self):
        r=runtime();r.time=1;r.perform_skill(r.skills[3],{})
        p=r.projectiles[0];self.assertGreater(p['hp'],100)
        hit(r,1);self.assertEqual(p['hp'],p['max_hp']) # Reaction delay.
        r.time=1.2;hit(r,1);self.assertEqual(p['hp'],p['max_hp']-1)
        hit(r,1e9);self.assertEqual(p['status'],'passed');self.assertEqual(r.damage,0)
        self.assertEqual(r.damage_to_projectiles,p['max_hp'])

    def test_undestroyable_green_missiles_are_not_intercepted(self):
        r=runtime('alteisen',bind=True);r.perform_skill(r.skills[6],{})
        self.assertFalse(r.projectiles);self.assertTrue(r.incoming)

    def test_modernia_core_first_and_last_wing_preserved(self):
        r=runtime('modernia');self.assertEqual(r.select_part('unit'),'Weapon_03')
        r.world.parts.self_destruct('Weapon_03',0);self.assertEqual(r.select_part('unit'),'Weapon_01')
        r.world.parts.self_destruct('Weapon_01',0);self.assertIsNone(r.select_part('unit'))
        r.part_policy='all';self.assertEqual(r.select_part('unit'),'Weapon_02')

    def test_modernia_destroyed_wings_trigger_qte_and_restore_core(self):
        r=runtime('modernia')
        for p in ('Weapon_01','Weapon_02','Weapon_03'):r.world.parts.self_destruct(p,0)
        r.tree.modernia();self.assertEqual(r.world.phase,2)
        self.assertTrue(r.world.parts.alive('Weapon_03'))
        self.assertEqual(r.tree.running[0][0]['SkillAniNumberTypemSkillAniNumber'],'Shot_9')

    def test_chatterbox_preserves_head_and_last_launcher(self):
        r=runtime('chatterbox');self.assertEqual(r.select_part('unit'),'Weapon_01')
        r.world.parts.self_destruct('Weapon_01',0);self.assertIsNone(r.select_part('unit'))
        self.assertTrue(r.world.parts.alive('Weapon_03'))

    def test_corrosion_is_conditional_and_can_be_cleansed(self):
        r=runtime('chatterbox',bind=True);n=next(iter(r.squad))
        for _ in range(6):r.apply_function(1999101,n)
        self.assertGreater(r.bm.state['hp'][n],0)
        r.apply_function(1999101,n);self.assertEqual(r.bm.state['hp'][n],0)
        self.assertIn('seven stacks',r.stop_reason)
        r=runtime('chatterbox',bind=True);n=next(iter(r.squad))
        for _ in range(6):r.apply_function(1999101,n)
        r.bm._active=[a for a in r.bm._active if a.effect.get('name')!='Chatterbox corrosion']
        r.apply_function(1999101,n);self.assertEqual(r.debuff_stacks[n],1)
        self.assertFalse(r.stopped)

    def test_first_death_stops_damage_and_reports_failure(self):
        r=runtime('alteisen',bind=True,auto_cover=False);n=next(iter(r.squad));r.bm.state['hp'][n]=1
        r.receive_attack(r.skills[6],{'_locked_targets':[n],'_bypass_cover':True})
        self.assertTrue(r.stopped);self.assertEqual(hit(r,1e10,n),0)
        self.assertEqual(r.report()['survival'],'failed')

    def test_reward_threshold_stops_successfully(self):
        r=runtime();r.damage=r.max_reward_damage;r.advance(.1,{})
        self.assertTrue(r.target_reached);self.assertTrue(r.stopped)
        self.assertEqual(r.report()['reward_stage'],9);self.assertIsNone(r.stop_reason)

    def test_reward_progress_beats_direct_damage_and_clears_keep_safety(self):
        from candidate_ranking import score
        from critical_parts import select_tested
        def row(damage,progress,clear=False,fail=False):
            return dict(members=list('abcde'),damage=damage,duration=180,encounter_timeline=dict(
                special_interception=True,boss_hp_damage=progress,max_reward_damage=62007001,
                target_reached=clear,simulated_until=40,minimum_hp_pct=60,checks=[dict(status='failed' if fail else 'passed')]))
        incomplete=row(61000000,61000000)
        clear=row(40000000,62007001,True)
        unsafe=row(100000000,100000000,True,True)
        self.assertGreater(score(clear),score(incomplete))
        self.assertGreater(score(clear),score(unsafe))
        self.assertIs(select_tested([incomplete,unsafe,clear],1)[0],clear)
        self.assertEqual(score(dict(damage=123)),123)

    def test_modernia_has_opening_time_and_second_beam_deadline(self):
        r=runtime('modernia',duration=35)
        for i in range(301):r.advance(i/60,{})
        self.assertFalse(r.part_deadlines.rows)
        # The first beam can be covered. The next beam is the critical break.
        for i in range(301,2101):r.advance(i/60,{})
        self.assertTrue(r.part_deadlines.rows)
        self.assertTrue(all(x['deadline']>10 for x in r.report()['critical_deadlines']))

    def test_short_clear_rates_use_observed_time(self):
        r=runtime();r.damage=r.max_reward_damage;r.advance(20,{})
        row=dict(members=[],breakdown={},damage=100000,duration=180,encounter_timeline=r.report(),
            burst_rotation=dict(full_burst_seconds=10),mechanics={})
        core.attach_combat_assessment(row)
        self.assertEqual(row['dps'],5000)
        self.assertEqual(row['burst_rotation']['uptime_pct'],50)

    def test_default_guidance_keeps_beginner_support_and_builds(self):
        p=encounters.BY_ID['special-blacksmith'];self.assertIn('Healing',p['guidance']['required_tags'])
        for key in SPECIAL_KEYS:
            guide=encounters.BY_ID[key]['guidance']
            self.assertTrue(guide['qte_tip']);self.assertTrue(guide['survival_tip'])
            self.assertIn('special-interception',guide['source'])

if __name__=='__main__':unittest.main()

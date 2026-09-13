import unittest
from types import SimpleNamespace
from critical_parts import assessment, best_allocation, Deadlines, refine, screen_score, select_tested
from boss_parts import BossParts
import core
import encounters


def row(members,damage,passed=True):
    return dict(members=list(members),damage=damage,duration=30,encounter_timeline=dict(
        simulated_until=30,critical_parts=[dict(status='passed' if passed else 'failed')]))


class CriticalPartsTests(unittest.TestCase):
    def test_pass_dominates_damage_and_allocations_are_disjoint(self):
        a=row('abcde',1000,False);b=row('abcdf',10);c=row('eghij',9)
        best=best_allocation([a,b,c],2)
        self.assertEqual([r['damage'] for r in best],[10,9])
        self.assertTrue(set(best[0]['members']).isdisjoint(best[1]['members']))
        self.assertEqual(best_allocation([a,b],1)[0]['damage'],10)

    def test_failed_fallback_uses_damage_not_partial_breaks(self):
        a=row('abcde',100,False);b=row('abcdf',1000,False)
        self.assertEqual(best_allocation([a,b],1)[0]['damage'],1000)

    def test_late_break_and_respawn_cannot_erase_missed_deadline(self):
        parts=BossParts();parts.spawn('core',100,0);d=Deadlines()
        d.register(parts,['core'],5,1);parts.damage('core',100,6)
        parts.spawn('core',100,7);d.register(parts,['core'],10,2);parts.damage('core',100,9)
        self.assertEqual([r['status'] for r in d.report(12)],['failed','passed'])

    def test_self_destruction_is_not_player_break(self):
        p=BossParts();p.spawn('x',100,0);d=Deadlines();d.register(p,['x'],5,1)
        p.self_destruct('x',2)
        self.assertEqual(d.report(6)[0]['status'],'failed')

    def test_pending_and_shortened_runs_do_not_pass(self):
        r=row('abcde',100);r['encounter_timeline']['simulated_until']=10
        self.assertFalse(assessment(r)['passed'])
        r['encounter_timeline']['simulated_until']=30;r['encounter_timeline']['critical_parts'][0]['status']='pending'
        self.assertFalse(assessment(r)['passed'])

    def test_applicability_and_body_comparison_normalized(self):
        s=core.validate_settings(dict(boss_id='museum-mother-whale',require_critical_parts=True))
        self.assertTrue(s['require_critical_parts'])
        self.assertFalse(core.validate_settings(dict(boss_id='training',require_critical_parts=True))['require_critical_parts'])
        s=core.validate_settings(dict(boss_id='anomaly-kraken',require_critical_parts=True,kraken_target_policy='body'))
        self.assertEqual(s['kraken_target_policy'],'safe')
        self.assertFalse(core.validate_settings(dict(boss_id='anomaly-kraken',boss_simulation='reference',require_critical_parts=True))['require_critical_parts'])

    def test_late_damage_does_not_improve_screen_score(self):
        p=BossParts();p.spawn('core',100,0);d=Deadlines();d.register(p,['core'],5,1)
        p.damage('core',20,4);d.advance(5);p.damage('core',80,6)
        r=row('abcde',1000,False);r['encounter_timeline']['critical_parts']=d.report(30)
        self.assertAlmostEqual(screen_score(r)[1],.2)
        self.assertEqual(r['encounter_timeline']['critical_parts'][0]['status'],'failed')

    def test_bounded_selection_keeps_full_seed_and_prefers_passing_teams(self):
        seed=[row('abcde',1000,False),row('fghij',1000,False)]
        passing=[row('abcdf',10),row('eghij',10)]
        result=select_tested(seed+passing,2,True,[seed])
        self.assertEqual(len(result),2);self.assertTrue(all(assessment(r)['passed'] for r in result))

    def test_expired_budget_never_launches_rescue(self):
        from unittest.mock import Mock
        prefetch=Mock()
        refine([row('abcde',100,False)],Mock(),Mock(),prefetch,Mock(),30,0,lambda:False)
        prefetch.assert_not_called()

    def test_deadline_margin_beats_late_total_damage_in_screening(self):
        a=row('abcde',100000,False);b=row('abcdf',10,False)
        for r,remaining in [(a,90),(b,10)]:
            r['encounter_timeline']['critical_parts']=[dict(status='failed',hp=100,remaining_hp_at_deadline=remaining)]
        self.assertGreater(screen_score(b),screen_score(a))


if __name__=='__main__':unittest.main()

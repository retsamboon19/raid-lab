import unittest
from types import SimpleNamespace as N
from dependency_search import healing_dependencies,healing_repairs

class DependencySearchTests(unittest.TestCase):
    def test_uptime_comes_from_buff_events_not_healer_membership(self):
        team=['dependent','shared']
        effects={'dependent':[{'type':'buff','target':'all_allies','name':'power','stat':'atk_dmg_pct','trigger':{'timing':['event:heal_received']}}],'shared':[{'stat':'heal_split'}]}
        self.assertEqual(healing_dependencies(team,effects,[],30)[0]['uptime'],0)
        events=[N(t=t,kind='activate',name='power',stat='atk_dmg_pct',caster='dependent',target=n,expires_at=t+7) for t in (3,6) for n in team]
        self.assertAlmostEqual(healing_dependencies(team,effects,events,30)[0]['uptime'],10/30)

    def test_early_expiry_reduces_measured_uptime(self):
        effects={'unit':[{'type':'buff','target':'all_allies','name':'power','stat':'atk','trigger':{'timing':['event:heal_received']}}]}
        events=[N(t=t,kind=kind,name='power',stat='atk',caster='unit',target='unit',expires_at=10) for t,kind in [(0,'activate'),(2,'expire')]]
        self.assertEqual(healing_dependencies(['unit'],effects,events,10)[0]['uptime'],.2)

    def test_low_damage_direct_healer_gets_comparison_without_named_rules(self):
        team=['b1','dependent','shared','dps1','dps2'];ids=team+['direct','burst_healer']
        effects={n:[] for n in ids};effects['shared']=[{'stat':'heal_split'}]
        effects['direct']=[{'stat':'heal_hp_pct','target':'all_allies','trigger':{'timing':['normal_attack_count:5']}}]
        effects['burst_healer']=[{'stat':'heal_hp_pct','target':'all_allies','trigger':{'timing':['burst_cast']}}]
        catalog={n:{'burst':'2' if n in ('dependent','shared','direct','burst_healer') else '1' if n=='b1' else '3'} for n in ids}
        weights=dict.fromkeys(ids,100);weights['direct']=1
        baseline={'members':team,'healing_dependencies':[{'unit':'dependent','uptime':0}]}
        proposals=healing_repairs(baseline,ids,effects,catalog,weights,lambda t:len(set(t))==5)
        self.assertTrue(any(p['incoming']=='direct' and p['outgoing']=='shared' for p in proposals))
        direct=[p['members'] for p in proposals if p['incoming']=='direct']
        self.assertTrue(any(t.index('direct')<t.index('dependent') for t in direct))
        self.assertTrue(any(t.index('direct')>t.index('dependent') for t in direct))
        baseline['healing_dependencies'][0]['uptime']=1
        self.assertEqual(healing_repairs(baseline,ids,effects,catalog,weights,lambda t:True),[])

if __name__=='__main__':unittest.main()

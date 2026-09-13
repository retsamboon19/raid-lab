import copy
import unittest
from unittest.mock import patch
import rotation_search as rotation


class RotationSearchTests(unittest.TestCase):
    def row(self, members, damage, bursts=3, gap=8):
        return {'members': members, 'damage': damage, 'duration': 180,
                'burst_rotation': {'full_bursts': [{'start': 1+i*20, 'end': 11+i*20, 'complete': True} for i in range(bursts)],
                                  'stage_delays': [{'stage': '1', 'cast_time': 11+i*20+gap} for i in range(bursts)]}}

    def test_low_priority_cooldown_and_non_cdr_duration_choices_are_reserved(self):
        ids=['b1','b2','d1','d2','flex','nuke','cdr','short']
        cat={n:{'burst':'1' if n in ('b1','nuke','cdr') else '2' if n=='b2' else '3','weapon':'AR'} for n in ids}
        effects={'cdr':[{'stat':'burst_cooldown_reduce'}],'short':[{'stat':'fullburst_duration'}]}
        rows=[self.row(ids[:5],100)]
        options=rotation.proposals(rows,0,ids,cat,effects,lambda n,t:1000 if n=='nuke' else 1,lambda t:True)
        self.assertTrue(any(p['incoming']=='cdr' and p['outgoing']=='b1' for p in options))
        self.assertTrue(any(p['incoming']=='short' for p in options))

    def test_donor_exchange_keeps_units_disjoint_and_checks_both_teams(self):
        ids=list('abcdefghij');cat={n:{'burst':'1','weapon':'SMG'} for n in ids}
        rows=[self.row(ids[:5],100),self.row(ids[5:],100)]
        options=rotation.proposals(rows,0,ids,cat,{},lambda n,t:1,lambda t:len(t)==len(set(t))==5)
        self.assertTrue(options)
        for p in options:
            self.assertEqual(set(p['changes']),{0,1})
            flattened=sum(p['changes'].values(),[])
            self.assertEqual(set(flattened),set(ids));self.assertEqual(len(flattened),len(set(flattened)))

    def test_more_bursts_cannot_replace_higher_damage(self):
        base=self.row(['a'],100,3);faster=self.row(['b'],90,8,2)
        proposal={'outgoing':'a','incoming':'b','changes':{0:['b']},'reason':'gauge'}
        results=[base]
        def run(team,*args):return faster if team==('b',) else base
        with patch.object(rotation,'proposals',return_value=[proposal]):
            audit=rotation.improve(results,[],{}, {},lambda *a:0,lambda t:True,lambda t:[tuple(t)],lambda *a,**kw:None,run,180,lambda:False)
        self.assertEqual(results,[base]);self.assertTrue(audit)
        self.assertFalse(any(a['accepted'] for a in audit))

    def test_swap_rejected_if_donor_loss_outweighs_gain(self):
        base=[self.row(['a'],100),self.row(['b'],100)]
        proposal={'outgoing':'a','incoming':'b','changes':{0:['b'],1:['a']},'reason':'cooldown'}
        results=copy.deepcopy(base)
        # Track donor context using an additional stable slot.
        base=[self.row(['a','x'],100),self.row(['b','y'],100)];results=copy.deepcopy(base)
        proposal['changes']={0:['b','x'],1:['a','y']}
        def run(team,*args):
            if set(team)=={'b','x'}:return self.row(list(team),140,8,2)
            if set(team)=={'a','y'}:return self.row(list(team),40)
            return next(r for r in base if set(r['members'])==set(team))
        with patch.object(rotation,'proposals',side_effect=[[proposal],[]]):
            audit=rotation.improve(results,[],{}, {},lambda *a:0,lambda t:True,lambda t:[tuple(t)],lambda *a,**kw:None,run,180,lambda:False)
        self.assertEqual(results,base);self.assertFalse(any(a['accepted'] for a in audit))

    def test_timing_uses_full_burst_end_and_counts_missing_followup(self):
        row=self.row(['a'],100,2,5)
        self.assertEqual(rotation.timing(row)['within_5s'],2)
        row['burst_rotation']['stage_delays'].pop()
        self.assertEqual(rotation.timing(row)['within_5s'],1)
        self.assertEqual(rotation.timing(row)['cycles'],2)


if __name__=='__main__':unittest.main()

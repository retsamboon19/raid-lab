"""Joint team moves must improve the entire allocation and preserve donors."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import pairing_search


class JointSearchTests(unittest.TestCase):
    def test_bounded_order_choices_vary_target_and_donors(self):
        choices=[[('target-a',),('target-b',)],
                 [('donor-a',),('donor-b',),('donor-c',),('donor-d',)]]
        opening=pairing_search.diverse_order_combinations(choices,2)
        self.assertEqual({c[0] for c in opening},set(choices[0]))
        self.assertEqual({c[1] for c in opening},{choices[1][0],choices[1][1]})
        full=pairing_search.diverse_order_combinations(choices,4)
        self.assertEqual({c[1] for c in full},set(choices[1]))
        self.assertEqual(len(set(full)),4)

    def fixture(self,donor=False):
        teams=[[f'{letter}{i}' for i in range(1,6)] for letter in 'abcde']
        if donor:teams[1][2]='x'
        catalog={n:{'burst':'1' if n.endswith('1') else '2' if n.endswith('2') else '3'} for t in teams for n in t}
        catalog.update(x={'burst':'3'},y={'burst':'3'})
        ids=list(catalog)
        def valid(t):return len(t)==5 and len(set(t))==5 and {'1','2','3'}<={catalog[n]['burst'] for n in t}
        def row(t,damage=100,duration=180):return {'members':list(t),'damage':damage,'duration':duration}
        results=[row(t) for t in teams]
        priority=lambda n,t:1 if n in ('x','y') else 2
        guidance=SimpleNamespace(score=lambda t:100*({'x','y'}<=set(t))+sum(priority(n,t) for n in t),
                                 priority=priority,alternatives=lambda names,t,i:sorted(names,key=lambda n:priority(n,t),reverse=True))
        return results,ids,catalog,guidance,valid,row

    def test_completion_preserves_multiple_support_options(self):
        _,ids,catalog,guidance,valid,_=self.fixture()
        teams=pairing_search.complete_teams(['x','y'],ids,catalog,guidance,valid,limit=3)
        self.assertEqual(len(teams),3)
        self.assertEqual(len({frozenset(t) for t in teams}),3)
        self.assertTrue(all({'x','y'}<=set(t) and valid(t) for t in teams))

    def test_borrowed_partnership_repairs_donor_and_preserves_five_squads(self):
        results,ids,catalog,guidance,valid,_=self.fixture(donor=True)
        with patch.object(pairing_search,'packages',return_value=[['x','y']]):
            proposals=pairing_search.joint_proposals(results,0,ids,guidance,catalog,valid)
        together=[p for p in proposals if {'x','y'}<=set(p['changes'][0])]
        self.assertTrue(together)
        self.assertTrue(all(1 in p['changes'] for p in together))
        for p in together:
            allocation=[p['changes'].get(i,r['members']) for i,r in enumerate(results)]
            self.assertTrue(all(valid(t) for t in allocation))
            self.assertEqual(len({n for t in allocation for n in t}),25)

    def run_refinement(self,evaluator,donor=True,stop=lambda:False):
        results,ids,catalog,guidance,valid,row=self.fixture(donor)
        cache={};calls=[]
        def prefetch(teams,duration,detail=False,**kwargs):
            for t in teams:
                key=(tuple(t),duration,detail)
                if key not in cache:cache[key]=row(t,evaluator(t,duration,detail),duration);calls.append(key)
        def run(t,duration,detail=False):return cache[(tuple(t),duration,detail)]
        with patch.object(pairing_search,'packages',return_value=[['x','y']]):
            audit=pairing_search.refine_allocations(results,ids,catalog,guidance,valid,
                lambda t:[tuple(t)],prefetch,run,180,stop)
        return results,audit,calls

    def test_joint_improvement_does_not_require_either_isolated_move_to_win(self):
        def damage(t,duration,detail):
            return 300 if {'x','y'}<=set(t) else 50 if 'y' in t else 100
        results,audit,calls=self.run_refinement(damage)
        self.assertGreater(sum(r['damage'] for r in results),500)
        self.assertTrue(any({'x','y'}<=set(r['members']) for r in results))
        accepted=[r for r in audit if r['accepted']]
        self.assertTrue(accepted)
        self.assertTrue(any(len(r['affected_squads'])==2 for r in accepted))
        self.assertEqual(len({n for r in results for n in r['members']}),25)
        for record in accepted:
            for members in record['members'].values():self.assertIn((tuple(members),180,True),calls)

    def test_full_fight_donor_loss_can_veto_an_opening_damage_win(self):
        def damage(t,duration,detail):
            if {'x','y'}<=set(t):return 300 if not detail else 110
            if any(n.startswith('b') for n in t) and 'x' not in t:return 100 if not detail else 1
            if 'y' in t:return 1
            return 100
        results,audit,_=self.run_refinement(damage)
        self.assertFalse(any(r['accepted'] and len(r['affected_squads'])>1 for r in audit))
        self.assertIn('x',results[1]['members'])
        self.assertGreaterEqual(sum(r['damage'] for r in results),500)

    def test_joint_search_can_change_target_priority_while_verifying_donor(self):
        results,ids,catalog,guidance,valid,row=self.fixture(donor=True)
        cache={}
        def prefetch(teams,duration,detail=False,**kwargs):
            for t in teams:
                damage=300 if {'x','y'}<=set(t) and t.index('y')<t.index('x') else 80 if 'y' in t else 100
                cache[(tuple(t),duration,detail)]=row(t,damage,duration)
        def run(t,duration,detail=False):return cache[(tuple(t),duration,detail)]
        def orders(t):
            # Keep each support slot fixed; vary the damage-dealer priority.
            import itertools
            slots=[i for i,n in enumerate(t) if catalog[n]['burst']=='3']
            out=[]
            for permutation in itertools.permutations([t[i] for i in slots]):
                ordered=list(t)
                for i,n in zip(slots,permutation):ordered[i]=n
                out.append(tuple(ordered))
            return out
        with patch.object(pairing_search,'packages',return_value=[['x','y']]):
            audit=pairing_search.refine_allocations(results,ids,catalog,guidance,valid,
                orders,prefetch,run,180,lambda:False,rounds=1)
        accepted=[r for r in audit if r['accepted']]
        self.assertTrue(accepted)
        self.assertTrue(any(len(r['affected_squads'])>1 for r in accepted))
        self.assertTrue(any({'x','y'}<=set(r['members']) and r['members'].index('y')<r['members'].index('x') for r in results))

    def test_no_work_starts_after_search_deadline(self):
        results,audit,calls=self.run_refinement(lambda *args:300,stop=lambda:True)
        self.assertEqual(len(results),5);self.assertEqual(audit,[]);self.assertEqual(calls,[])

    def test_cancellation_does_not_publish_half_an_allocation(self):
        results,ids,catalog,guidance,valid,_=self.fixture(donor=True)
        before=copy.deepcopy(results)
        def cancel(*args,**kwargs):raise InterruptedError('Search cancelled.')
        with patch.object(pairing_search,'packages',return_value=[['x','y']]),self.assertRaises(InterruptedError):
            pairing_search.refine_allocations(results,ids,catalog,guidance,valid,lambda t:[tuple(t)],cancel,None,180,lambda:False)
        self.assertEqual(results,before)

    def test_required_part_passes_are_preserved_when_damage_rises(self):
        results,ids,catalog,guidance,valid,row=self.fixture(donor=True)
        def evidence(t,damage):
            result=row(t,damage)
            result['encounter_timeline']={'simulated_until':180,'critical_parts':[
                {'status':'failed' if {'x','y'}<=set(t) else 'passed'}]}
            return result
        results[:]=[evidence(r['members'],r['damage']) for r in results]
        cache={}
        def prefetch(teams,duration,detail=False,**kwargs):
            for t in teams:cache[(tuple(t),duration,detail)]=evidence(t,1000 if {'x','y'}<=set(t) else 100)
        def run(t,duration,detail=False):return cache[(tuple(t),duration,detail)]
        with patch.object(pairing_search,'packages',return_value=[['x','y']]):
            audit=pairing_search.refine_allocations(results,ids,catalog,guidance,valid,
                lambda t:[tuple(t)],prefetch,run,180,lambda:False,required=True)
        self.assertFalse(any(r['accepted'] for r in audit))
        self.assertFalse(any({'x','y'}<=set(r['members']) for r in results))

    def test_large_roster_screen_batch_is_bounded_before_order_expansion(self):
        results,ids,catalog,guidance,valid,row=self.fixture(donor=True)
        packages=[['x','y']]
        for i in range(40):
            package=[f'new{i}a',f'new{i}b'];packages.append(package)
            for n in package:ids.append(n);catalog[n]={'burst':'3'}
        cache={};batches=[];cost=0
        def prefetch(teams,duration,detail=False,**kwargs):
            nonlocal cost
            teams=list(teams);batches.append((detail,len(teams)));cost+=len(teams)
            for t in teams:cache[(tuple(t),duration,detail)]=row(t,100,duration)
        def run(t,duration,detail=False):return cache[(tuple(t),duration,detail)]
        def orders(t):
            t=list(t)
            return [tuple(t),tuple(reversed(t)),tuple(t[1:]+t[:1]),tuple(t[-1:]+t[:-1])]
        with patch.object(pairing_search,'packages',return_value=packages):
            self.assertGreater(sum(len(pairing_search.joint_proposals(results,i,ids,guidance,catalog,valid)) for i in range(5)),12)
            pairing_search.refine_allocations(results,ids,catalog,guidance,valid,orders,prefetch,run,
                180,lambda:cost>=100,rounds=1)
        # Each partnership moves at most two units, affecting at most three
        # squads. Reserve only two opening orders before promoting full fights.
        self.assertFalse(batches[0][0])
        self.assertLessEqual(batches[0][1],5+12*2*3)
        self.assertTrue(any(detail for detail,_ in batches),batches)


if __name__=='__main__':unittest.main()

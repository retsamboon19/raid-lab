import unittest
from boss_behavior import BehaviorTree,StrictWorld,UnsupportedBossAction,RUNNING,SUCCESS,FAILURE

def node(ident,kind,*children,**fields):
    return dict(ID=ident,Type=kind,Children=list(children),**fields)

class World(StrictWorld):
    def __init__(self):self.calls=[];self.cancelled=[]
    def action(self,n,t,s):
        self.calls.append((n['ID'],t))
        if n['Type']=='Wait':return SUCCESS if t-s['started']>=n['seconds'] else RUNNING
        if n['Type']=='Pass':return SUCCESS
        if n['Type']=='Fail':return FAILURE
        return super().action(n,t,s)
    def cancel(self,n,t):self.cancelled.append(n['ID'])

class Tests(unittest.TestCase):
    def test_sequence_waits_before_next_action(self):
        w=World();t=BehaviorTree(node(0,'Sequence',node(1,'Wait',seconds=2),node(2,'Pass')),w)
        self.assertEqual(t.advance(0),RUNNING);self.assertEqual(t.advance(1),RUNNING)
        self.assertNotIn(2,[i for i,_ in w.calls]);self.assertEqual(t.advance(2),SUCCESS)
    def test_part_destroy_condition_can_cancel_attack_branch(self):
        w=World();t=BehaviorTree(node(0,'ParallelSelector',node(1,'Wait',seconds=15),node(2,'Wait',seconds=3)),w)
        t.advance(0);self.assertEqual(t.advance(3),SUCCESS);self.assertEqual(w.cancelled,[1])
    def test_selector_only_runs_fallback_after_failure(self):
        w=World();t=BehaviorTree(node(0,'Selector',node(1,'Fail'),node(2,'Pass'),node(3,'Pass')),w)
        self.assertEqual(t.advance(0),SUCCESS);self.assertEqual([i for i,_ in w.calls],[1,2])
    def test_decorator_does_not_finish_a_running_attack(self):
        w=World();t=BehaviorTree(node(0,'ReturnSuccess',node(1,'Wait',seconds=3)),w)
        self.assertEqual(t.advance(0),RUNNING);self.assertEqual(t.advance(3),SUCCESS)
    def test_repeater_resets_child_clock(self):
        w=World();t=BehaviorTree(node(0,'Repeater',node(1,'Wait',seconds=2),SharedIntcount={'Int32mValue':2}),w)
        for time in [0,2,3,4]:self.assertEqual(t.advance(time),RUNNING)
        self.assertEqual(t.advance(5),SUCCESS)
    def test_unknown_action_is_never_treated_as_success(self):
        t=BehaviorTree(node(0,'UnresolvedAttack'),StrictWorld())
        with self.assertRaises(UnsupportedBossAction):t.advance(0)
    def test_clock_cannot_rewind(self):
        t=BehaviorTree(node(0,'Wait',seconds=10),World());t.advance(2)
        with self.assertRaises(ValueError):t.advance(1)

if __name__=='__main__':unittest.main()

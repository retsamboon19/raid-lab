import unittest
from boss_behavior import BehaviorTree,SUCCESS,RUNNING,FAILURE,UnsupportedBossAction
from boss_world import PartWorld
from test_boss_behavior import node

class Tests(unittest.TestCase):
    def test_real_part_hp_controls_attack_branch(self):
        attacks=[]
        def fire(n,t,s,w):attacks.append(t);return SUCCESS
        root=node(0,'Sequence',node(1,'TimeCount',ETimeCountTypemType='None',SinglemCustomTime=2),
                  node(2,'CheckHp',Int32mValue=0,BooleanmLower=False,PartsTypemPartsType='front',BooleanisUsingMianHp=False),
                  node(3,'TimelineSkill'))
        w=PartWorld({'front':100},{'TimelineSkill':fire});w.parts.spawn('front',100,0)
        tree=BehaviorTree(root,w);tree.advance(0);w.parts.damage('front',100,1)
        self.assertEqual(tree.advance(2),FAILURE);self.assertEqual(attacks,[])
        w=PartWorld({'front':100},{'TimelineSkill':fire});w.parts.spawn('front',100,0)
        tree=BehaviorTree(root,w);tree.advance(0);w.parts.damage('front',99,1)
        self.assertEqual(tree.advance(2),SUCCESS);self.assertEqual(attacks,[2])
    def test_unresolved_attack_cannot_silently_advance_boss(self):
        w=PartWorld({});tree=BehaviorTree(node(0,'AttackV3'),w)
        with self.assertRaises(UnsupportedBossAction):tree.advance(0)
    def test_repair_waits_for_completion(self):
        w=PartWorld({'front':100})
        tree=BehaviorTree(node(0,'RepairPartsVer2',**{'List`1_partsList':['front'],'Single_repairTime':.2}),w)
        self.assertEqual(tree.advance(0),RUNNING);self.assertFalse(w.parts.alive('front'))
        self.assertEqual(tree.advance(.2),SUCCESS);self.assertTrue(w.parts.alive('front'))

if __name__=='__main__':unittest.main()

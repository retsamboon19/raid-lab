import unittest
from qte_graph import QTEGraph

class Tests(unittest.TestCase):
    def graph(self):return QTEGraph([
        dict(id=1,kind='break',hp=10,duration=2,first=True,chain=[3,4]),
        dict(id=2,kind='counter',hp=10,duration=10,first=True),
        dict(id=3,kind='break',hp=20,duration=2,delay=.1),
        dict(id=4,kind='counter',hp=10,duration=10,delay=.1)],0,10)
    def test_actual_damage_unlocks_chain_without_carrying_overkill(self):
        q=self.graph();self.assertEqual(q.aim(0)['id'],1)
        self.assertEqual(q.hit(1,100,1),10);self.assertIsNone(q.aim(1.05))
        self.assertEqual(q.aim(1.1)['remaining'],20)
        q.hit(3,19,1.2);self.assertEqual(q.status,'active')
        q.hit(3,1,1.3);self.assertEqual(q.status,'passed')
    def test_grey_hit_fails_even_with_high_damage(self):
        q=self.graph();q.hit(2,1,0);self.assertEqual(q.status,'failed')
    def test_insufficient_damage_fails_per_target_deadline(self):
        q=self.graph();q.hit(1,9,1);q.advance(2);self.assertEqual(q.status,'failed')
    def test_shots_before_target_appears_do_nothing(self):
        q=self.graph();self.assertEqual(q.hit(3,100,0),0)
        self.assertEqual(q.targets[3]['remaining'],20)

if __name__=='__main__':unittest.main()

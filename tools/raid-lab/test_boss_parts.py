import unittest
from boss_parts import BossParts

class Tests(unittest.TestCase):
    def test_damage_interrupts_attack_without_automatic_success(self):
        p=BossParts();p.spawn('front',100,0,attack_at=5)
        p.damage('front',99,4);self.assertEqual(p.due_attacks(5),['front'])
        p=BossParts();p.spawn('front',100,0,attack_at=5)
        p.damage('front',100,4);self.assertEqual(p.due_attacks(5),[])
    def test_overkill_is_not_added_to_another_part(self):
        p=BossParts();p.spawn('left',10,0);p.spawn('right',10,0)
        self.assertEqual(p.damage('left',100,1),10);self.assertEqual(p.parts['right']['hp'],10)
    def test_self_destruction_is_not_a_player_interrupt(self):
        p=BossParts();p.spawn('front',100,0,attack_at=5)
        p.due_attacks(5);p.self_destruct('front',6)
        self.assertEqual(p.parts['front']['status'],'self-destructed')
        self.assertFalse(p.parts['front']['attack_cancelled'])
    def test_respawn_resets_health_and_deadline(self):
        p=BossParts();p.spawn('front',100,0,attack_at=5);p.damage('front',100,2)
        p.spawn('front',10,3,attack_at=4);self.assertTrue(p.alive('front'))
        self.assertEqual(p.due_attacks(4),['front']);self.assertEqual(p.due_attacks(5),[])
    def test_destroying_part_does_not_cancel_already_committed_attack(self):
        p=BossParts();p.spawn('back',100,0,attack_at=5);p.due_attacks(5)
        p.damage('back',100,6);self.assertFalse(p.parts['back']['attack_cancelled'])

if __name__=='__main__':unittest.main()

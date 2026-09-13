"""Candidate discovery must account for kit scaling without class weights."""
import unittest
from unittest.mock import patch
import core


class KitPriorTests(unittest.TestCase):
    def prior(self,effects,*,attack=100,hp=10000,level=10,role='Defender',cooldown=40):
        char={'skill_levels':{'1':level,'2':level,'3':level}}
        with patch.object(core.spec,'static_atk',return_value=attack),patch.object(core.spec,'calc_base_stats',return_value={'hp':hp}):
            return core.kit_search_attack(char,effects,{'class':role,'burst_cooldown':cooldown})

    @staticmethod
    def conversion(**changes):
        return {'source':'skill1','type':'buff','stat':'atk_from_hp_pct','target':'self',
                'values':{'1':1,'10':2},'trigger':{'timing':['burst_enter:3'],'condition':[]},**changes}

    @staticmethod
    def burst(**changes):
        return {'source':'skill3','type':'damage','stat':'sequential_damage:10','target':'enemies_random',
                'values':{'1':500,'10':1000},'trigger':{'timing':['burst_cast'],'condition':[]},**changes}

    def test_hp_scaling_damage_dealer_is_not_buried_by_lower_static_attack(self):
        hp_scaling=self.prior([self.conversion(),self.burst()],attack=100)
        static_attacker=self.prior([],attack=250,role='Attacker')
        self.assertGreater(hp_scaling,static_attacker)
        self.assertGreater(self.prior([self.conversion()],hp=20000),self.prior([self.conversion()]))

    def test_class_label_and_burst_stage_do_not_add_weight(self):
        effects=[self.conversion(),self.burst()]
        self.assertEqual(self.prior(effects,role='Defender'),self.prior(effects,role='Attacker'))
        self.assertEqual(self.prior(effects,role='Supporter'),self.prior(effects,role='Attacker'))

    def test_uses_owned_skill_level_not_maximum_value(self):
        self.assertGreater(self.prior([self.conversion(),self.burst()],level=10),
                           self.prior([self.conversion(),self.burst()],level=1))

    def test_unconditional_sequential_coefficient_changes_candidate_priority(self):
        self.assertGreater(self.prior([self.burst()]),self.prior([self.burst(stat='burst_damage')]))
        self.assertLess(self.prior([self.burst()],cooldown=60),self.prior([self.burst()],cooldown=20))

    def test_optional_enablers_and_dynamic_stacks_are_not_assumed(self):
        effects=[self.conversion(trigger={'condition':['during_shield']}),
                 self.burst(stat='sequential_damage:stored_hits'),
                 self.burst(scaling='stack_count'),
                 self.burst(trigger={'timing':['burst_cast'],'condition':['self_state:optional']})]
        self.assertEqual(self.prior(effects),self.prior([]))

    def test_other_recipient_hp_conversion_is_not_personal_attack(self):
        self.assertEqual(self.prior([self.conversion(target='allies_excl_self')]),self.prior([]))

    def test_damage_prior_is_bounded_and_does_not_multiply_aoe_targets(self):
        extreme=self.burst(values={'10':1e12})
        self.assertLessEqual(self.prior([extreme]),2*self.prior([]))
        self.assertEqual(self.prior([self.burst(target='all_enemies')]),self.prior([self.burst(target='target')]))
        self.assertEqual(self.prior([self.burst(target='all_projectiles')]),self.prior([]))

    def test_favorite_item_skill_data_is_used_by_the_heuristic(self):
        name=core.NAME_MAP['helm'];build=core.default_build();build['favorite_stage']=3
        roster={name:{'build':build}}
        settings=core.validate_settings({'content_mode':'practice','element':'Any'})
        with patch.object(core,'kit_search_attack',return_value=100) as prior:
            core.heuristic([name],roster,settings)
        effects=prior.call_args.args[1]
        self.assertTrue(any(e.get('favorite')==3 for e in effects))


if __name__=='__main__':unittest.main()

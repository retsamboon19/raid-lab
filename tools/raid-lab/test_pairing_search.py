import copy
import unittest
from types import SimpleNamespace as N
import core
from calculator.buff_manager import char_effects
from kit_dependencies import KitDependencies,possible_target
from search_guidance import SearchGuidance
from pairing_search import packages,complete_team,replacements


class PairingSearchTests(unittest.TestCase):
    def setup_kits(self,names,phase=0):
        ids=[core.NAME_MAP[n.lower()] for n in names]
        effects={n:char_effects(n,phase) for n in ids}
        return ids,KitDependencies(effects,core.META,core.CAT)

    def test_blanc_uses_actual_squad_members_not_fixed_partner_list(self):
        ids,k=self.setup_kits(['Blanc','Noir','Rouge','Liter'])
        r=next(r for r in k.requirements if r['kind']=='squad' and r['unit']==ids[0])
        self.assertEqual(set(r['providers']),set(ids[1:3]))
        self.assertEqual(k.inspect([ids[0],ids[3]])[0]['status'],'missing enabler')

    def test_bready_discovers_both_build_routes(self):
        ids,k=self.setup_kits(['Bready','Anchor: Innocent Maid','Rosanna: Chic Ocean','Liter'])
        pairs=set(k.packages())
        self.assertIn((ids[0],ids[1]),pairs)
        self.assertIn((ids[0],ids[2]),pairs)
        self.assertNotIn((ids[0],ids[3]),pairs)

    def test_shared_recovery_and_self_shield_cannot_enable_other_unit(self):
        meta={n:{} for n in ['crown','naga','shared','selfshield','direct']}
        effects={'crown':[{'name':'power','stat':'atk_dmg_pct','trigger':{'timing':['event:heal_received']}}],
                 'naga':[{'name':'core','stat':'core_dmg_pct','trigger':{'timing':['event:shield_applied']}}],
                 'shared':[{'stat':'heal_split','target':'all_allies'}],
                 'selfshield':[{'stat':'shield_from_max_hp_pct','target':'self'}],
                 'direct':[{'stat':'heal_hp_pct','target':'all_allies'}]}
        k=KitDependencies(effects,meta,{})
        self.assertEqual(k.requirements[0]['providers'],['direct'])
        self.assertEqual(k.requirements[1]['providers'],[])

    def test_element_weapon_and_class_target_filters(self):
        meta={'unit':{'element_code':'wind','weapon_type':'SR','class':'support'}}
        self.assertFalse(possible_target('allies_code:water','source','unit',meta))
        self.assertFalse(possible_target('allies_weapon:SG','source','unit',meta))
        self.assertFalse(possible_target('allies_class:attacker','source','unit',meta))
        self.assertTrue(possible_target('allies_code_weapon:wind:SR','source','unit',meta))

    def test_presence_does_not_claim_activation(self):
        ids,k=self.setup_kits(['Arcana','Isabel'])
        rows=[r for r in k.inspect(ids,N(log=N(buff_events=[],instant_events=[]))) if r['kind']=='named_ally']
        self.assertTrue(rows)
        self.assertTrue(all(r['status']=='not activated' for r in rows))
        rule=next(r for r in k.requirements if r['kind']=='named_ally')
        event=N(caster=ids[0],target=ids[1],name=rule['effect'],stat=rule['stat'],kind='activate')
        rows=k.inspect(ids,N(log=N(buff_events=[event],instant_events=[])))
        self.assertTrue(any(r['status']=='activation observed' for r in rows))

    def test_low_weight_enabler_receives_repair(self):
        ids,k=self.setup_kits(['Blanc','Liter','Cinderella','Scarlet','Modernia','Rouge'])
        weights=dict.fromkeys(ids,100);weights[ids[-1]]=1
        options=k.repairs(ids[:5],ids,weights,lambda t:True)
        self.assertTrue(any(p['consumer']==ids[0] and p['incoming']==ids[-1] for p in options))

    def make_guidance(self,names):
        ids=[core.NAME_MAP[n.lower()] for n in names]
        roster={n:{'build':core.default_build()} for n in ids}
        return ids,SearchGuidance(roster,core.CAT,{'element':'Electric'},dict.fromkeys(ids,100))

    def test_joint_cinderella_rouge_replacement_does_not_require_isolated_win(self):
        ids,g=self.make_guidance(['Liter','Crown','Scarlet','Modernia','Privaty','Cinderella','Rouge'])
        options=replacements(ids[:5],ids,g,core.CAT,lambda t:core.valid(t,{'element':'Any','encounter':{},'cdr':False,'healing':False}),limit=100)
        self.assertTrue(any(set(ids[-2:])<=set(p['members']) and len(p['incoming'])==2 for p in options))

    def test_seed_keeps_enabler_when_completing_team(self):
        ids,g=self.make_guidance(['Liter','Crown','Scarlet','Modernia','Privaty','Cinderella','Rouge'])
        team=complete_team(ids[-2:],ids,core.CAT,g,lambda t:core.valid(t,{'element':'Any','encounter':{},'cdr':False,'healing':False}))
        self.assertIsNotNone(team);self.assertTrue(set(ids[-2:])<=set(team))

    def test_team_card_needs_all_members_and_role_slots(self):
        ids,g=self.make_guidance(['Liter','Crown','Scarlet','Cinderella','Rouge'])
        g.edges=[];g.templates=[ids[1:4]];g.template_roles={tuple(ids[1:4]):['B1-CDR','FLEX']}
        self.assertEqual(g.pair_values(ids[1:3]),{})
        self.assertTrue(g.pair_values(ids))
        self.assertFalse(g.template_fits(ids[1:4],ids[1:4]))

    def test_preferred_partner_is_not_a_whole_character_ban(self):
        ids,g=self.make_guidance(['Cinderella','Liter','Crown','Scarlet','Privaty'])
        self.assertTrue(core.valid(ids,{'element':'Any','encounter':{},'cdr':False,'healing':False}))

    def test_cyclic_support_rule_reaches_simulator_and_remains_order_sensitive(self):
        names=['Liter','Mast: Romantic Maid','Anchor: Innocent Maid','Queen (Makoto)','Yukiko']
        ids=[core.NAME_MAP[n.lower()] for n in names]
        roster={n:{'id':n,'build':core.default_build(),'enabled':True,'assumptions':[]} for n in ids}
        settings=core.validate_settings({'content_mode':'practice','duration':30})
        g=SearchGuidance(roster,core.CAT,settings,dict.fromkeys(ids,100))
        settings['_support_cycles']=g.cycle_rules()
        self.assertTrue(settings['_support_cycles'])
        result=core.evaluate_candidate(tuple(ids),30,False,roster,settings)
        self.assertEqual(result['support_burst_patterns'][ids[1]][:3],[1,3,5])
        self.assertEqual(result['support_burst_patterns'][ids[2]][:3],[2,4,6])
        reversed_team=[ids[0],ids[2],ids[1],ids[3],ids[4]]
        result=core.evaluate_candidate(tuple(reversed_team),30,False,roster,settings)
        self.assertEqual(result['support_burst_patterns'][ids[2]][:3],[1,3,5])

    def test_intrinsic_weapon_change_is_not_a_missing_teammate(self):
        ids,k=self.setup_kits(['Moran'])
        self.assertFalse(any(r['kind']=='external_state' for r in k.requirements))


if __name__=='__main__':unittest.main()

"""Comparison contracts only: no registry read, native call or player execution."""
import copy
import unittest
from check_auto_preferences153 import NAMES,PATHS,validate_before,validate_after


def rows(private):
    return {scope:{'registryPath':'HKCU\\'+path,'keyExists':True,'values':{
        name:({'exists':True,'registryType':4,'value':1}if scope=='normal'or private else{'exists':False})for name in NAMES}}
        for scope,path in PATHS.items()}


class WitnessContracts(unittest.TestCase):
    def test_accepted_pre_then_private_only_inputs(self):
        before,after=rows(False),rows(True)
        self.assertEqual(validate_before(before),[]);self.assertEqual(validate_after(before,after),[])
    def test_normal_change_rejected(self):
        before,after=rows(False),rows(True);after['normal']['values'][NAMES[0]]['value']=0
        self.assertIn('normal_preferences_changed',validate_after(before,after))
    def test_private_missing_wrong_value_and_wrong_type_rejected(self):
        before=rows(False)
        for replacement in [{'exists':False},{'exists':True,'registryType':4,'value':0},{'exists':True,'registryType':3,'value':'01000000'}]:
            after=rows(True);after['private']['values'][NAMES[1]]=replacement
            self.assertTrue(validate_after(before,after))
    def test_changed_prebaseline_rejected(self):
        self.assertTrue(validate_before(rows(True)))


if __name__=='__main__':unittest.main()

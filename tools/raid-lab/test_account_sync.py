import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import account_sync as sync

class AccountSyncTests(unittest.TestCase):
    cookie='game_token=test-session; game_openid=test-account'
    def post(self,route,body,cookie):
        self.calls.append((route,body))
        if route.endswith('GetUserCharacters'):return {'code':0,'data':{'characters':[{'name_code':1}]}}
        if route.endswith('GetUserCharacterDetails'):return {'code':0,'data':{'character_details':[{'name_code':1}],'state_effects':[]}}
        return {'code':0,'data':{'outpost_info':{'recycle_room_researches':[{'tid':1}]}}}

    def setUp(self):self.calls=[]
    def test_every_refresh_fetches_roster_details_and_research_again(self):
        a,_=sync.fetch_latest(self.cookie,self.post)
        b,_=sync.fetch_latest(self.cookie,self.post)
        self.assertEqual(len(self.calls),6)
        self.assertTrue(a['complete'] and b['complete'])
        self.assertNotIn('cookie',json.dumps(a))
        self.assertNotIn('test-session',json.dumps(a))

    def test_expired_login_is_not_a_successful_cached_refresh(self):
        with self.assertRaises(sync.LoginRequired):
            sync.fetch_latest(self.cookie,lambda *args:{'code':300001})

    def test_browser_profile_identity_is_used_without_extracting_cookies(self):
        sync.fetch_latest('',self.post,preferred_area=219,account_id='community-profile-id')
        self.assertTrue(all(body['intl_open_id']=='community-profile-id' for _,body in self.calls))
        self.assertTrue(all(body['nikke_area_id']==219 for _,body in self.calls))

    def test_forbidden_is_not_an_instruction_to_sign_in_again(self):
        with self.assertRaises(sync.RefreshError) as caught:
            sync.fetch_latest('',lambda *args:{'code':403},account_id='profile-id')
        self.assertNotIsInstance(caught.exception,sync.LoginRequired)

    def test_region_discovery_continues_after_unavailable_region(self):
        def post(route,body,cookie):
            if route.endswith('GetUserCharacters') and body['nikke_area_id']==83:return {'code':123456}
            return self.post(route,body,cookie)
        _,metadata=sync.fetch_latest(self.cookie,post)
        self.assertEqual(metadata['area'],1)

    def test_cancellation_is_not_wrapped_as_network_failure(self):
        def post(*args):raise InterruptedError()
        with self.assertRaises(InterruptedError):sync.fetch_latest(self.cookie,post)

    def test_missing_details_or_research_fail_closed(self):
        for missing in ('GetUserCharacterDetails','GetUserProfileOutpostInfo'):
            with self.subTest(missing=missing),self.assertRaises(sync.RefreshError):
                sync.fetch_latest(self.cookie,lambda route,*args:{'code':0,'data':{}} if route.endswith(missing) else self.post(route,*args))

    def test_validation_failure_preserves_previous_saved_roster(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'roster.json';path.write_text('{"roster":[]}',encoding='utf-8')
            with patch('core.import_roster',side_effect=ValueError('invalid')):
                with self.assertRaises(ValueError):sync.convert_and_save({},path)
            self.assertEqual(path.read_text(encoding='utf-8'),'{"roster":[]}')

    def test_live_build_replaces_old_gear_while_preserving_enabled_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'roster.json'
            path.write_text(json.dumps({'roster':[{'id':'a','enabled':False,'build':{'atk':1}}]}),encoding='utf-8')
            fresh={'roster':[{'id':'a','enabled':True,'build':{'atk':2}}]}
            with patch('core.import_roster',return_value=fresh):
                result=sync.convert_and_save({'captured_at':'2026-09-11T01:00:00+00:00'},path)
            self.assertFalse(result['roster'][0]['enabled'])
            self.assertEqual(result['roster'][0]['build']['atk'],2)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),result)

if __name__=='__main__':unittest.main()

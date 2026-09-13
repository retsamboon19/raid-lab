import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import accounts
import core
import server
import browser_connection
from test_browser_connection import CHROME, BrowserConnectionTests

class AccountStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.patch=patch.object(accounts,'ROOT',self.root)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.roster=core.demo_roster()[:2]

    def test_url_validation(self):
        token=base64.b64encode(b'29080-17034417567439165047').decode()
        self.assertEqual(accounts.public_identity('https://www.blablalink.com/user?openid='+token),'17034417567439165047')
        for url in ['https://evil.test/?openid='+token,'http://www.blablalink.com/user?openid='+token,'https://www.blablalink.com/user?openid=bad','https://www.blablalink.com:443/user?openid='+token]:
            with self.assertRaises(ValueError):accounts.public_identity(url)

    def test_replace_does_not_merge_builds_or_ownership(self):
        a=accounts.import_file({'account_id':'a','account_name':'A','roster':self.roster})
        changed=json.loads(json.dumps(self.roster[:1]));changed[0]['build']['skill_levels']['1']=2
        b=accounts.import_file({'account_id':'b','account_name':'B','roster':changed})
        before=accounts.read('a')
        accounts.import_file({'account_id':'b','roster':self.roster[1:]})
        self.assertEqual(accounts.read('a'),before)
        self.assertEqual(len(accounts.read('b')['roster']),1)
        self.assertEqual(accounts.read('b')['roster'][0]['id'],self.roster[1]['id'])
        self.assertEqual(len(accounts.listing()),2)

    def test_export_reimport_reuses_same_account(self):
        a=accounts.import_file({'roster':self.roster},'First account')
        b=accounts.import_file(a)
        self.assertEqual(a['account_id'],b['account_id'])
        self.assertEqual(len(accounts.listing()),1)

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):accounts.read('../roster')

    def test_delete_removes_only_selected_account_cache_and_history(self):
        from test_report_history import report
        for key in ('a', 'b'):
            accounts.import_file({'account_id':key,'roster':self.roster})
            accounts.account_sync.atomic_json(accounts.account_dir(key)/'snapshot.json', {'private':'details'})
        saved=server.history_store('a').save(report())
        self.assertIsNone(server.history_store('b').get(saved['id']))
        other=server.history_store('b').save(report(total=555))
        accounts.delete('a')
        self.assertFalse(accounts.account_dir('a').exists())
        self.assertEqual(server.history_store('b').get(other['id'])['report']['total'],555)
        self.assertTrue((accounts.account_dir('b')/'snapshot.json').exists())

    def test_deleted_legacy_account_does_not_reappear(self):
        accounts.account_sync.atomic_json(self.root/'roster.json',{'roster':self.roster})
        accounts.migrate()
        accounts.delete('my-account')
        self.assertEqual(accounts.listing(),[])
        self.assertFalse((self.root/'roster.json').exists())

    def test_history_directories_are_per_account(self):
        accounts.import_file({'account_id':'a','roster':self.roster})
        accounts.import_file({'account_id':'b','roster':self.roster})
        with patch.object(server.report_history,'ReportHistory') as history:
            server.history_store('a');server.history_store('b')
            self.assertNotEqual(history.call_args_list[0].args[0],history.call_args_list[1].args[0])
            self.assertEqual(history.call_args_list[0].args[0],accounts.account_dir('a'))

    def test_legacy_migration_never_replaces_saved_account(self):
        accounts.account_sync.atomic_json(self.root/'roster.json',{'roster':self.roster})
        accounts.migrate();before=accounts.read('my-account')
        accounts.account_sync.atomic_json(self.root/'roster.json',{'roster':[]})
        accounts.migrate();self.assertEqual(accounts.read('my-account'),before)

class PublicImportTests(BrowserConnectionTests):
    def test_public_import_uses_target_region_and_independent_save(self):
        token=base64.b64encode(b'29080-17034417567439165047').decode()
        job=browser_connection.start(profile_url='https://www.blablalink.com/user?openid='+token)
        browser_connection.connect(job,'chrome')
        login=self.make_login()
        calls=[]
        def request(route,body):
            calls.append((route,body))
            if route=='player_info':return {'code':0,'data':{'area_id':'85','role_name':'ZERO1'}}
            return self.post(route,body,None)
        login.request.side_effect=request
        with patch.object(browser_connection.browser_login,'LoginBrowser',return_value=login),patch.object(accounts,'save_snapshot',return_value={'refreshed_at':'now'}) as saved:
            browser_connection.run(job,CHROME)
        self.assertEqual(browser_connection.state(job)['status'],'done')
        for route,body in calls:
            if route.startswith('Game/'):
                self.assertEqual(body['intl_open_id'],'17034417567439165047')
                self.assertEqual(body['nikke_area_id'],85)
        self.assertEqual(saved.call_args.args[1:4],('17034417567439165047',85,'ZERO1'))
        self.assertTrue(saved.call_args.kwargs['public'])

if __name__=='__main__':unittest.main()

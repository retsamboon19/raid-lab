import json
import unittest
from unittest.mock import patch, MagicMock
import browser_connection as b
import account_sync

CHROME = {'id': 'chrome', 'name': 'Google Chrome', 'path': 'C:/Chrome/chrome.exe'}
COOKIE = 'game_token=test-secret; game_openid=test-account'

class BrowserConnectionTests(unittest.TestCase):
    def setUp(self):
        b.JOBS.clear()
        for name, value in [('browsers', [CHROME])]:
            p = patch.object(b, name, return_value=value); p.start(); self.addCleanup(p.stop)
        self.pref = patch.object(b.browser_login, 'preference', return_value={}).start()
        self.remember = patch.object(b.browser_login, 'remember').start()
        self.thread = patch.object(b.threading, 'Thread').start()
        self.addCleanup(patch.stopall)

    def job(self):
        job = b.start(); b.connect(job, 'chrome'); return job

    def post(self, route, body, cookie):
        if route.endswith('GetUserCharacters'):
            return {'code': 0, 'data': {'characters': [{'name_code': 1}]}}
        if route.endswith('GetUserCharacterDetails'):
            return {'code': 0, 'data': {'character_details': [{'name_code': 1}]}}
        return {'code': 0, 'data': {'outpost_info': {'recycle_room_researches': [{'tid': 1}]}}}

    def make_login(self):
        login=MagicMock()
        login.just_signed_in=False
        login.account.return_value={'openid':'profile-id','area':83}
        login.request.side_effect=lambda route,body:self.post(route,body,None)
        return login

    def test_first_use_waits_for_selection_without_paths(self):
        job = b.start()
        self.assertEqual(b.state(job)['status'], 'needs_browser')
        self.assertNotIn('path', json.dumps(b.state(job)))
        self.thread.assert_not_called()

    def test_remembered_browser_starts_automatically(self):
        self.pref.return_value = {'browser': 'chrome'}
        job = b.start()
        self.assertEqual(b.state(job)['status'], 'running')
        self.thread.assert_called_once()

    def test_force_selection_and_uninstalled_preference(self):
        for saved, force in [('chrome', True), ('missing', False)]:
            b.JOBS.clear(); self.pref.return_value = {'browser': saved}
            self.assertEqual(b.state(b.start(force))['status'], 'needs_browser')

    def test_unavailable_browser_is_actionable_error(self):
        with patch.object(b, 'browsers', return_value=[]):
            self.assertIn('Install Chrome', b.state(b.start())['error'])

    def test_invalid_executable_cannot_be_selected(self):
        job = b.start()
        with self.assertRaises(ValueError): b.connect(job, 'C:/other.exe')
        self.thread.assert_not_called()

    def test_duplicate_start_and_connect_do_not_spawn_twice(self):
        job = self.job()
        self.assertEqual(b.start(), job)
        with self.assertRaises(ValueError): b.connect(job, 'chrome')
        self.thread.assert_called_once()

    def test_success_reads_all_endpoints_and_exposes_no_credentials(self):
        job = self.job(); login = self.make_login()
        fresh = {'roster': [], 'source': 'BlaBlaLink', 'refreshed_at': 'now'}
        with patch.object(b.browser_login, 'LoginBrowser', return_value=login), \
             patch.object(login, 'request', side_effect=lambda route,body:self.post(route,body,None)) as post, \
             patch.object(account_sync, 'convert_and_save', return_value=fresh) as save:
            b.run(job, CHROME)
        self.assertEqual(post.call_count, 3)
        self.assertTrue(save.call_args.args[0]['complete'])
        self.assertEqual(b.state(job)['status'], 'done')
        self.assertNotIn('test-secret', json.dumps(b.state(job)))
        self.assertNotIn('test-account', json.dumps(b.state(job)))
        login.close.assert_called_once()
        b.cancel(job); self.assertEqual(b.state(job)['status'], 'done')

    def test_cancellation_during_fetch_never_saves(self):
        job = self.job(); login = self.make_login()
        def cancelled_post(*args):
            b.cancel(job)
            return self.post(*args)
        with patch.object(b.browser_login, 'LoginBrowser', return_value=login), \
             patch.object(login, 'request', side_effect=lambda route,body:cancelled_post(route,body,None)), \
             patch.object(account_sync, 'convert_and_save') as save:
            b.run(job, CHROME)
        save.assert_not_called(); self.assertEqual(b.state(job)['status'], 'error')

    def test_expired_session_waits_for_login_then_imports(self):
        job = self.job(); login = self.make_login()
        login.account.side_effect=[account_sync.LoginRequired(),{'openid':'profile-id','area':83}]
        with patch.object(b.browser_login, 'LoginBrowser', return_value=login), \
             patch.object(account_sync, 'convert_and_save', return_value={'refreshed_at':'now'}):
            b.run(job,CHROME)
        login.sign_in.assert_called_once()
        self.assertEqual(b.state(job)['status'],'done')

    def test_rejected_fresh_login_never_reopens_browser(self):
        job=self.job(); login=self.make_login(); login.just_signed_in=True
        login.account.side_effect=account_sync.LoginRequired('Session rejected')
        with patch.object(b.browser_login,'LoginBrowser',return_value=login): b.run(job,CHROME)
        login.sign_in.assert_not_called()
        self.assertEqual(b.state(job)['status'],'error')
        self.assertIn('automatic sign-in retries have stopped',b.state(job)['error'])

    def test_missing_roster_is_not_a_login_retry(self):
        job=self.job(); login=self.make_login()
        login.request.return_value={'code':0,'data':{'characters':[]}};login.request.side_effect=None
        with patch.object(b.browser_login,'LoginBrowser',return_value=login): b.run(job,CHROME)
        login.sign_in.assert_not_called()
        self.assertEqual(b.state(job)['status'],'error')
        self.assertIn('no roster',b.state(job)['error'])

    def test_denied_request_is_not_a_login_retry(self):
        job=self.job(); login=self.make_login()
        login.request.return_value={'code':403};login.request.side_effect=None
        with patch.object(b.browser_login,'LoginBrowser',return_value=login): b.run(job,CHROME)
        login.sign_in.assert_not_called(); self.assertIn('403',b.state(job)['error'])

    def test_missing_details_does_not_save(self):
        job = self.job(); login = self.make_login()
        def post(route, *args):
            return {'code': 0, 'data': {}} if route.endswith('GetUserCharacterDetails') else self.post(route, *args)
        with patch.object(b.browser_login, 'LoginBrowser', return_value=login), \
             patch.object(login, 'request', side_effect=lambda route,body:post(route,body,None)), \
             patch.object(account_sync, 'convert_and_save') as save:
            b.run(job, CHROME)
        save.assert_not_called(); self.assertEqual(b.state(job)['status'], 'error')

    def test_transport_errors_do_not_echo_secrets(self):
        job = self.job()
        with patch.object(b.browser_login, 'LoginBrowser', side_effect=RuntimeError(COOKIE)):
            b.run(job, CHROME)
        self.assertNotIn('test-secret', json.dumps(b.state(job)))

    def test_timeout_signals_worker_and_allows_retry(self):
        job = self.job(); b.JOBS[job]['created'] = 0
        self.assertEqual(b.state(job)['status'], 'error')
        self.assertTrue(b.JOBS[job]['cancel'].is_set())
        self.assertNotEqual(b.start(), job)

if __name__ == '__main__': unittest.main()

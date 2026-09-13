from pathlib import Path
import json
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import browser_login as b

class BrowserLoginTests(unittest.TestCase):
    def test_persistent_preferences_contain_no_session(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(b, 'DATA_ROOT', Path(folder)):
            b.remember('edge', 83)
            self.assertEqual(b.preference(), {'browser': 'edge', 'area': 83})
            self.assertEqual(list(Path(folder).iterdir()), [Path(folder) / 'browser.json'])

    def login(self, folder):
        login = object.__new__(b.LoginBrowser)
        login.client = None; login.reader_process = None; login.just_signed_in = False
        login.profile = Path(folder); login.selected = {'id': 'chrome', 'name': 'Chrome', 'path': 'C:/Chrome/chrome.exe'}
        login.cancelled = MagicMock(); login.cancelled.wait.return_value = False; login.cancelled.is_set.return_value = False
        login.phase = MagicMock()
        return login

    def test_interactive_login_has_no_automation_and_waits_until_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder)
            with patch.object(login, 'close'), patch.object(login, 'open_reader') as read, \
                 patch.object(b, 'profile_running', side_effect=[False, True, True, False]) as running, \
                 patch.object(b.subprocess, 'Popen') as launch, patch.object(b, 'DevTools') as cdp:
                login.sign_in()
            args = launch.call_args.args[0]
            self.assertFalse(any('debugging' in x or 'automation' in x or 'headless' in x for x in args))
            self.assertIn('--user-data-dir=' + folder, args)
            self.assertEqual(args[-1], b.HOME_URL)
            self.assertEqual(running.call_count, 4)
            read.assert_called_once(); cdp.assert_not_called()
            self.assertTrue(login.just_signed_in)

    def test_open_normal_window_is_reused_without_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder)
            with patch.object(login, 'close'), patch.object(login, 'open_reader'), \
                 patch.object(b, 'profile_running', side_effect=[True, True, False]), \
                 patch.object(b.subprocess, 'Popen') as launch:
                login.sign_in()
            launch.assert_not_called()

    def test_reader_only_opens_blank_page_after_normal_browser_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder); client = MagicMock()
            client.call.side_effect = [{'targetInfos': [{'type': 'page', 'targetId': 't', 'url': 'about:blank'}]}, {'sessionId': 's'}]
            with patch.object(b, 'profile_running', return_value=False), \
                 patch.object(b, 'endpoint', side_effect=[None, 'ws://reader']), \
                 patch.object(b, 'DevTools', return_value=client), patch.object(b.subprocess, 'Popen') as launch:
                login.open_reader()
            args = launch.call_args.args[0]
            self.assertIn('--headless=new', args)
            self.assertIn('--remote-debugging-address=127.0.0.1', args)
            self.assertEqual(args[-1], 'about:blank')
            self.assertNotIn(b.HOME_URL, args)
            self.assertFalse(any('google' in str(call) for call in client.call.call_args_list))

    def test_cancelled_signin_never_attaches_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder); login.cancelled.wait.return_value = True
            with patch.object(login, 'close'), patch.object(login, 'open_reader') as reader, \
                 patch.object(b, 'profile_running', return_value=True):
                with self.assertRaises(InterruptedError): login.sign_in()
            reader.assert_not_called()

    def test_requests_use_browser_credentials_and_allowlisted_routes(self):
        login=object.__new__(b.LoginBrowser);login.client=MagicMock();login.session='s'
        login.client.call.return_value={'result':{'value':{'code':0,'data':{}}}}
        self.assertEqual(login.request('Game/GetUserCharacters',{'intl_open_id':'profile-id'})['code'],0)
        script=login.client.call.call_args.args[1]['expression']
        self.assertIn("credentials: 'include'",script)
        self.assertIn("redirect: 'error'",script)
        self.assertNotIn('Cookie',script)
        self.assertIn('/api/game/proxy/Game/GetUserCharacters',script)
        with self.assertRaises(ValueError):login.request('Game/ChangeSomething',{})

    def test_identity_and_server_come_from_selected_account(self):
        login=object.__new__(b.LoginBrowser);login.client=MagicMock();login.session='s';login.phase=MagicMock()
        login.cancelled=MagicMock();login.cancelled.wait.return_value=False
        login.client.call.return_value={'result':{'value':True}}
        login.request=MagicMock(side_effect=[{'code':0,'data':{'info':{'intl_openid':'29080-profile-id'}}}, {'code':0,'data':{'role_info':{'area_id':219}}}])
        self.assertEqual(login.account(),{'openid':'profile-id','area':219})
        self.assertEqual([x.args[0] for x in login.request.call_args_list],['account','role'])

    def test_reader_closes_after_use(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder); client = MagicMock(); login.client = client
            login.close()
            client.call.assert_called_once_with('Browser.close')
            client.close.assert_called_once()

    def test_repeated_cleanup_does_not_close_a_new_refresh_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            login = self.login(folder); login.client = MagicMock()
            login.close()
            with patch.object(b, 'endpoint') as endpoint:
                login.close()
            endpoint.assert_not_called()

    def test_finish_button_only_closes_own_interactive_profile(self):
        selected={'id':'chrome','path':'C:/Chrome/chrome.exe'}
        with patch.object(b.subprocess,'run',return_value=MagicMock(returncode=0)) as run:
            b.finish_signin(selected)
        args=run.call_args
        self.assertEqual(args.kwargs['env']['RAID_LAB_LOGIN_PROFILE'],str(b.DATA_ROOT/'signin-profiles'/'chrome'))
        script=args.args[0][-1]
        self.assertIn('CloseMainWindow()',script)
        self.assertIn('--type=|--headless',script)
        self.assertNotIn('Stop-Process',script)

    def test_process_check_returns_only_status_and_uses_literal_profile(self):
        profile = Path('C:/A folder/RaidLab/signin-profiles/chrome')
        with patch.object(b.subprocess, 'run', return_value=MagicMock(returncode=0, stdout='closed')) as run:
            self.assertFalse(b.profile_running(profile, 'C:/Chrome/chrome.exe'))
        args = run.call_args
        self.assertEqual(args.kwargs['env']['RAID_LAB_LOGIN_PROFILE'], str(profile))
        self.assertNotIn(str(profile), args.args[0][-1])

    def test_devtools_rejects_remote_endpoints(self):
        with patch.object(b.websocket, 'create_connection') as connect:
            for url in ['ws://example.com/devtools/browser/id', 'ws://127.0.0.1:123/devtools/page/id']:
                with self.assertRaises(b.BrowserError): b.DevTools(url)
        connect.assert_not_called()

    def test_devtools_handles_events_before_response(self):
        socket = MagicMock(); socket.recv.side_effect = [json.dumps({'method': 'Page.event'}), json.dumps({'id': 1, 'result': {'ok': True}})]
        with patch.object(b.websocket, 'create_connection', return_value=socket):
            client = b.DevTools('ws://127.0.0.1:123/devtools/browser/id')
            self.assertEqual(client.call('Target.getTargets'), {'ok': True})

    def test_stale_debugging_port_does_not_attach_to_another_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder); (profile / 'DevToolsActivePort').write_text('12345\n/devtools/browser/expected\n')
            response = MagicMock(); response.read.return_value = json.dumps({'webSocketDebuggerUrl': 'ws://127.0.0.1:12345/devtools/browser/other'}).encode()
            opener = MagicMock(); opener.open.return_value.__enter__.return_value = response
            with patch.object(b.urllib.request, 'build_opener', return_value=opener):
                self.assertIsNone(b.endpoint(profile))

if __name__ == '__main__': unittest.main()

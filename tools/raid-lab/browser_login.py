"""Persistent app-owned browser login. Authenticated reads stay in the browser."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.browser-runtime'))
import websocket

HOME_URL = 'https://www.blablalink.com/shiftyspad'
ROUTES = frozenset(('Game/GetUserCharacters', 'Game/GetUserCharacterDetails', 'Game/GetUserProfileOutpostInfo'))
DATA_ROOT = Path(os.environ.get('LOCALAPPDATA', str(ROOT / 'private'))) / 'RaidLab'
COMMON = {'game_id': '29080', 'area_id': 'global', 'source': 'pc_web', 'intl_game_id': '29080', 'language': 'en', 'env': 'prod'}

class BrowserError(Exception):
    pass

def profile_running(profile, executable):
    """Check only this app profile's main process; never return other command lines."""
    env = dict(os.environ, RAID_LAB_LOGIN_PROFILE=str(profile), RAID_LAB_LOGIN_EXE=Path(executable).name)
    script = """$ErrorActionPreference='Stop'
$items=Get-CimInstance Win32_Process -Filter ("Name='"+$env:RAID_LAB_LOGIN_EXE+"'")
$match=$items | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:RAID_LAB_LOGIN_PROFILE) -and $_.CommandLine -notmatch '--type=' }
if ($match) { 'running' } else { 'closed' }
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            env=env, capture_output=True, text=True, timeout=10,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or result.stdout.strip() not in ('running', 'closed'):
        raise BrowserError('Could not check the account window. Close it and try Load my account again.')
    return result.stdout.strip() == 'running'

def finish_signin(selected):
    """User's Import button gracefully closes only the app's sign-in window."""
    profile = DATA_ROOT / 'signin-profiles' / selected['id']
    env = dict(os.environ, RAID_LAB_LOGIN_PROFILE=str(profile), RAID_LAB_LOGIN_EXE=Path(selected['path']).name)
    script = """$ErrorActionPreference='Stop'
$items=Get-CimInstance Win32_Process -Filter ("Name='"+$env:RAID_LAB_LOGIN_EXE+"'")
$match=$items | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($env:RAID_LAB_LOGIN_PROFILE) -and $_.CommandLine -notmatch '--type=|--headless' }
foreach ($item in $match) { $process=Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue; if ($process) { [void]$process.CloseMainWindow() } }
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            env=env, capture_output=True, timeout=10,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise BrowserError('Close the BlaBlaLink account window to finish importing.')

def browsers():
    found = []
    if os.name != 'nt':
        return found
    import winreg
    for ident, title, exe, relative in (
        ('chrome', 'Google Chrome', 'chrome.exe', 'Google/Chrome/Application/chrome.exe'),
        ('edge', 'Microsoft Edge', 'msedge.exe', 'Microsoft/Edge/Application/msedge.exe'),
        ('brave', 'Brave', 'brave.exe', 'BraveSoftware/Brave-Browser/Application/brave.exe'),
        ('vivaldi', 'Vivaldi', 'vivaldi.exe', 'Vivaldi/Application/vivaldi.exe'),
    ):
        candidates = []
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\' + exe,
                                        0, winreg.KEY_READ | view) as key:
                        candidates.append(Path(str(winreg.QueryValue(key, None)).strip('"')))
                except OSError:
                    pass
        candidates += [Path(os.environ[k]) / relative for k in ('LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)') if os.environ.get(k)]
        path = next((p for p in candidates if p.is_file()), None)
        if path:
            found.append({'id': ident, 'name': title, 'path': str(path)})
    return found

def preference():
    try:
        data = json.loads((DATA_ROOT / 'browser.json').read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def remember(browser, area=None):
    import account_sync
    data = {'browser': browser}
    if area is not None:
        data['area'] = area
    account_sync.atomic_json(DATA_ROOT / 'browser.json', data)

class DevTools:
    def __init__(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != 'ws' or parsed.hostname != '127.0.0.1' or not parsed.path.startswith('/devtools/browser/'):
            raise BrowserError('Invalid local browser connection.')
        self.socket = websocket.create_connection(url, timeout=8, suppress_origin=True, http_no_proxy=['127.0.0.1', 'localhost'])
        self.serial = 0

    def call(self, method, params=None, session=None, timeout=12):
        self.serial += 1
        message = {'id': self.serial, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        self.socket.send(json.dumps(message))
        self.socket.settimeout(timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = json.loads(self.socket.recv())
            if result.get('id') != self.serial:
                continue
            if 'error' in result:
                raise BrowserError('The account browser could not complete the connection. Close its window and try again.')
            return result.get('result', {})
        raise BrowserError('The account browser stopped responding. Close its window and try again.')

    def close(self):
        self.socket.close()

def endpoint(profile):
    try:
        lines = (profile / 'DevToolsActivePort').read_text(encoding='utf-8').splitlines()
        port = int(lines[0])
        if not 0 < port < 65536 or not lines[1].startswith('/devtools/browser/'):
            return None
        url = 'ws://127.0.0.1:' + str(port) + lines[1]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/json/version', timeout=1) as response:
            data = json.load(response)
        return url if data.get('webSocketDebuggerUrl') == url else None
    except (OSError, ValueError, IndexError):
        return None

class LoginBrowser:
    def __init__(self, selected, cancelled, phase):
        self.client = None
        self.session = None
        self.target = None
        self.reader_process = None
        self.just_signed_in = False
        self.selected = selected
        self.cancelled = cancelled
        self.phase = phase
        # A new profile avoids reusing the old debugging-enabled login window.
        self.profile = DATA_ROOT / 'signin-profiles' / selected['id']
        self.profile.mkdir(parents=True, exist_ok=True)
        try:
            if (self.profile / 'raid-lab-imported').exists():
                self.open_reader()
            else:
                self.sign_in()
        except Exception:
            self.close()
            raise

    def wait_for_close(self):
        while profile_running(self.profile, self.selected['path']):
            self.phase('Finish signing in and select your NIKKE account, then close the account browser window. Import starts automatically.')
            if self.cancelled.wait(2):
                raise InterruptedError()

    def sign_in(self):
        self.close()
        # The interactive login has NO debugging/automation flags or connection.
        # We do not read its page, credentials or cookies during authentication.
        if not profile_running(self.profile, self.selected['path']):
            self.phase('Opening a normal ' + self.selected['name'] + ' window for sign-in')
            process = subprocess.Popen([self.selected['path'], '--user-data-dir=' + str(self.profile),
                                        '--no-first-run', '--no-default-browser-check', '--new-window', HOME_URL],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 30
            while not profile_running(self.profile, self.selected['path']):
                if self.cancelled.wait(.5):
                    raise InterruptedError()
                if time.monotonic() >= deadline or process.poll() is not None:
                    raise BrowserError('The sign-in browser closed before it was ready. Try Load my account again.')
        self.wait_for_close()
        if self.cancelled.is_set():
            raise InterruptedError()
        self.open_reader()
        self.just_signed_in = True

    def open_reader(self):
        # Wait for any normal sign-in window to close before connecting at all.
        url = endpoint(self.profile)
        if not url:
            self.wait_for_close()
        if self.cancelled.is_set():
            raise InterruptedError()
        self.phase('Reading the saved BlaBlaLink session')
        if not url:
            (self.profile / 'DevToolsActivePort').unlink(missing_ok=True)
            self.reader_process = subprocess.Popen([self.selected['path'], '--user-data-dir=' + str(self.profile),
                          '--headless=new', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
                          '--no-first-run', '--no-default-browser-check', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 30
        while not url and time.monotonic() < deadline:
            if self.cancelled.wait(.3):
                raise InterruptedError()
            url = endpoint(self.profile)
            if url:
                break
        if not url:
            raise BrowserError('Could not open the saved-session reader. Close the account window and retry.')
        self.client = DevTools(url)
        try:
            targets = self.client.call('Target.getTargets').get('targetInfos', [])
            target = next((t for t in targets if t.get('type') == 'page' and t.get('url') == 'about:blank'), None)
            self.target = target['targetId'] if target else self.client.call('Target.createTarget', {'url': 'about:blank'})['targetId']
            self.session = self.client.call('Target.attachToTarget', {'targetId': self.target, 'flatten': True})['sessionId']
        except Exception:
            self.close()
            raise

    def request(self, route, body=None):
        paths = {name: ('/api/game/proxy/' + name, 'POST') for name in ROUTES}
        paths['account'] = ('/api/ugc/proxy/standalonesite/User/GetUserInfoNew', 'POST')
        paths['role'] = ('/api/game/proxy/Game/GetSavedRoleInfo', 'GET')
        if route not in paths:
            raise ValueError('Unsupported account endpoint.')
        path, method = paths[route]
        expression = """(async () => {
          if (!['https://www.blablalink.com','https://blablalink.com'].includes(location.origin))
            return {code: -1, transport: 'page'};
          try {
            const config = %s;
            const response = await fetch('https://api.blablalink.com' + config.path, {
              method: config.method, credentials: 'include', cache: 'no-store', redirect: 'error',
              headers: {'Content-Type':'application/json','Accept':'application/json, text/plain, */*',
                'X-Channel-Type':'2','X-Language':'en','X-Common-Params':JSON.stringify(config.common)},
              ...(config.method === 'POST' ? {body: JSON.stringify(config.body)} : {}),
              signal: AbortSignal.timeout(30000)
            });
            if (!response.ok) return {code: response.status, transport: 'http'};
            return await response.json();
          } catch { return {code: -1, transport: 'network'}; }
        })()""" % json.dumps({'path': path, 'method': method, 'body': body or {}, 'common': COMMON})
        result = self.client.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True,
                                 'returnByValue': True}, self.session, timeout=40)
        value = result.get('result', {}).get('value')
        if not isinstance(value, dict) or value.get('code') == -1:
            raise BrowserError('Could not read BlaBlaLink from the saved browser session. The signed-in profile has been kept.')
        return value

    def account(self):
        import account_sync
        self.phase('Opening your saved BlaBlaLink session')
        self.client.call('Page.navigate', {'url': HOME_URL}, self.session)
        # Let the site's own login restoration finish before querying its APIs.
        for attempt in range(12):
            if self.cancelled.wait(1):
                raise InterruptedError()
            result = self.client.call('Runtime.evaluate', {'expression': "['https://www.blablalink.com','https://blablalink.com'].includes(location.origin) && document.readyState !== 'loading'", 'returnByValue': True}, self.session)
            if not result.get('result', {}).get('value'):
                continue
            profile = self.request('account')
            if profile.get('code') == 0:
                break
            if profile.get('code') not in (300001, 401):
                raise account_sync.RefreshError('BlaBlaLink rejected the account lookup (code ' + str(profile.get('code')) + ').')
        else:
            raise account_sync.LoginRequired('The saved browser session was not accepted by BlaBlaLink.')
        data = profile.get('data', {})
        user = data.get('info') or data.get('user_info') or data
        identity = user.get('intl_openid', '')
        if not isinstance(identity, str) or not identity.startswith('29080-') or not identity[6:]:
            raise account_sync.RefreshError('BlaBlaLink returned an incomplete account identifier.')
        role = self.request('role')
        if role.get('code') in (300001, 401):
            raise account_sync.LoginRequired('BlaBlaLink rejected the saved game binding.')
        if role.get('code') != 0:
            raise account_sync.RefreshError('BlaBlaLink rejected the selected game lookup (code ' + str(role.get('code')) + ').')
        info = role.get('data', {}).get('role_info') or {}
        area = info.get('area_id')
        if not area:
            raise account_sync.AccountSelectionRequired('BlaBlaLink has no selected NIKKE account. Select your account under Game Binding before importing.')
        return {'openid': identity.split('-', 1)[1], 'area': int(area)}

    def mark_ready(self):
        (self.profile / 'raid-lab-imported').write_text('1', encoding='utf-8')

    def close(self):
        # This client only owns the hidden reader, never the interactive browser.
        if not self.client and self.reader_process:
            url = endpoint(self.profile)
            if url:
                self.client = DevTools(url)
        if self.client:
            try:
                self.client.call('Browser.close')
            except Exception:
                pass
            finally:
                self.client.close()
                self.client = None
        if self.reader_process:
            try:
                self.reader_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.reader_process.terminate()
            self.reader_process = None

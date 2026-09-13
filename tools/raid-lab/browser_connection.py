"""Background account import with a persistent, app-owned browser login."""
import secrets
import threading
import time
import account_sync
import browser_login
import accounts

LOCK = threading.RLock()
JOBS = {}
ACTIVE = ('running', 'needs_browser')
browsers = browser_login.browsers

def start(force_browser=False, profile_url=None):
    target = accounts.public_identity(profile_url) if profile_url else None
    with LOCK:
        for key, row in JOBS.items():
            if row['status'] in ACTIVE:
                if time.time() - row['created'] < 900:
                    if row.get('target') != target:
                        raise ValueError('An account import is already running. Finish or cancel it first.')
                    return key
                row['cancel'].set()
                row.update(status='error', error='Account connection timed out. Try Load my account again.')
        while len(JOBS) >= 8:
            JOBS.pop(next(iter(JOBS)))
        token = secrets.token_hex(16)
        available = browsers()
        saved = browser_login.preference().get('browser')
        JOBS[token] = {'status': 'needs_browser', 'phase': 'Choose a browser for BlaBlaLink sign-in',
                       'created': time.time(), 'cancel': threading.Event(), 'browser': None, 'target':target}
        if not available:
            JOBS[token].update(status='error', error='Install Chrome or Microsoft Edge to use browser login. You can still import a roster file.')
        elif not force_browser and any(b['id'] == saved for b in available):
            connect(token, saved)
        return token

def state(token):
    with LOCK:
        row = JOBS.get(token)
        if row is None:
            return None
        if row['status'] in ACTIVE and time.time() - row['created'] > 900:
            row['cancel'].set()
            row.update(status='error', error='Account connection timed out. Click Load my account to try again. Your saved roster was not changed.')
        result = {k: v for k, v in row.items() if k not in ('cancel', 'created', 'target')}
        if row['status'] == 'needs_browser':
            result['browsers'] = [{'id': b['id'], 'name': b['name']} for b in browsers()]
            result['preferred'] = browser_login.preference().get('browser')
        return result

def connect(job, browser):
    with LOCK:
        if job not in JOBS or JOBS[job]['status'] != 'needs_browser':
            raise ValueError('This refresh is no longer waiting for a browser.')
        selected = next((b for b in browsers() if b['id'] == browser), None)
        if selected is None:
            raise ValueError('Choose an available browser.')
        JOBS[job].update(status='running', browser=selected['name'], browser_id=selected['id'], phase='Connecting to your BlaBlaLink account…')
        threading.Thread(target=run, args=(job, selected), daemon=True, name='account-login').start()
        return {'browser': selected['name']}

def run(job, selected):
    login = None
    with LOCK:
        row = JOBS[job]
        cancelled = row['cancel']

    def phase(text):
        with LOCK:
            if cancelled.is_set() or row['status'] != 'running':
                raise InterruptedError()
            if time.time() - row['created'] > 900:
                raise browser_login.BrowserError('Account connection timed out. Try Load my account again.')
            row['phase'] = text
            row['awaiting_close'] = text.startswith('Finish signing in')

    try:
        login = browser_login.LoginBrowser(selected, cancelled, phase)
        browser_login.remember(selected['id'], browser_login.preference().get('area'))
        while not cancelled.is_set():
            try:
                identity = login.account()
                target = row.get('target')
                name = 'My account'
                if target:
                    phase('Reading public profile')
                    profile = login.request('player_info', {'intl_openid':'29080-' + target})
                    if profile.get('code') != 0 or not (profile.get('data') or {}).get('area_id'):
                        raise account_sync.RefreshError('The public profile is unavailable or private. No saved account was changed.')
                    info = profile['data']
                    identity = {'openid':target, 'area':int(info['area_id'])}
                    name = info.get('role_name') or info.get('nickname') or info.get('nick_name') or info.get('name') or ('Public account ' + target[-6:])
                def request(route, body, cookie):
                    if cancelled.is_set():
                        raise InterruptedError()
                    return login.request(route, body)
                snapshot, metadata = account_sync.fetch_latest('', request,
                    progress=lambda **kw: phase(kw['phase']), preferred_area=identity['area'], account_id=identity['openid'])
                phase('Saving your refreshed roster')
                with LOCK:
                    if cancelled.is_set() or row['status'] != 'running':
                        raise InterruptedError()
                    fresh = accounts.save_snapshot(snapshot, identity['openid'], metadata['area'], name, public=bool(target))
                    try:
                        if not target:
                            browser_login.remember(selected['id'], metadata['area'])
                        login.mark_ready()
                    except OSError:
                        pass
                    # Finish owning this reader before another refresh can start.
                    try:
                        login.close()
                    except Exception:
                        pass
                    login = None
                    row.update(status='done', result=fresh, refreshed_at=fresh['refreshed_at'])
                return
            except account_sync.LoginRequired as error:
                if login.just_signed_in:
                    raise account_sync.RefreshError(str(error) + ' The signed-in profile was kept; automatic sign-in retries have stopped.') from None
                phase('Your saved session needs sign-in. Opening a normal account browser once.')
                login.sign_in()
    except InterruptedError:
        pass
    except Exception as error:
        with LOCK:
            if row['status'] == 'running':
                message = str(error) if isinstance(error, (browser_login.BrowserError, account_sync.RefreshError)) else 'Could not complete browser login or import. Close the Raid Lab account window and retry.'
                row.update(status='error', error=message + ' Your saved roster was not changed.')
    finally:
        if login:
            try:
                login.close()
            except Exception:
                pass

def cancel(job):
    with LOCK:
        row = JOBS.get(job)
        if row and row['status'] in ACTIVE:
            row['cancel'].set()
            row.update(status='error', error='Account refresh cancelled. Your saved roster was not changed.')

def finish_signin(job):
    with LOCK:
        row = JOBS.get(job)
        if not row or row['status'] != 'running' or not row.get('awaiting_close'):
            raise ValueError('The importer is not waiting for sign-in.')
        selected = next((item for item in browsers() if item['id'] == row.get('browser_id')), None)
        if not selected:
            raise ValueError('The account browser is no longer available.')
    browser_login.finish_signin(selected)
    return {'ok': True}

"""Independent, atomic account snapshots. No roster or investment merging."""
import base64
import hashlib
import json
import re
import secrets
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import account_sync
import core

ROOT = Path(__file__).resolve().parent / 'private'
LOCK = threading.RLock()

def public_identity(url):
    try:
        parsed = urlsplit(str(url).strip())
        if parsed.scheme != 'https' or parsed.hostname not in ('www.blablalink.com', 'blablalink.com') or parsed.port or parsed.username or parsed.password:
            raise ValueError()
        query = parse_qs(parsed.query)
        token = (query.get('openid') or query.get('uid') or [''])[0]
        decoded = base64.b64decode(token, validate=True).decode('ascii')
        if not re.fullmatch(r'29080-\d{1,30}', decoded):
            raise ValueError()
        return decoded.split('-', 1)[1]
    except (ValueError, UnicodeError):
        raise ValueError('Paste a public https://www.blablalink.com/user?openid=… profile link.') from None

def account_key(identity, area):
    return 'blabla-' + hashlib.sha256(f'{identity}:{area}'.encode()).hexdigest()[:24]

def account_dir(key):
    if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', key):
        raise ValueError('Invalid account selection.')
    return ROOT / 'accounts' / key

def read(key):
    path = account_dir(key) / 'roster.json'
    if not path.exists():
        raise ValueError('That saved account was not found.')
    return core.read(path)

def save(fresh, key=None, name=None, kind='file', identity=None):
    with LOCK:
        key = key or 'import-' + secrets.token_hex(12)
        path = account_dir(key) / 'roster.json'
        old = core.read(path) if path.exists() else {}
        record = dict(fresh)
        record.update(account_id=key, account_name=str(name or old.get('account_name') or 'Imported account')[:100],
                      account_kind=old.get('account_kind', kind),
                      updated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
        if identity or old.get('identity'):
            record['identity'] = identity or old['identity']
        account_sync.atomic_json(path, record)
        return record

def migrate():
    with LOCK:
        marker = ROOT / 'accounts-migrated.json'
        if marker.exists():
            return
        legacy = ROOT / 'roster.json'
        if legacy.exists() and not (account_dir('my-account') / 'roster.json').exists():
            save(core.read(legacy), 'my-account', 'My account', 'own')
        if legacy.exists():
            destination = account_dir('my-account')
            database = ROOT / 'recommendation-history.sqlite3'
            if database.exists() and not (destination / database.name).exists():
                with sqlite3.connect(database) as src, sqlite3.connect(destination / database.name) as dst:
                    src.backup(dst)
            report = ROOT / 'report.json'
            if report.exists() and not (destination / report.name).exists():
                shutil.copy2(report, destination / report.name)
        account_sync.atomic_json(marker, {'done': True})


def delete(key):
    with LOCK:
        migrate()
        read(key)
        parent = (ROOT / 'accounts').resolve()
        target = account_dir(key).resolve()
        if target.parent != parent:
            raise ValueError('Invalid account directory.')
        shutil.rmtree(target)
        if key == 'my-account':
            for name in ('roster.json', 'report.json', 'recommendation-history.sqlite3',
                         'recommendation-history.sqlite3-wal', 'recommendation-history.sqlite3-shm',
                         'recommendation-history.sqlite3-journal'):
                path = ROOT / name
                if path.resolve().parent != ROOT.resolve():
                    raise ValueError('Invalid legacy cache path.')
                path.unlink(missing_ok=True)

def listing():
    migrate()
    records = [core.read(p) for p in (ROOT / 'accounts').glob('*/roster.json')]
    return [{'id':r['account_id'], 'name':r['account_name'], 'kind':r.get('account_kind'),
             'count':len(r.get('roster', [])), 'updated_at':r.get('updated_at')}
            for r in sorted(records, key=lambda r:(r['account_id'] != 'my-account', r['account_name'].casefold()))]

def import_file(data, name=None):
    fresh = core.import_roster(data)
    info = data if isinstance(data, dict) else {}
    key = info.get('account_id')
    # An export retains its identity; a legacy file gets its own snapshot.
    if not key:
        key = 'import-' + hashlib.sha256(json.dumps(fresh['roster'], sort_keys=True).encode()).hexdigest()[:24]
    fresh['source'] = str(info.get('source') or fresh['source'])[:250]
    return save(fresh, key, info.get('account_name') or name, 'file')

def save_snapshot(snapshot, identity, area, name, public=False):
    fresh = core.import_roster(snapshot)
    fresh['refreshed_at'] = snapshot['captured_at']
    fresh['source'] = f'{name} · BlaBlaLink · {snapshot["captured_at"]}'
    marker = account_key(identity, area)
    key = marker
    with LOCK:
        migrate()
        if not public:
            try:
                legacy = read('my-account')
                if not legacy.get('identity') or legacy.get('identity') == marker:
                    key = 'my-account'
            except ValueError:
                key = 'my-account'
        record = save(fresh, key, name, 'public' if public else 'own', marker)
        account_sync.atomic_json(account_dir(key) / 'snapshot.json', snapshot)
        return record

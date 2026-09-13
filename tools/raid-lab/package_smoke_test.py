"""Validate an extracted portable package without opening a browser."""
import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def fetch(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def start_server(python, app, port):
    # Refuse to talk to another already-running app on the smoke port.
    with socket.socket() as probe:
        probe.settimeout(.5)
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError('The portable smoke port is already in use.')
    return subprocess.Popen(
        [python, app / 'server.py', '--port', str(port)], cwd=app,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )


def ready(process, base):
    for _ in range(40):
        if process.poll() is not None:
            raise RuntimeError(process.stderr.read())
        try:
            return fetch(base + '/api/health')
        except OSError:
            time.sleep(.25)
    raise RuntimeError('Portable server did not become ready.')


def stop_server(process):
    if process.poll() is not None:
        # An unexpected parent exit prevents proving that its workers have exited.
        # Leave the database intact in this failure case rather than delete it live.
        raise RuntimeError('Portable server exited unexpectedly; smoke history was preserved.')
    stopped = subprocess.run(
        ['taskkill', '/PID', str(process.pid), '/T', '/F'],
        capture_output=True, text=True, timeout=15,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    if stopped.returncode:
        raise RuntimeError('Could not stop the portable server process tree; smoke history was preserved.')
    process.wait(timeout=5)
    process.stderr.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    parser.add_argument('--port', type=int, default=8877)
    args = parser.parse_args()
    package = args.package.resolve()
    python = package / 'runtime' / 'python.exe'
    app = package / 'tools' / 'raid-lab'
    private = (app / 'private').resolve()
    if not private.is_relative_to(app.resolve()):
        raise RuntimeError('Portable private storage resolves outside the app directory.')
    database = private / 'recommendation-history.sqlite3'
    history_files = [Path(str(database) + suffix) for suffix in ('', '-journal', '-wal', '-shm')]
    if any(path.exists() for path in history_files) or (private / 'report.json').exists():
        raise RuntimeError('Smoke test requires a fresh portable package without recommendation history or a saved report.')
    process = None
    cleanup_allowed = True
    try:
        base = f'http://127.0.0.1:{args.port}'
        process = start_server(python, app, args.port)
        health = ready(process, base)
        catalog = fetch(base + '/api/catalog')
        compute = fetch(base + '/api/compute')
        by_name = {row['name']: row['id'] for row in catalog['catalog']}
        team_names = ['Liter', 'Crown', 'Naga', 'Alice', 'Modernia']
        job = fetch(base + '/api/manual', {
            'roster': catalog['demo'],
            'members': [by_name[name] for name in team_names],
            'settings': {'content_mode': 'practice', 'duration': 30, 'compute_mode': 'single'},
        })['id']
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            result = fetch(base + '/api/jobs/' + job)
            if result['status'] != 'running':
                break
            time.sleep(.25)
        if result['status'] != 'done' or result['result']['total'] <= 0:
            raise RuntimeError('Portable simulation failed: ' + repr(result))
        recommendation = result['result']
        history = recommendation.get('history')
        if not history or recommendation.get('history_error'):
            raise RuntimeError('Portable recommendation was not saved to history.')
        index = fetch(base + '/api/history')
        if index['runs'] or not any(mode['id'] == 'practice' for mode in index['modes']):
            raise RuntimeError('Portable history did not expose mode-first navigation.')
        page = fetch(base + '/api/history?mode=practice&boss=training')
        if page['total'] != 1 or len(page['runs']) != 1 or page['runs'][0]['id'] != history['id']:
            raise RuntimeError('Portable history did not retain one grouped run.')
        summary = page['runs'][0]
        if len(summary['teams']) != 1 or summary['total'] != recommendation['total']:
            raise RuntimeError('Portable history changed the squad grouping or total damage.')
        if [member['id'] for member in summary['teams'][0]['members']] != recommendation['teams'][0]['members']:
            raise RuntimeError('Portable history changed squad slot order.')
        expected = {key: value for key, value in recommendation.items() if key != 'history'}
        snapshot = fetch(base + '/api/history/' + history['id'])
        if snapshot['report'] != expected or snapshot['summary'] != summary or snapshot['kind'] != 'manual':
            raise RuntimeError('Portable history changed the saved report snapshot.')
        stop_server(process)
        process = None
        process = start_server(python, app, args.port)
        ready(process, base)
        if fetch(base + '/api/history/' + history['id']) != snapshot:
            raise RuntimeError('Portable history did not survive a server restart.')
        if fetch(base + '/api/history?mode=practice&boss=training')['total'] != 1:
            raise RuntimeError('Portable server restart duplicated the history record.')
        print(json.dumps({'health': health['app'], 'version': health['version'],
                          'catalog': len(catalog['catalog']), 'demo': len(catalog['demo']),
                          'gpu_available': compute['gpu']['available'],
                          'manual_damage': recommendation['total'], 'history_persisted_after_restart': True}))
    finally:
        try:
            if process is not None:
                stop_server(process)
        except BaseException:
            cleanup_allowed = False
            raise
        finally:
            if cleanup_allowed:
                # These exact files were absent before this smoke. No recursive
                # deletion and no cleanup until all server workers are stopped.
                for path in history_files:
                    if path.resolve().parent != private:
                        raise RuntimeError('History cleanup path left the portable private directory.')
                    path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

"""One real loopback request through the app to its original native broker."""
from pathlib import Path
import hashlib
import json
import multiprocessing
import sys
import threading
import time
import urllib.request

APP = Path('I:/Raid Lab/tools/raid-lab')
OUT = Path(__file__).resolve().parents[1] / 'results/native-service-http1'
sys.path.insert(0, str(APP))


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    if sys.argv[1:] != ['--run']:
        raise ValueError('Explicit --run required')
    import server
    server.PORT = 18766
    OUT.mkdir(exist_ok=False)
    payload = {'engine': 'original153', 'fixtureId': 'captured-fire90-run1',
        'inputSourceSha256': '9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7',
        'releaseId': 'native153-fire90-run1-v20-20261101'}
    save('request.json', payload)
    save('source-pins.json', {name: hashlib.sha256((APP / name).read_bytes()).hexdigest()
        for name in ('server.py', 'native_practice.py')})
    httpd = server.ThreadingHTTPServer(('127.0.0.1', server.PORT), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:18766'
    try:
        request = urllib.request.Request(base + '/api/native/practice',
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=30) as response:
            accepted = {'httpStatus': response.status, 'body': json.load(response)}
        save('accepted.json', accepted)
        print(json.dumps(accepted), flush=True)
        token = accepted['body']['id']
        last_phase = None
        started = time.monotonic()
        while True:
            with urllib.request.urlopen(base + '/api/jobs/' + token, timeout=15) as response:
                state = json.load(response)
            phase = (state.get('status'), state.get('phase'))
            if phase != last_phase:
                print(json.dumps({'status': phase[0], 'phase': phase[1]}), flush=True)
                last_phase = phase
            if state.get('status') != 'running':
                save('terminal.json', state)
                break
            if time.monotonic() - started > 150:
                raise TimeoutError('HTTP observation exceeded150s; native worker must close before harness exits')
            time.sleep(.5)
        worker = server.JOBS[token]['process']
        worker.join()
        save('completion.json', {'httpJobId': token, 'workerExitCode': worker.exitcode,
            'status': state.get('status'), 'elapsedSeconds': time.monotonic() - started,
            'freshNativeJobRequired': True, 'pythonCombatFallback': False})
        if state.get('status') != 'done' or worker.exitcode != 0:
            raise RuntimeError(json.dumps(state))
        print(json.dumps({'status': 'passed', 'jobId': token, 'result': state['result']}), flush=True)
    except BaseException as error:
        save('error.json', {'type': type(error).__name__, 'error': str(error)})
        raise
    finally:
        # Never kill the original player or abandon the app's owned worker.
        for job in server.JOBS.values():
            job['process'].join()
        httpd.shutdown()
        httpd.server_close()
        thread.join()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()

"""Loopback-only app. One simulation worker avoids upstream global-state races."""
import json
import multiprocessing as mp
import queue
import secrets
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import core
import browser_connection
import report_history

ROOT=Path(__file__).resolve().parent
JOBS={}
LOCK=threading.Lock()
PORT=8766

def history_store():
    return report_history.ReportHistory(ROOT/'private', core.CAT)

def worker(payload,kind,events,cancel):
    try:
        result=core.manual(payload) if kind=='manual' else core.search(payload,lambda **kw:events.put({'status':'running',**kw}),cancel.is_set)
        try:
            result['history']=history_store().save(result,kind)
        except Exception:
            # The computed result remains usable even if private storage is full,
            # read-only or unavailable. This must never turn a successful run into an error.
            result['history_error']='This recommendation could not be saved to history. Export the report to keep a copy.'
        events.put({'status':'done','result':result})
    except InterruptedError as error:events.put({'status':'cancelled','message':str(error)})
    except BaseException as e:events.put({'status':'error','error':str(e) or type(e).__name__})

def collect(job):
    while True:
        try:job['state'].update(job['queue'].get_nowait())
        except queue.Empty:break
    if job['state']['status']=='running' and not job['process'].is_alive():
        time.sleep(.03)
        try:job['state'].update(job['queue'].get_nowait())
        except queue.Empty:job['state'].update(status='error',error='Simulation worker exited before returning a result.')
    return job['state']

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'web'),**kw)
    def log_message(self,*a):pass
    def send_json(self,data,status=200):
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def allowed(self):
        host=self.headers.get('Host','')
        origin=self.headers.get('Origin')
        return host in (f'127.0.0.1:{PORT}',f'localhost:{PORT}') and (not origin or origin in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'))
    def do_GET(self):
        if not self.allowed():return self.send_json({'error':'Local access only.'},403)
        path=urlsplit(self.path).path
        if path=='/api/history' or path.startswith('/api/history/'):
            try:
                if path=='/api/history':
                    params=parse_qs(urlsplit(self.path).query,keep_blank_values=True)
                    if set(params)-{'mode','boss','offset','limit'} or any(len(values)!=1 for values in params.values()):
                        raise ValueError('Invalid history query.')
                    return self.send_json(history_store().list(**{key:values[0] for key,values in params.items()}))
                result=history_store().get(path[len('/api/history/'):])
                return self.send_json(result or {'error':'Recommendation not found.'},200 if result else 404)
            except ValueError as error:return self.send_json({'error':str(error)},400)
            except Exception:return self.send_json({'error':'Recommendation history is unavailable. Try again after checking local storage.'},503)
        if path=='/api/catalog':
            cubes=core.read(core.ENGINE/'data/base_stat_tables/cube.json')
            return self.send_json({'model_revision':core.encounters.MODEL_REVISION,'modes':core.encounters.MODES,'bosses':core.encounters.BOSSES,'catalog':core.CATALOG,'default_build':core.default_build(),'demo':core.demo_roster(),'cubes':[k for k in cubes if not k.startswith('_') and k!='공통']})
        if path=='/api/compute':
            from gpu_search import device_info
            from parallel_compute import worker_count, available_cpus, worker_limit
            return self.send_json({'cpu_workers':worker_count(),'cpu_available':available_cpus(),'cpu_worker_limit':worker_limit(),'gpu':device_info()})
        if path=='/api/health':return self.send_json({'app':'Raid Lab','version':1})
        if path=='/api/local-roster':
            seed=ROOT/'private'/'roster.json'
            saved=core.read(seed) if seed.exists() else {'roster':[]}
            report=ROOT/'private'/'report.json'
            if report.exists():saved['report']=core.read(report)
            return self.send_json(saved)
        if path.startswith('/api/account-refresh/'):
            result=browser_connection.state(path.rsplit('/',1)[1])
            return self.send_json(result or {'error':'Refresh not found.'},200 if result else 404)
        if path.startswith('/api/jobs/'):
            with LOCK:
                job=JOBS.get(path.rsplit('/',1)[1])
                if not job:return self.send_json({'error':'Job not found.'},404)
                return self.send_json(collect(job))
        if path.startswith('/api/'):return self.send_json({'error':'Not found.'},404)
        super().do_GET()
    def do_POST(self):
        if not self.allowed():return self.send_json({'error':'Local access only.'},403)
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send_json({'error':'JSON required.'},415)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4_000_000:raise ValueError('JSON must be between 1 byte and 4 MB.')
            body=json.loads(self.rfile.read(length))
            if self.path=='/api/account-refresh':
                return self.send_json({'id':browser_connection.start(body.get('choose_browser',False))},202)
            if self.path=='/api/account-connect':return self.send_json(browser_connection.connect(body['job'],body['browser']))
            if self.path=='/api/account-finish-signin':return self.send_json(browser_connection.finish_signin(body['job']))
            if self.path=='/api/account-cancel':
                browser_connection.cancel(body['job']);return self.send_json({'ok':True})
            if self.path=='/api/import':return self.send_json(core.import_roster(body))
            if self.path in ('/api/search','/api/manual'):
                core.validate_settings(body.get('settings',{}));core.import_roster({'roster':body.get('roster',[])})
                with LOCK:
                    for job in JOBS.values():
                        if collect(job)['status']=='running':return self.send_json({'error':'A simulation is already running. Cancel it or wait for completion.'},409)
                    # Limit memory retained by old reports.
                    while len(JOBS)>=8:JOBS.pop(next(iter(JOBS)))
                    token=secrets.token_hex(12);events=mp.Queue();cancel=mp.Event()
                    p=mp.Process(target=worker,args=(body,'manual' if self.path.endswith('manual') else 'search',events,cancel),daemon=False)
                    p.start();JOBS[token]={'process':p,'queue':events,'cancel':cancel,'state':{'status':'running','phase':'Preparing roster','simulations':0}}
                return self.send_json({'id':token},202)
            if self.path.startswith('/api/cancel/'):
                with LOCK:
                    job=JOBS.get(self.path.rsplit('/',1)[1])
                    if job:
                        job['cancel'].set()
                        job['state'].update(phase='Stopping workers and keeping completed recommendations…')
                return self.send_json({'status':'cancelling'})
            return self.send_json({'error':'Not found.'},404)
        except (ValueError,TypeError,KeyError,AttributeError) as e:return self.send_json({'error':str(e)},400)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766)
    PORT=parser.parse_args().port
    mp.freeze_support()
    print(f'Raid Lab ready: http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()

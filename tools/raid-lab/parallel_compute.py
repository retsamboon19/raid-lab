"""Isolated CPU workers keep the stateful combat engine deterministic."""
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

def available_cpus():
    return max(1,getattr(os,'process_cpu_count',os.cpu_count)() or 1)

def worker_limit():
    return min(available_cpus(),61) if os.name=='nt' else available_cpus()

def worker_count(mode='auto',requested=0):
    available=available_cpus()
    if mode=='single':return 1
    if requested:return max(1,min(int(requested),worker_limit()))
    return min(worker_limit(),max(1,available//2))

def _initialize(roster, settings, stop):
    global _ROSTER, _SETTINGS, _STOP
    _ROSTER, _SETTINGS, _STOP = roster, settings, stop

def _evaluate(key):
    if _STOP.is_set():raise InterruptedError('Search cancelled.')
    from core import evaluate_candidate
    return evaluate_candidate(*key[:3],_ROSTER,dict(_SETTINGS,_aim_controller=key[3]) if len(key)>3 else _SETTINGS)

class CandidateExecutor:
    def __init__(self,mode='auto',requested=0):
        self.workers=worker_count(mode,requested)
        self.pool=None
        self.stop=None
        self.deadline=float('inf')

    def terminate(self):
        if self.pool is None:return
        self.stop.set()
        if hasattr(self.pool,'terminate_workers'):self.pool.terminate_workers()
        else:
            for process in list(self.pool._processes.values()):process.terminate()
            self.pool.shutdown(wait=True,cancel_futures=True)
        self.pool=None

    def fill(self, keys, roster, settings, cache, failures, completed, cancelled):
        if cancelled():raise InterruptedError('Search cancelled.')
        keys=list(dict.fromkeys(k for k in keys if k not in cache and k not in failures))
        if not keys or time.perf_counter()>=self.deadline:return
        critical=settings.get('require_critical_parts',False)
        work=[];choices={};collected={};errors={}
        for key in keys:
            if not critical:work.append(key);continue
            team,duration,detail=key
            controllers=list(team)
            # Opening samples compare all five. Full fights spend their budget
            # on the best two observed aim choices, instead of repeating all five.
            samples=[r for k,r in cache.items() if k[0]==team and not k[2] and k[1]<=duration and r.get('control_comparison')]
            if detail and samples:
                sample=max(samples,key=lambda r:r.get('duration',0))
                controllers=[c['unit'] for c in sorted(sample['control_comparison'],key=lambda c:c['deadline_score'],reverse=True)[:2]]
            choices[key]=controllers;collected[key]={};errors[key]=[]
            work.extend((*key,n) for n in controllers)
        if critical:work.sort(key=lambda k:choices[k[:3]].index(k[3]))
        if self.pool is None:
            context=mp.get_context('spawn');self.stop=context.Event()
            self.pool=ProcessPoolExecutor(max_workers=self.workers,mp_context=context,
                initializer=_initialize,initargs=(roster,settings,self.stop))
        pending=iter(work);futures={}
        def submit():
            while len(futures)<self.workers and time.perf_counter()<self.deadline:
                key=next(pending,None)
                if key is None:break
                futures[self.pool.submit(_evaluate,key)]=key
        def retain(done):
            for future in done:
                key=futures.pop(future)
                if future.cancelled():continue
                base=key[:3] if critical else key
                try:
                    row=future.result()
                    if critical:
                        from critical_parts import assessment,screen_score
                        collected[base][key[3]]=row
                        rows=list(collected[base].values())
                        rank=(lambda r:(assessment(r)['passed'],r['damage'])) if base[2] else screen_score
                        best=dict(max(rows,key=rank))
                        best['control_comparison']=[dict(unit=n,damage=r['damage'],parts_passed=assessment(r)['passed'],deadline_score=screen_score(r)) for n,r in collected[base].items()]
                        best['critical_part_requirement']=assessment(best)
                        best['control_search_complete']=len(rows)+len(errors[base])==len(choices[base])
                        cache[base]=best
                    else:cache[base]=row
                except (ValueError,KeyError,IndexError,TypeError) as error:
                    if critical:
                        errors[base].append(error)
                        if len(errors[base])==len(choices[base]):failures[base]=error
                        elif base in cache:cache[base]['control_search_complete']=len(collected[base])+len(errors[base])==len(choices[base])
                    else:failures[base]=error
                completed()
        submit()
        try:
            while futures:
                # Keep already completed simulations before honouring stop.
                retain([f for f in futures if f.done()])
                if cancelled():
                    self.terminate();raise InterruptedError('Search cancelled.')
                if time.perf_counter()>=self.deadline:
                    self.terminate();return
                if not futures:
                    submit()
                    if not futures:break
                done,_=wait(futures,timeout=.1,return_when=FIRST_COMPLETED)
                retain(done);submit()
        except BaseException:
            self.terminate()
            raise

    def close(self):
        if self.pool is not None:
            self.stop.set()
            self.pool.shutdown(wait=True,cancel_futures=True)
            self.pool=None

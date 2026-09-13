"""Check every catalog kit at levels 1/10 and all Favorite Item stages.

Uses synthetic builds; writes only a local validation report under private/.
Run from the app directory with python validate_roster.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json, time, math
from concurrent.futures import ProcessPoolExecutor, as_completed
import core
from calculator.buff_manager import char_effects

def run(case):
    name, level, favorite = case
    stage = str(core.META[name]['burst_stage'])
    mates = {'1': [name, 'test_B2', 'test_B3'], '2': ['test_B1', name, 'test_B3']}.get(stage, ['test_B1', 'test_B2', name])
    extras = [n for n in ('리타', '크라운', '나가', '홍련') if n not in mates][:2]
    build = core.default_build()
    build['skill_levels'] = dict.fromkeys(('1','2','3'), level)
    chars = [core.spec.build_char(n, dict(build, favorite_stage=favorite if n == name else 0), no_layer=True) for n in mates+extras]
    result = core.simulate(chars, config={'duration':45, 'first_burst_time':1, 'rng_mode':'expected'}, seed=42)
    total = sum(result.char_total.values())
    assert math.isfinite(total) and total>0
    return {'name':core.CAT[name]['name'],'level':level,'favorite':favorite,'damage':total,'effects':len(char_effects(name,favorite))}

if __name__ == '__main__':
    (Path(__file__).resolve().parent / 'private').mkdir(exist_ok=True)
    started=time.time()
    cases=[(c['id'],lv,fav) for c in core.CATALOG for fav in (range(4) if core.META[c['id']].get('favorite_slots') else [0]) for lv in [1,10]]
    done=[];errors=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(run,c):c for c in cases}
        for f in as_completed(futures):
            try:done.append(f.result())
            except Exception as exc:errors.append({'case':futures[f],'error':repr(exc)})
            if (len(done)+len(errors))%40==0:print(len(done),'passed',len(errors),'failed',flush=True)
    result={'cases':len(cases),'passed':len(done),'errors':errors,'seconds':round(time.time()-started,2),'results':done}
    (Path(__file__).resolve().parent / 'private' / 'all-kit-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('DONE',len(done),len(errors),flush=True)
    sys.exit(bool(errors))

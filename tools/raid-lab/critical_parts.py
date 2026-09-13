"""Deadline evidence and pass-first allocation, independent of DPS heuristics."""
import time


def assessment(entry):
    fight=entry.get('encounter_timeline') or {}
    checks=fight.get('critical_deadlines',fight.get('critical_parts',[]))
    missed=[p for p in checks if p.get('status')=='failed']
    pending=[p for p in checks if p.get('status') not in ('passed','failed','not_required')]
    complete=fight.get('simulated_until',0)>=entry.get('duration',float('inf'))-.1
    passed=bool(fight.get('critical_deadlines_supported') or checks) and complete and not missed and not pending
    return dict(passed=passed,missed=len(missed),pending=len(pending),checks=checks,complete=complete)


class Deadlines:
    """Retain part instances, so a later respawn cannot erase an earlier miss."""
    def __init__(self):self.rows=[];self.at_deadline={}
    def register(self,parts,names,deadline,shot):
        targets=[(n,parts.parts[n]) for n in names if n in parts.parts]
        if targets:self.rows.append((targets,deadline,shot))
    def advance(self,time):
        for index,(targets,deadline,_) in enumerate(self.rows):
            if time>=deadline and index not in self.at_deadline:
                self.at_deadline[index]=sum(p['hp'] for _,p in targets)
    def report(self,time):
        out=[]
        for index,(targets,deadline,shot) in enumerate(self.rows):
            broken=[p['destroyed_at'] for _,p in targets if p.get('destroyed_at') is not None]
            destroyed=min(broken) if broken else None
            out.append(dict(id='deadline-'+str(index),part=' / '.join(n for n,_ in targets),shot=shot,
                hp=sum(p['max_hp'] for _,p in targets),remaining_hp=sum(p['hp'] for _,p in targets),
                deadline=round(deadline,3),destroyed_at=destroyed,remaining_hp_at_deadline=self.at_deadline.get(index),
                status='passed' if destroyed is not None and destroyed<=deadline+1e-9 else 'failed' if time>=deadline else 'pending'))
        return out


def best_allocation(rows,count,cancelled=lambda:False):
    """Exact disjoint selection within the evaluated pool; passes dominate damage."""
    by_members={}
    for row in rows:
        key=frozenset(row['members'])
        score=(assessment(row)['passed'],row['damage'])
        if key not in by_members or score>(assessment(by_members[key])['passed'],by_members[key]['damage']):by_members[key]=row
    candidates=sorted(by_members.values(),key=lambda r:(assessment(r)['passed'],r['damage']),reverse=True)
    scored=[(r,frozenset(r['members']),int(assessment(r)['passed'])) for r in candidates]
    best=None;best_score=(-1,-1);visits=0
    def visit(start,chosen,used,passes,damage):
        nonlocal best,best_score,visits
        visits+=1
        if visits%256==0 and cancelled():raise InterruptedError('Search cancelled.')
        left=count-len(chosen)
        if not left:
            if (passes,damage)>best_score:best_score=(passes,damage);best=list(chosen)
            return
        available=[(i,r,ids,p) for i,(r,ids,p) in enumerate(scored[start:],start) if not ids&used]
        if len(available)<left:return
        bound=passes+sum(p for _,_,_,p in available[:left])
        if bound<best_score[0]:return
        if bound==best_score[0] and damage+sum(sorted((r['damage'] for _,r,_,_ in available),reverse=True)[:left])<=best_score[1]:return
        for i,r,ids,p in available:visit(i+1,chosen+[r],used|ids,passes+p,damage+r['damage'])
    if cancelled():raise InterruptedError('Search cancelled.')
    visit(0,[],set(),0,0)
    return best


def screen_score(row):
    """Observed part damage at its deadline, never late damage or squad DPS."""
    a=assessment(row);ratios=[];observed=0
    for p in a['checks']:
        if p.get('status')=='passed':ratios.append(1.);observed+=1;continue
        remaining=p.get('remaining_hp_at_deadline')
        if remaining is not None and p.get('hp',0)>0:
            ratios.append(max(0.,min(1.,1-remaining/p['hp'])));observed+=1
    return (int(a['passed']), min(ratios,default=0.), sum(ratios)/max(1,len(ratios)), observed, row['damage'])


def select_tested(rows,count,required=False,seeds=(),width=64):
    """Bounded allocation beam; completed seed plans are always retained."""
    by_members={}
    def rank(r):return (int(required and assessment(r)['passed']),r['damage'])
    for r in rows:
        key=frozenset(r['members'])
        if key not in by_members or rank(r)>rank(by_members[key]):by_members[key]=r
    candidates=sorted(by_members.values(),key=rank,reverse=True)
    def score(group):return (len(group),sum(rank(r)[0] for r in group),sum(r['damage'] for r in group))
    best=[]
    for seed in seeds:
        used=set();group=[]
        for r in seed:
            if used.isdisjoint(r['members']):group.append(r);used.update(r['members'])
        if len(group)<=count and score(group)>score(best):best=group
    # Greedy starts preserve alternatives with a different allocation of supports.
    beam=[([],frozenset(),0,0)]
    for _ in range(count):
        expanded={}
        for group,used,passes,damage in beam:
            taken=0
            for r in candidates:
                members=frozenset(r['members'])
                if used&members:continue
                next_used=used|members;item=(group+[r],next_used,passes+rank(r)[0],damage+r['damage'])
                if next_used not in expanded or item[2:]>expanded[next_used][2:]:expanded[next_used]=item
                taken+=1
                if taken>=width:break
        if not expanded:break
        beam=sorted(expanded.values(),key=lambda item:item[2:],reverse=True)[:width]
        if score(beam[0][0])>score(best):best=beam[0][0]
    return best


def selection_report(rows,count,reason='completed'):
    passes=sum(assessment(r)['passed'] for r in rows)
    return dict(enabled=True,passed_teams=passes,total_teams=count,fallback=passes<count,exhausted=False,
        scope='Deadline-focused screening and full-fight verification within the selected search time limit.',
        message=(f'All {count} squads meet the modeled critical-part deadlines.' if passes==count else
                 f'{passes}/{count} requested squads meet the modeled part deadlines. This is the best tested allocation so far; untested teams may still pass.'))


def refine(results,proposals,orders,prefetch,run,duration,deadline,cancelled):
    """Learn from deadline margins; test nearby damage/support/rotation repairs."""
    audit=[]
    stop=lambda:time.perf_counter()>=deadline
    for iteration in range(3):
        changed=False
        for index in sorted(range(len(results)),key=lambda i:screen_score(results[i])):
            if cancelled():raise InterruptedError('Search cancelled.')
            if stop():return audit
            baseline=results[index]
            # Later checks need a longer opening sample; full fights remain the
            # only way to establish all required deadlines and repeated parts.
            deadlines=[p['deadline'] for p in assessment(baseline)['checks'] if p.get('deadline') is not None]
            sample=min(duration,max(30,min(deadlines,default=28)+2))
            candidates=[]
            for team in proposals(index,results,iteration):
                candidates.extend(orders(team)[:2])
            candidates=list(dict.fromkeys(tuple(t) for t in candidates))[:24]
            prefetch(candidates,sample,phase='Screening damage before critical-part deadlines')
            screened=[]
            for t in candidates:
                try:screened.append(run(t,sample))
                except (ValueError,KeyError,IndexError,TypeError):continue
            # Near-miss lineups and a damage leader each get full verification.
            leaders=sorted(screened,key=screen_score,reverse=True)[:2]
            if screened:leaders.append(max(screened,key=lambda r:r['damage']))
            finalists=list(dict.fromkeys(tuple(r['members']) for r in leaders))
            if stop():return audit
            prefetch(finalists,duration,True,phase='Verifying promising part-break teams through the full fight')
            best=baseline
            for t in finalists:
                try:alternative=run(t,duration,True)
                except (ValueError,KeyError,IndexError,TypeError):continue
                audit.append(dict(members=list(t),passed=assessment(alternative)['passed'],deadline_score=screen_score(alternative),damage=alternative['damage']))
                if screen_score(alternative)>screen_score(best):best=alternative
            if best is not baseline:results[index]=best;changed=True
        if not changed:break
    return audit

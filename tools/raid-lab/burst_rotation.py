"""Observe real burst timing; never infer rotation coverage from a CDR tag."""
import re


def report(team, catalog, events, duration, switch_delay=.1, *, observed_until=None):
    until=duration if observed_until is None else min(duration,max(0.,observed_until))
    windows=[]; waits=[]; opened=None; stage=None; previous={}; caster=None
    for e in events:
        t=float(e.t)
        if t>until+1e-9:continue
        if '→ 1단계 진입' in e.event:
            opened=t; stage='1'
        match=re.match(r'(stage|reenter):(\d) 사용',e.event)
        if match:
            current=match[2]
            if current==stage and opened is not None:
                delay=max(0,t-opened)
                # A standard 20-second support may naturally still be cooling
                # down after a short Full Burst. Only the additional delay is
                # treated as missing long-cooldown coverage.
                allowance=max(0,previous.get(current,-100)+20-opened)
                waits.append(dict(stage=current,unit=e.caster,ready_time=round(opened,2),
                    cast_time=round(t,2),delay=round(delay,2),
                    excess=round(max(0,delay-allowance),2)))
            previous[current]=t
            stage=str(int(current)+1); opened=t+switch_delay
            if current=='3':caster=e.caster
        if e.event=='full_burst 시작':
            windows.append(dict(start=round(t,2),end=None,seconds=None,unit=caster,complete=False))
            opened=None;stage=None
        elif e.event=='full_burst 종료' and windows:
            windows[-1].update(end=round(t,2),seconds=round(t-windows[-1]['start'],2),complete=True)
    if windows and not windows[-1]['complete']:
        windows[-1].update(end=until,seconds=round(max(0,until-windows[-1]['start']),2))
    stages=[]
    for s in ('1','2'):
        members=[n for n in team if catalog[n]['burst']==s]
        long_only=bool(members) and all(catalog[n]['cooldown']>20 for n in members)
        observed=[w for w in waits if w['stage']==s]
        excessive=[w for w in observed if w['excess']>1]
        failed=long_only and bool(excessive)
        stages.append(dict(stage=s,members=members,cooldowns=[catalog[n]['cooldown'] for n in members],
            status='uncovered long cooldown' if failed else 'observed' if len(observed)>1 else 'not enough cycles',
            largest_delay=max((w['delay'] for w in observed),default=0),
            excess_delay=sum(w['excess'] for w in observed),casts=len(observed)))
    starts=[w['start'] for w in windows]
    return dict(full_bursts=windows,full_burst_seconds=round(sum(w['seconds'] for w in windows),2),
        uptime_pct=round(100*sum(w['seconds'] for w in windows)/duration,1),
        intervals=[round(b-a,2) for a,b in zip(starts,starts[1:])],support_stages=stages,stage_delays=waits,
        covered=not any(s['status']=='uncovered long cooldown' for s in stages),
        policy='Long-cooldown B1/B2 coverage uses observed stage delays beyond a standard 20-second support cadence (1-second tolerance). Actual Full Burst length, gauge generation and activated CDR are already included. Short samples cannot establish sustained coverage; delays can also include control or incapacitation.')


def warnings(rotation):
    return [f"Burst {s['stage']} has uncovered long cooldowns: {s['largest_delay']:.1f}s stage delay. Add another unit for this stage or enough activated cooldown reduction."
            for s in rotation['support_stages'] if s['status']=='uncovered long cooldown']

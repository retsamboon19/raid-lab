"""Compare EX reward progress; preserve damage ranking for other modes."""


def score(row):
    fight=row.get('encounter_timeline') or {}
    if not fight.get('special_interception'):return row['damage']
    maximum=max(1,fight['max_reward_damage'])
    progress=min(maximum,max(0,fight.get('boss_hp_damage',row['damage'])))
    if not fight.get('target_reached'):return min(progress,maximum-1)
    # A completed reward target always wins. Among clears, prefer fewer failed
    # checks, then more remaining HP, then a faster finish. Post-clear overkill
    # cannot inflate the result and part-break progress is counted consistently.
    failures=sum(c['status']=='failed' for c in fight.get('checks',[]))
    safety=min(1,max(0,fight.get('minimum_hp_pct',0)/100))
    speed=1-min(1,fight.get('simulated_until',180)/max(1,row.get('duration',180)))
    return maximum+1+100000/(1+failures)+100*safety+speed

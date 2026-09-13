"""Propose complete teams from partner packages, not independent unit ranks."""
import itertools

JOINT_SCREEN_MEMBERSHIPS=12
JOINT_SCREEN_ORDERS=2


def diverse_order_combinations(choices,limit):
    """Cover every affected squad's priority before filling Cartesian gaps."""
    if not choices or any(not pool for pool in choices) or limit<=0:return []
    selected=[];seen=set()
    diagonal=(tuple(pool[index%len(pool)] for pool in choices) for index in range(max(map(len,choices))))
    for combination in itertools.chain(diagonal,itertools.product(*choices)):
        key=tuple(tuple(order) for order in combination)
        if key in seen:continue
        seen.add(key);selected.append(combination)
        if len(selected)>=limit:break
    return selected


def complete_teams(seed,available,catalog,guidance,valid,width=5,limit=3):
    seed=list(dict.fromkeys(seed))
    if len(seed)>5 or not set(seed)<=set(available):return []
    beam=[seed]
    while beam and len(beam[0])<5:
        choices={}
        for team in beam:
            missing=[s for s in ('1','2','3') if not any(catalog[n]['burst']==s for n in team)]
            slots=5-len(team)
            if len(missing)>slots:continue
            pool=[n for n in available if n not in team and (slots>len(missing) or catalog[n]['burst'] in missing)]
            for n in sorted(pool,key=lambda n:guidance.priority(n,team),reverse=True)[:12]:
                candidate=team+[n]
                if len(candidate)==5 and not valid(candidate):continue
                key=frozenset(candidate)
                choices[key]=candidate
        beam=sorted(choices.values(),key=guidance.score,reverse=True)[:width]
    return [t for t in beam if valid(t)][:limit]


def complete_team(seed,available,catalog,guidance,valid,width=5):
    return next(iter(complete_teams(seed,available,catalog,guidance,valid,width,1)),None)


def packages(guidance):
    """Keep named dependencies, explicit pair conditions, and full team cards."""
    found=[]
    for rule in guidance.data['dependencies']:
        anchor=guidance.resolve(rule['unit'])
        for slug in rule['any_of']:
            partner=guidance.resolve(slug)
            if anchor and partner:found.append([anchor,partner])
    for a,b,weight,rule in guidance.edges:
        if weight<=0 or not guidance.context(rule):continue
        required=[guidance.resolve(x) for x in rule.get('requires',[])]
        if any(n is None for n in required):continue
        choices=rule.get('requires_any',[])
        alternatives=[guidance.resolve(x) for x in choices] if choices else [None]
        for alternative in alternatives:
            if choices and not alternative:continue
            found.append(list(dict.fromkeys([a,b]+required+([alternative] if alternative else []))))
    found.extend(guidance.templates)
    if getattr(guidance,'kits',None):found.extend(map(list,guidance.kits.packages()))
    # Reserve combinations with a second B1/B2 for long-cooldown supports.
    # Keep the original package too: actual CDR may make the backup unnecessary.
    for package in list(found):
        for n in package:
            c=guidance.catalog[n]
            if c['burst'] not in ('1','2') or c['cooldown']<=20:continue
            if any(m!=n and guidance.catalog[m]['burst']==c['burst'] for m in package):continue
            partners=[m for m in guidance.roster if m not in package and guidance.catalog[m]['burst']==c['burst']]
            for m in sorted(partners,key=lambda m:guidance.priority(m,package),reverse=True)[:3]:
                if len(package)<5:found.append(package+[m])
    seen=set()
    for package in found:
        key=frozenset(package)
        if 2<=len(key)<=5 and key not in seen:
            seen.add(key);yield package


def allocations(ids,catalog,guidance,valid,ordered,team_count,limit):
    completed={};package_count=0
    for package in packages(guidance):
        package_count+=1
        teams=complete_teams(package,ids,catalog,guidance,lambda t:valid(t) and guidance.template_fits(package,t))
        for team in teams:completed.setdefault(frozenset(team),(team,package))
    # First cover distinct anchors, then additional combinations. This prevents
    # a single popular support package occupying every reserved comparison.
    ranked=sorted(completed.values(),key=lambda row:guidance.score(row[0]),reverse=True)
    selected=[];anchors=set();alternatives=[]
    for row in ranked:
        if row[1][0] not in anchors:selected.append(row);anchors.add(row[1][0])
        else:alternatives.append(row)
    # Reserve a few places for different supports around a strong anchor.
    # A named package can have several worthwhile completions, not one winner
    # selected solely by a static proposal score.
    primary=max(1,limit-max(1,limit//3))
    first=selected[:primary]
    support_signatures={(row[1][0],tuple(sorted(n for n in row[0] if catalog[n]['burst'] in ('1','2')))) for row in first}
    diverse=[]
    for row in alternatives:
        signature=(row[1][0],tuple(sorted(n for n in row[0] if catalog[n]['burst'] in ('1','2'))))
        if signature not in support_signatures:
            diverse.append(row);support_signatures.add(signature)
        if len(diverse)>=limit-primary:break
    selected=first+diverse+selected[primary:]+[row for row in alternatives if row not in diverse]
    plans=[];audit=[]
    for team,package in selected:
        allocation=[ordered(team)];available=[n for n in ids if n not in team]
        for _ in range(team_count-1):
            next_team=complete_team([],available,catalog,guidance,valid)
            if not next_team:break
            allocation.append(ordered(next_team));available=[n for n in available if n not in next_team]
        if len(allocation)!=team_count:continue
        key=tuple(sorted(tuple(t) for t in allocation))
        if key in plans:continue
        plans.append(key);audit.append({'package':package,'teams':[list(t) for t in key]})
        if len(plans)>=limit:break
    return plans,{'packages_available':package_count,'completed_memberships':len(completed),'reserved_allocations':audit,
                  'scope':'Bounded package search. A completed proposal is not evidence that its skill conditions activated.'}


def replacements(team,available,guidance,catalog,valid,limit=12):
    """Joint partner replacements can cross a one-unit local optimum."""
    candidates={}
    for package in packages(guidance):
        if not set(package)<=set(available) or set(package)<=set(team):continue
        missing=[n for n in package if n not in team]
        if len(missing)>2:continue
        removable=[n for n in team if n not in package]
        for outgoing in itertools.combinations(removable,len(missing)):
            candidate=[n for n in team if n not in outgoing]+missing
            if valid(candidate):candidates[frozenset(candidate)]={'members':candidate,'package':package,'outgoing':list(outgoing),'incoming':missing}
    ranked=sorted(candidates.values(),key=lambda row:guidance.score(row['members']),reverse=True)
    chosen=[];anchors=set()
    for row in ranked:
        anchor=row['package'][0]
        if anchor not in anchors:chosen.append(row);anchors.add(anchor)
        if len(chosen)>=limit:break
    return chosen


def joint_proposals(results,index,ids,guidance,catalog,valid,iteration=0,limit=10):
    """Move a partnership together, repairing every squad it borrows from."""
    team=results[index]['members']
    owners={n:i for i,row in enumerate(results) for n in row['members']}
    options=replacements(team,ids,guidance,catalog,valid,limit=limit*4)
    # Rotate lower-prior packages across rounds instead of revisiting only the
    # same strongest relationship. Also permit ordinary support exchanges.
    options=options[:3]+options[3+iteration*max(1,limit-3):][:max(1,limit-3)]
    for outgoing in team:
        remainder=[n for n in team if n!=outgoing]
        available=[n for n in ids if n not in team and valid(remainder+[n])]
        ranked=guidance.alternatives(available,remainder,iteration)
        if ranked:
            incoming=ranked[min(iteration,len(ranked)-1)]
            options.append({'members':remainder+[incoming],'package':[incoming],
                            'incoming':[incoming],'outgoing':[outgoing]})
    found={}
    for option in options:
        for outgoing in itertools.permutations(option['outgoing']):
            changes={index:list(option['members'])}
            for incoming,displaced in zip(option['incoming'],outgoing):
                donor=owners.get(incoming)
                if donor is not None:
                    donor_team=changes.setdefault(donor,list(results[donor]['members']))
                    donor_team[donor_team.index(incoming)]=displaced
            if not all(valid(t) for t in changes.values()):continue
            all_members=[n for i,row in enumerate(results) for n in changes.get(i,row['members'])]
            if len(all_members)!=len(set(all_members)):continue
            key=tuple(sorted((i,frozenset(t)) for i,t in changes.items()))
            found.setdefault(key,{'squad':index+1,'package':option['package'],'changes':changes})
    return list(found.values())


def refine_allocations(results,ids,catalog,guidance,valid,orders,prefetch,run,duration,exhausted,required=False,rounds=4):
    """Bounded joint moves, accepted only after all affected full fights finish."""
    from critical_parts import assessment
    def score(rows):return (sum(assessment(r)['passed'] for r in rows) if required else 0,sum(r['damage'] for r in rows))
    def gain(before,after):
        old,new=score(before),score(after)
        return (new[0]-old[0],new[1]-old[1])
    seen=set();audit=[];stable=0
    for iteration in range(rounds):
        if exhausted():break
        groups=[]
        for index in range(len(results)):
            if exhausted():break
            proposals=joint_proposals(results,index,ids,guidance,catalog,valid,iteration)
            # A donor's two exchange assignments must not monopolize the
            # opening sample before another partnership gets a comparison.
            first=[];others=[];anchors=set()
            for proposal in proposals:
                anchor=tuple(proposal['package'])
                if anchor not in anchors:first.append(proposal);anchors.add(anchor)
                else:others.append(proposal)
            groups.append(iter(first+others))
        # Round-robin squads before expanding orders. A large roster must not
        # turn one round into hundreds of opening simulations and leave no
        # opportunity to verify the promising joint moves through full fights.
        selected=[]
        while groups and len(selected)<JOINT_SCREEN_MEMBERSHIPS:
            remaining=[]
            for group in groups:
                for proposal in group:
                    key=tuple(sorted((i,frozenset(t)) for i,t in proposal['changes'].items()))
                    if key in seen:continue
                    seen.add(key);selected.append(proposal);remaining.append(group);break
                if len(selected)>=JOINT_SCREEN_MEMBERSHIPS:break
            groups=remaining
        expanded=[]
        for proposal in selected:
            affected=list(proposal['changes'])
            choices=[orders(proposal['changes'][i])[:2] for i in affected]
            for combination in diverse_order_combinations(choices,JOINT_SCREEN_ORDERS):
                expanded.append((proposal,dict(zip(affected,combination))))
        if not expanded:break
        sample=min(60,duration)
        prefetch([r['members'] for r in results]+[t for _,changes in expanded for t in changes.values()],sample,
                 phase='Refining squad partnerships and shared supports')
        screened=[]
        for proposal,changes in expanded:
            try:
                before=[run(results[i]['members'],sample) for i in changes]
                after=[run(t,sample) for t in changes.values()]
            except (ValueError,KeyError,IndexError,TypeError):continue
            screened.append((gain(before,after),proposal,changes))
        promoted=[];memberships=set();targets=set()
        for delta,proposal,changes in sorted(screened,key=lambda r:r[0],reverse=True):
            key=tuple(sorted((i,frozenset(t)) for i,t in changes.items()))
            if key in memberships or proposal['squad'] in targets:continue
            memberships.add(key);targets.add(proposal['squad']);promoted.append((proposal,changes))
            if len(promoted)>=3:break
        full=[]
        for proposal,changes in promoted:
            affected=list(changes)
            for combination in diverse_order_combinations([orders(changes[i])[:4] for i in affected],4):
                full.append((proposal,dict(zip(affected,combination))))
        if exhausted():break
        prefetch([t for _,changes in full for t in changes.values()],duration,True,
                 phase='Verifying joint changes across the affected squads')
        best=None;best_gain=(0,0)
        for proposal,changes in full:
            try:alternative={i:run(t,duration,True) for i,t in changes.items()}
            except (ValueError,KeyError,IndexError,TypeError):continue
            before=[results[i] for i in changes];after=list(alternative.values())
            delta=gain(before,after)
            record={'round':iteration+1,'squad':proposal['squad'],'package':proposal['package'],
                    'affected_squads':[i+1 for i in changes],'members':{i+1:list(t) for i,t in changes.items()},
                    'baseline_damage':sum(r['damage'] for r in before),'damage':sum(r['damage'] for r in after),
                    'part_pass_gain':delta[0],'accepted':False}
            audit.append(record)
            if delta>best_gain:best_gain=delta;best=(alternative,record)
        if best:
            for i,row in best[0].items():results[i]=row
            best[1]['accepted']=True;stable=0
        else:
            stable+=1
            if stable>=2:break
    return audit

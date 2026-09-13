"""Damage-driven chained interruption targets. Inputs use seconds and absolute HP."""
import copy
import math

class QTEGraph:
    def __init__(self,targets,start,deadline):
        self.targets={};self.start=start;self.deadline=deadline;self.status='active';self.events=[]
        for raw in targets:
            row=copy.deepcopy(raw)
            if row['id'] in self.targets:raise ValueError('Duplicate QTE target')
            if row['kind'] not in ('break','counter'):raise ValueError('Unknown QTE target type')
            for key in ['hp','duration']:
                if not isinstance(row[key],(int,float)) or not math.isfinite(row[key]) or row[key]<=0:raise ValueError('Invalid QTE target '+key)
            row.update(remaining=row['hp'],activated=None,status='pending')
            self.targets[row['id']]=row
        for row in self.targets.values():
            if any(k not in self.targets for k in row.get('chain',[])):raise ValueError('Dangling QTE chain')
        if not any(r.get('first') and r['kind']=='break' for r in self.targets.values()):raise ValueError('Missing first red target')
        for row in self.targets.values():
            if row.get('first'):self.activate(row['id'],start)

    def activate(self,ident,time):
        row=self.targets[ident]
        if row['status']!='pending':return
        row['activated']=time+row.get('delay',0);row['status']='scheduled'

    def advance(self,time):
        if self.status!='active':return
        if time>=self.deadline:self.status='failed';return
        for row in self.targets.values():
            if row['status']=='scheduled' and time>=row['activated']:row['status']='active'
            if row['status']=='active' and time>=row['activated']+row['duration']:
                row['status']='expired'
                if row['kind']=='break':self.status='failed'

    def aim(self,time):
        self.advance(time)
        if self.status!='active':return None
        eligible=[r for r in self.targets.values() if r['status']=='active' and r['kind']=='break']
        return min(eligible,key=lambda r:(r['activated']+r['duration'],r['id'])) if eligible else None

    def hit(self,ident,damage,time):
        self.advance(time)
        if not math.isfinite(damage) or damage<0:raise ValueError('Invalid QTE damage')
        row=self.targets[ident]
        if self.status!='active' or row['status']!='active' or damage==0:return 0
        if row['kind']=='counter':
            self.status='failed';self.events.append({'time':time,'event':'grey target hit','target':ident});return 0
        dealt=min(damage,row['remaining']);row['remaining']-=dealt
        if row['remaining']<=0:
            row['status']='destroyed';self.events.append({'time':time,'event':'red target destroyed','target':ident})
            for child in row.get('chain',[]):self.activate(child,time)
            if all(r['status']=='destroyed' for r in self.targets.values() if r['kind']=='break'):self.status='passed'
        return dealt

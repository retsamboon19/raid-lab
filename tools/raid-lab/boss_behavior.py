"""Tick-based execution of recovered behavior-tree control flow.

Leaf actions belong to the combat world. Unimplemented leaves raise rather than
silently succeeding. No wall-clock waits or damage-score fitting occur here.
"""
import random

RUNNING='running'
SUCCESS='success'
FAILURE='failure'

class UnsupportedBossAction(RuntimeError):
    pass

class BehaviorTree:
    def __init__(self,root,world,seed=42):
        self.root=root;self.world=world;self.rng=random.Random(seed)
        self.memory={};self.time=0.;self.status=RUNNING
        self.nodes={}
        def collect(node):
            ident=node['ID']
            if ident in self.nodes:raise ValueError('Duplicate behavior node ID')
            self.nodes[ident]=node
            for child in node.get('Children',[]):collect(child)
        collect(root)

    def reset(self,node):
        state=self.memory.pop(node['ID'],None)
        if state and state.get('leaf_running'):
            self.world.cancel(node,self.time)
        for child in node.get('Children',[]):self.reset(child)

    def advance(self,time):
        if time<self.time:raise ValueError('Boss clock cannot run backwards')
        self.time=time
        if self.status==RUNNING:self.status=self.tick(self.root)
        return self.status

    def tick(self,node):
        if node.get('Disabled'):return SUCCESS
        kind=node['Type'].split('.')[-1]
        state=self.memory.setdefault(node['ID'],{})
        children=[c for c in node.get('Children',[]) if not c.get('Disabled')]
        if kind.startswith('SpotRandom'):kind=kind.removeprefix('Spot')
        if kind in ('PatternSequence','PatternSelector'):
            state.setdefault('pattern_started',self.time)
            if self.time-state['pattern_started']>=node['Single_timeOut']:
                for child in children:self.reset(child)
                return node['PatternResult_timeOutResult'].lower()
            kind=kind.removeprefix('Pattern')
        if kind=='ChoiceSkillSelector':
            if 'chosen' not in state:
                selected=self.world.choose(node,self.time,state)
                if selected is None:return RUNNING
                if not 0<=selected<len(children):raise ValueError('Invalid boss attack choice')
                state['chosen']=selected
            return self.tick(children[state['chosen']])
        if kind=='InitVariables':
            if len(children)!=1:raise ValueError('Expected one root child')
            return self.tick(children[0])
        if kind in ('Sequence','Selector','RandomSequence','RandomSelector'):
            if 'order' not in state:
                state['order']=list(range(len(children)));state['position']=0
                if kind.startswith('Random'):self.rng.shuffle(state['order'])
            sequence=kind.endswith('Sequence')
            if sequence and node.get('AbortTypeabortType') in ('Self','Both') and state['position']>0:
                # Reevaluate completed leading conditions while an action runs.
                def conditional(n):
                    return '.Conditionals.' in n['Type'] or (n['Type'].endswith('.Inverter') and len(n.get('Children',[]))==1 and conditional(n['Children'][0]))
                for i in state['order'][:state['position']]:
                    child=children[i]
                    if not conditional(child):break
                    self.reset(child)
                    if self.tick(child)==FAILURE:
                        for c in children:self.reset(c)
                        return FAILURE
            while state['position']<len(children):
                child=children[state['order'][state['position']]]
                result=self.tick(child)
                if result==RUNNING:return result
                if result==(FAILURE if sequence else SUCCESS):return result
                state['position']+=1
            return SUCCESS if sequence else FAILURE
        if kind in ('Parallel','ParallelSelector','ParallelComplete'):
            completed=state.setdefault('completed',{})
            for child in children:
                if child['ID'] not in completed:
                    result=self.tick(child)
                    if result!=RUNNING:completed[child['ID']]=result
            if kind=='ParallelComplete' and completed:
                for child in children:
                    if child['ID'] not in completed:self.reset(child)
                return SUCCESS
            decisive=SUCCESS if kind=='ParallelSelector' else FAILURE
            if decisive in completed.values():
                for child in children:
                    if child['ID'] not in completed:self.reset(child)
                return decisive
            if len(completed)==len(children):return FAILURE if kind=='ParallelSelector' else SUCCESS
            return RUNNING
        if kind in ('Inverter','ReturnSuccess','ReturnFailure','StartAttack','EndAttack'):
            if not children and node.get('Children'):
                return FAILURE if kind=='ReturnFailure' else SUCCESS
            if len(children)!=1:raise ValueError('Decorator needs one child')
            result=self.tick(children[0])
            if result==RUNNING:return result
            if kind in ('StartAttack','EndAttack'):return result
            if kind=='Inverter':return FAILURE if result==SUCCESS else SUCCESS
            return SUCCESS if kind=='ReturnSuccess' else FAILURE
        if kind=='Repeater':
            if len(children)!=1:raise ValueError('Repeater needs one child')
            # At most one repetition per simulation tick prevents zero-time loops.
            result=self.tick(children[0])
            if result==RUNNING:return result
            if result==FAILURE and node.get('SharedBoolendOnFailure',{}).get('BooleanmValue',False):return FAILURE
            state['count']=state.get('count',0)+1
            forever=node.get('SharedBoolrepeatForever',{}).get('BooleanmValue',False)
            count=node.get('SharedIntcount',{}).get('Int32mValue',0)
            if not forever and state['count']>=count:return SUCCESS
            self.reset(children[0]);return RUNNING
        if 'started' not in state:state['started']=self.time
        result=self.world.action(node,self.time,state)
        if result not in (RUNNING,SUCCESS,FAILURE):raise ValueError('Invalid boss action result')
        state['leaf_running']=result==RUNNING
        return result

class StrictWorld:
    """Adapter contract. Missing physical semantics must never become a pass."""
    def action(self,node,time,state):
        raise UnsupportedBossAction(f"Unimplemented boss node {node['ID']}: {node['Type']}")
    def cancel(self,node,time):
        pass

"""Part/variable actions for recovered boss trees; attacks require real handlers."""
from boss_behavior import StrictWorld,RUNNING,SUCCESS,FAILURE
from boss_parts import BossParts

class PartWorld(StrictWorld):
    def __init__(self,part_hp,handlers=None):
        self.parts=BossParts();self.part_hp=dict(part_hp);self.variables={}
        self.handlers=handlers or {};self.cancel_handlers={}
    def action(self,node,time,state):
        kind=node['Type'].split('.')[-1]
        if kind=='SetVariableNode':
            self.variables[node['MonsterBtVariabletype']]=node['Int32value'];return SUCCESS
        if kind=='CheckVariableNode':
            return SUCCESS if self.variables.get(node['MonsterBtVariabletype'])==node['Int32value'] else FAILURE
        if kind=='TimeCount':
            if node.get('ETimeCountTypemType') not in ('None','Custom'):return super().action(node,time,state)
            return SUCCESS if time-state['started']>=node['SinglemCustomTime'] else RUNNING
        if kind=='CheckHp':
            # Kraken's part-liveness checks are zero-threshold checks. Other
            # threshold units are intentionally not guessed.
            if node['Int32mValue']!=0 or node.get('BooleanisUsingMianHp'):return super().action(node,time,state)
            alive=self.parts.alive(node['PartsTypemPartsType'])
            return SUCCESS if (not alive if node['BooleanmLower'] else alive) else FAILURE
        if kind in ('BrokenParts','BrokenPartsV2'):
            for part in node['List`1_partsList']:
                if self.parts.alive(part):self.parts.self_destruct(part,time)
            return SUCCESS
        if kind=='RepairPartsVer2':
            if time-state['started']<node['Single_repairTime']:return RUNNING
            if not state.get('repaired'):
                for part in node['List`1_partsList']:
                    self.parts.spawn(part,self.part_hp[part],time)
                state['repaired']=True
            return SUCCESS
        if kind in self.handlers:return self.handlers[kind](node,time,state,self)
        return super().action(node,time,state)
    def cancel(self,node,time):
        handler=self.cancel_handlers.get(node['Type'].split('.')[-1])
        if handler:handler(node,time,self)

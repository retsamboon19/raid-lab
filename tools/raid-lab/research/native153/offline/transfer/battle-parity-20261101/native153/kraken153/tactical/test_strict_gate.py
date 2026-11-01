"""Synthetic successful/negative evidence controls; no native execution."""
import copy
import json
from pathlib import Path
import unittest
import synthetic_gate_fixture as fixture
import verify_kraken_tactical153 as subject

SOURCE = json.loads((Path(__file__).parents[2]/'kraken153-qte-cover-source.json').read_text())


def rows():
    result = fixture.with_qte()
    result += [r for r in fixture.with_cover() if r['status'] in ('original_threat_event','native_cover_decision')]
    state = next(r for r in result if r['status']=='original_tactical_observation_change')
    state['qte']['currentOrder']=0
    state['qte']['targets']=[{'id':i,'entityId':101+i,'colType':{'name':'Break' if i%2==0 else 'Counter'},
                            'state':{'name':'Enable'},'order':0,'health':{'hp':'20'}}for i in range(14)]
    aim=next(r for r in result if r.get('action')=='aim_break')
    hit=next(r for r in result if r.get('kind')=='QuickTimeColliderHit')
    result.remove(aim);result.remove(hit)
    for i in range(0,14,2):
        result.append({**aim,'targetId':i,'entityId':101+i})
        result.append({**hit,'entityInfoId':101+i})
    stop=next(r for r in result if r['status']=='original_tick_driver_stopped')
    stop['tacticalControl'].update(clientSha256=subject.CLIENT)
    stop['tacticalControl']['coverPolicy']=fixture.with_cover()[3]['tacticalControl']['coverPolicy']
    mode=next(r for r in result if r['status']=='native_control_mode_selected')
    mode.update(clientSha256=subject.CLIENT,authoredSourceSha256=subject.AUTHORED_SHA)
    attack={'tick':10,'casterId':50,'attackNodeId':230,'sequence':1}
    danger=next(r for r in result if r.get('action')=='danger_observed')
    danger.update(monsterTableId='1520040153',attack=attack)
    result.append({'status':'original_threat_event','kind':'attack',**attack})
    return fixture.finalize(result)


def verify(value=None, source=None, **kwargs):
    return subject.verify(rows() if value is None else value, SOURCE if source is None else source,
                          client_sha256=kwargs.get('client',subject.CLIENT),
                          source_sha256=kwargs.get('sha',subject.AUTHORED_SHA))


class StrictGate(unittest.TestCase):
    def test_positive_synthetic(self):
        self.assertTrue(verify()['passed'],verify()['errors'])

    def test_unexercised_rejected(self):
        self.assertFalse(verify(fixture.base())['passed'])

    def test_wrong_client_and_source(self):
        self.assertFalse(verify(client='2df7134a')['passed'])
        self.assertFalse(verify(sha='0'*64)['passed'])

    def test_missing_seventh_target(self):
        data=rows();data[:]=[r for r in data if not(r.get('entityId')==113 or r.get('entityInfoId')==113)]
        self.assertFalse(verify(fixture.finalize(data))['passed'])

    def test_counter_hit_rejected(self):
        data=rows();next(r for r in data if r.get('kind')=='QuickTimeColliderHit')['entityInfoId']=102
        self.assertFalse(verify(data)['passed'])

    def test_source_group_and_count_rejected(self):
        source=copy.deepcopy(SOURCE);source['qte']['breakIds'].pop()
        self.assertFalse(verify(source=source)['passed'])
        data=rows();next(r for r in data if r.get('action')=='aim_break')['groupId']=102
        self.assertFalse(verify(data)['passed'])

    def test_native_success_required(self):
        data=rows();next(r for r in data if r.get('kind')=='QuickTimePresetEnd')['success']=False
        self.assertFalse(verify(data)['passed'])

    def test_no_cover_or_no_resume_rejected(self):
        data=[r for r in rows() if r.get('action')!='entered'];self.assertFalse(verify(data)['passed'])
        data=rows();next(r for r in data if r.get('action')=='resume_readback')['firingResumed']=False
        self.assertFalse(verify(data)['passed'])

    def test_character_damage_or_cover_ownership_rejected(self):
        data=rows();data.append({'status':'original_threat_event','kind':'damage','tick':15,'targetType':'Character','actualDamage':'1'})
        self.assertFalse(verify(fixture.finalize(data))['passed'])
        data=rows();next(r for r in data if r.get('action')=='released')['nativeAfter']['forcedCover']=True
        self.assertFalse(verify(data)['passed'])

    def test_missing_original_attack_or_wrong_monster(self):
        data=[r for r in rows() if not(r.get('status')=='original_threat_event' and r.get('kind')=='attack')]
        self.assertFalse(verify(fixture.finalize(data))['passed'])
        data=rows();next(r for r in data if r.get('action')=='danger_observed')['monsterTableId']='1'
        self.assertFalse(verify(data)['passed'])

    def test_truncated_or_faulted_rejected(self):
        data=rows();stop=next(r for r in data if r['status']=='original_tick_driver_stopped')
        stop['threatObservation']['transitionsTruncated']=True
        self.assertFalse(verify(data)['passed'])
        data=rows();next(r for r in data if r['status']=='original_tick_driver_stopped')['tacticalControl']['fault']='native fault'
        self.assertFalse(verify(data)['passed'])


if __name__=='__main__':unittest.main()

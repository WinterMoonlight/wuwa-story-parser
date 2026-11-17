import unittest
from types import SimpleNamespace
from unittest.mock import patch
from wuwa_story.phone_world_context import context_effect


class PhoneWorldTests(unittest.TestCase):
    def test_scalar_shapes_and_phase(self):
        a={'Name':'SetTime','Params':{'Hour':10,'Min':0,'ShowUi':False}}
        self.assertIsNotNone(context_effect(a,'EnterActions',None))
        for value in (True,24,-1):
            a['Params']['Hour']=value;self.assertIsNone(context_effect(a,'EnterActions',None))
        a={'Name':'FocusOnMapMark','Params':{'MapMarkType':{'Type':'Custom','MarkId':1}}}
        self.assertIsNone(context_effect(a,'EnterActions',None))
        self.assertIsNotNone(context_effect(a,'FinishActions',None))
        a['Params']['Callback']=[];self.assertIsNone(context_effect(a,'FinishActions',None))

    def test_entity_ambiguity_and_narrative_callback_rejected(self):
        row={'Id':1,'EntityId':9,'MapId':8,'BinData':b'x'}
        action={'Name':'AwakeEntity','Params':{'EntityIds':[9]}}
        source=SimpleNamespace(rows=lambda *_:[row,dict(row,MapId=9)])
        self.assertIsNone(context_effect(action,'FinishActions',source))
        source=SimpleNamespace(rows=lambda *_:[row])
        cfg={'TriggerComponent':{'Actions':[{'Name':'PlayFlow','Params':{'FlowListName':'x','FlowId':1,'StateId':1}}]}}
        with patch('wuwa_story.phone_world_context.embedded',return_value=[(1,cfg)]):
            self.assertIsNone(context_effect(action,'FinishActions',source))
        cfg={'BaseInfoComponent':{'Actions':[]}}
        with patch('wuwa_story.phone_world_context.embedded',return_value=[(1,cfg)]):
            self.assertIsNone(context_effect(action,'FinishActions',source))
        state={'Name':'ChangeEntityState','Params':{'Type':'Directly','EntityId':9,'State':'active'}}
        cfg={'EntityStateComponent':{'StateChangeBehaviors':[{'State':'active','PendingConditionAvailable':True,
            'Action':[{'Name':'PlayFlow','Params':{'FlowListName':'x','FlowId':1,'StateId':1}}]}]}}
        with patch('wuwa_story.phone_world_context.embedded',return_value=[(1,cfg)]):
            self.assertIsNone(context_effect(state,'FinishActions',source))

    def test_real_node_world_context_preserves_unverified_effects(self):
        from wuwa_story.database import rows,embedded
        node=next(embedded(r['BinData'])[0][1] for r in rows('db_QuestNodeData.db','questnodedata') if r['Key']=='173000000_2')
        source=SimpleNamespace(rows=rows)
        actions=[('EnterActions',node['EnterActions'][1])]+[('FinishActions',a)for a in node['FinishActions']]
        for phase,action in actions:
            with self.subTest(action=action['Name']):
                evidence=context_effect(action,phase,source)
                self.assertIsNotNone(evidence)
                self.assertFalse(evidence['runtime_executed'])
                self.assertFalse(evidence['world_state_effects_verified'])


if __name__=='__main__':unittest.main()

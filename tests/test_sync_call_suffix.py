import copy
import unittest
from wuwa_story.sync_call_suffix import consensus_proof

def fixture():
    def flow(i):return {'Name':'PlayFlow','Params':{'FlowListName':'f','FlowId':1,'StateId':i}}
    leaves=[{'Id':i,'Type':'ChildQuest','ParentNodeId':10,'FinishActions':[flow(1),flow(2)]} for i in (1,2)]
    slots=[{'Condition':{'Type':0,'Conditions':[{'Type':'CheckChildQuestFinished','QuestId':8,'ChildQuestId':9,'Compare':c}]},'Node':{k:v for k,v in n.items() if k!='ParentNodeId'}} for c,n in zip(('Eq','Ne'),leaves)]
    return {},leaves+[{'Id':10,'Type':'ConditionSelector','ParentNodeId':0,'Slots':slots}]

class ConsensusTests(unittest.TestCase):
    def test_exclusive_pair(self):
        q,n=fixture();p=consensus_proof(q,n,'f_1_1','f_1_2');self.assertEqual(p['owner_node_ids'],[1,2]);self.assertFalse(p['runtime_verified'])
    def test_reject_unmatched_and_inconsistent(self):
        q,n=fixture();q['Flow']={'FlowListName':'f','FlowId':1,'StateId':1};self.assertIsNone(consensus_proof(q,n,'f_1_1','f_1_2'))
        q,n=fixture();n[0]['FinishActions'][1]['Async']=True;self.assertIsNone(consensus_proof(q,n,'f_1_1','f_1_2'))
        q,n=fixture();n[-1]['Slots'][1]['Condition']=copy.deepcopy(n[-1]['Slots'][0]['Condition']);self.assertIsNone(consensus_proof(q,n,'f_1_1','f_1_2'))
    def test_real_case(self):
        from wuwa_story.batch import Snapshot
        from wuwa_story.database import embedded
        s=Snapshot();ns=[embedded(r['BinData'])[0][1] for r in s.rows('db_QuestNodeData.db','questnodedata') if r['Key'].startswith('114000026_')]
        q=next(embedded(r['BinData'])[0][1] for r in s.rows('db_QuestData.db','questdata') if r['QuestId']==114000026)
        prefix='剧情_2_0_黎那汐塔主线_序幕_'
        self.assertEqual(consensus_proof(q,ns,prefix+'1_1',prefix+'10_1')['owner_node_ids'],[114,123,130])
    def test_unknown_ancestor_control_rejected(self):
        q,n=fixture();n[-1]['RepeatCount']=2
        self.assertIsNone(consensus_proof(q,n,'f_1_1','f_1_2'))
        q,n=fixture();n[-1]['Slots'][0]['Callback']={}
        self.assertIsNone(consensus_proof(q,n,'f_1_1','f_1_2'))

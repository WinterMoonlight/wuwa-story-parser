import copy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.database import texts
from wuwa_story.export_task import flow_actions, Exporter
from wuwa_story.qte_consensus import consensus_projection
from wuwa_story.recap_backbone import export_task_backbone


class QteConsensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key='剧情_3_5_穗穗线_玩法副本_1_6_1'
        row=next(r for r in Snapshot().rows('db_flowState.db','flowstate') if r['StateKey']==cls.key)
        cls.actions=flow_actions(row['BinData'])[0]
        cls.show=next(a for a in cls.actions if a['Name']=='ShowTalk')

    def test_all_declared_paths_have_one_text_signature(self):
        items, proof=consensus_projection(self.show,texts)
        self.assertEqual([i['Id'] for i in items],[1,2,3,4])
        self.assertEqual(proof['outcome_path_count'],32)
        self.assertEqual(len(proof['qte_talk_ids']),5)
        self.assertFalse(proof['runtime_completion_verified'])
        self.assertFalse(proof['qte_result_selected'])
        result=export_task_backbone(880000045)
        segment=next(s for s in result['recap_backbone']['segments'] if s['state_key']==self.key)
        self.assertEqual(segment['status'],'parsed')
        self.assertEqual([e['talk_id'] for e in segment['events']],[1,2,3,4])
        self.assertFalse(segment['route']['choices'])
        self.assertEqual(segment['source_actions'],self.actions)
        self.assertEqual(segment['action_trace'][-1]['Name'],'PostAkEvent')

    def test_mismatch_unknown_outcome_or_side_effect_rejected(self):
        for mode in ('missing_outcome','unknown_outcome','cycle','side_effect','edge','async','speech_key','condition','extra','timeout'):
            action=copy.deepcopy(self.show)
            p=action['Params']; q=next(i for i in p['TalkItems'] if i['Type']=='QTE')
            if mode=='missing_outcome':q['Options'].pop()
            elif mode=='unknown_outcome':q['Options'][0]['TypeParams']['Type']='Cancel'
            elif mode=='cycle':q['Options'][0]['Actions'][0]['Params']['TalkId']=q['Id']
            elif mode=='side_effect':q['Options'][0]['Actions'].append({'Name':'SetVar','Params':{}})
            elif mode=='edge':p['SequenceTransitions']['0'][0]['NextSequenceIndex']=4
            elif mode=='async':action['Async']=True
            elif mode=='speech_key':p['TalkItems'][-1]['TidTalk']='not_found'
            elif mode=='condition':q['Condition']={}
            elif mode=='extra':q['UnknownCallback']={}
            else:action['Timeout']=10
            self.assertIsNone(consensus_projection(action,texts),mode)

    def test_branch_specific_text_cannot_be_folded(self):
        action=copy.deepcopy(self.show)
        first_branch=next(i for i in action['Params']['TalkItems'] if i['Id']==5)
        first_branch.update(Type='Talk',TidTalk='branch_only',WhoId=1,Actions=[])
        self.assertIsNone(consensus_projection(action,{**texts,'branch_only':'only one outcome'}))

    def test_ordinary_and_strict_parser_still_rejects_qte(self):
        for review,capture in ((False,False),(True,False)):
            parser=Exporter(allow_incomplete=review,capture_control_prefix=capture)
            parser.state_key=self.key
            with self.assertRaisesRegex(ValueError,'QTE runtime'):
                parser.actions(self.actions)

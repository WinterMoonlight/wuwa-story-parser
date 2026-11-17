import copy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.export_task import flow_actions
from wuwa_story.terminal_text import project_terminal_text, last_item_terminal_evidence
from wuwa_story.prefix_boundary import UnresolvedControlBoundary
from wuwa_story.recap_backbone import export_task_backbone


class TerminalTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = {r['StateKey']: r for r in Snapshot().rows('db_flowState.db','flowstate')}
        cls.key = '剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_21_1'
        cls.actions = flow_actions(cls.states[cls.key]['BinData'])[0]

    def test_all_eight_choices_end_with_original_control_evidence(self):
        for opening in range(2):
            for ending in range(4):
                result = export_task_backbone(114000029, {f'{self.key}:1':opening, f'{self.key}:8':ending})
                segment = next(s for s in result['recap_backbone']['segments'] if s['state_key']==self.key)
                self.assertEqual(segment['status'],'parsed')
                self.assertEqual(len(segment['events']),9)
                proof = next(p for p in segment['unverified_content'] if p['kind']=='terminal_text_projection')
                self.assertEqual(proof['selected_terminal_ids'],[9+ending])
                self.assertFalse(proof['state_controls_executed'])
                self.assertFalse(proof['cross_segment_propagation'])
                self.assertFalse(proof['runtime_completion_verified'])
                self.assertTrue(any(a.get('Name')=='SetVar' for t in segment['source_actions'][-1]['Params']['TalkItems'] for a in t.get('Actions',[])))
                self.assertEqual(segment['events'][-1]['source_item']['Actions'][0]['Name'],'SetVar')

    def test_projection_refuses_unknown_or_nonterminal_shapes(self):
        self.assertIsNotNone(project_terminal_text(self.actions))
        for mode in ('suffix','async','condition','jump','global','edge'):
            actions=copy.deepcopy(self.actions)
            p=actions[-1]['Params']
            if mode=='suffix': actions.append({'Name':'ShowCenterText','Params':{'TidCenterText':'x'}})
            elif mode=='async': actions[-1]['Async']=True
            elif mode=='condition': p['TalkItems'][0]['Condition']={}
            elif mode=='jump': p['TalkItems'][-1]['Actions'].append({'Name':'JumpTalk','Params':{'TalkId':1}})
            elif mode=='global': p['TalkItems'][-1]['Actions'][0]['Params']['VarLeft']['Source']='Global'
            elif mode=='edge': p['SequenceTransitions']['7'][0]['NextSequenceIndex']=0
            self.assertIsNone(project_terminal_text(actions), mode)

    def test_early_cancel_is_not_terminal_last_item(self):
        key='剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_60_1'
        result=export_task_backbone(114000029,{key+':1':1})
        segment=next(s for s in result['recap_backbone']['segments'] if s['state_key']==key)
        self.assertEqual(segment['status'],'blocked')
        self.assertEqual(segment['prefix_event_count'],2)
        self.assertFalse(segment['control_boundary']['boundary_executed'])

    def test_terminal_boundary_rejects_mismatched_reached_item(self):
        key='剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_60_1'
        actions=flow_actions(self.states[key]['BinData'])[0]
        finish=actions[-1]['Params']['TalkItems'][-1]['Actions'][-1]
        exc=UnresolvedControlBoundary(finish,key)
        self.assertIsNone(last_item_terminal_evidence(actions,exc,1))
        self.assertIsNotNone(last_item_terminal_evidence(actions,exc,3))

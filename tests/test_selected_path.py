"""Selected-route reachability must not execute or hide unsupported state transfers."""
import unittest
from unittest.mock import patch
from wuwa_story.database import rows
from wuwa_story.export_task import Exporter, flow_actions


class SelectedPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = {r['StateKey']: r for r in rows('db_flowState.db', 'flowstate')}

    def parse_state(self, key, choices=None):
        parser = Exporter(allow_incomplete=True, choices=choices)
        parser.state_key = key
        actions, _ = flow_actions(self.states[key]['BinData'])
        parser.actions(actions)
        return parser

    def test_real_unselected_finish_state_does_not_block_selected_interaction(self):
        key = '剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_21_2'
        parser = self.parse_state(key)
        self.assertEqual([e['talk_id'] for e in parser.events if e['kind']=='dialogue'], [1, 2])
        self.assertEqual(len(parser.events), 3)
        with self.assertRaisesRegex(ValueError, 'FinishState'):
            self.parse_state(key, {key+':1': 3})

    def test_real_early_finish_talk_preserves_order_without_entering_longer_branch(self):
        key = '剧情_新主线_CE版_第一章_第四幕_奔策候残星_1_4'
        parser = self.parse_state(key)
        self.assertEqual([e['talk_id'] for e in parser.events if e['kind']=='dialogue'], [1, 2, 3, 4, 7])
        self.assertEqual(len(parser.events), 7)
        with self.assertRaisesRegex(ValueError, 'FinishState'):
            self.parse_state(key, {key+':7': 1, key+':11': 1, key+':17': 1})

    def test_real_unselected_change_state_cannot_change_following_dialogue(self):
        key = '剧情_2_7_黎那汐塔主线_上半_2_27_1'
        parser = self.parse_state(key)
        self.assertEqual([e['talk_id'] for e in parser.events if e['kind']=='dialogue'], [1,2,3,4,5,6,7,9,10,11,13,14,15])
        self.assertEqual(len(parser.events), 17)
        with self.assertRaisesRegex(ValueError, 'ChangeState'):
            self.parse_state(key, {key+':14': 1})

    def test_real_selected_finish_state_remains_blocked(self):
        key = '剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_60_1'
        for choices in [None, {key+':1': 1}]:
            with self.assertRaisesRegex(ValueError, 'FinishState'):
                self.parse_state(key, choices)

    def test_deferred_controls_are_audited_but_other_unknowns_still_block(self):
        control = {'Name': 'FinishState', 'Params': {}}
        items = [{'Type':'Talk','Id':1,'TidTalk':'ask','Options':[
            {'TidTalkOption':'safe','Actions':[{'Name':'FinishTalk','Params':{}}]},
            {'TidTalkOption':'unknown','Actions':[control]}]}]
        with patch('wuwa_story.export_task.texts', {'ask':'问题','safe':'结束','unknown':'未知'}):
            parser=Exporter(allow_incomplete=True); parser.state_key='test'; parser.talk(items)
            self.assertEqual(len(parser.events),2)
            audit = next(v for v in parser.unverified_content if v['kind']=='unselected_control_actions')
            self.assertEqual(audit['controls'], [{'talk_id':1, 'source_action':control}])
            self.assertFalse(parser.talk_coverage[0]['all_branch_actions_verified'])
            self.assertEqual(parser.talk_coverage[0]['unselected_control_actions'], audit['controls'])
            parser=Exporter(allow_incomplete=True,choices={'test:1':1}); parser.state_key='test'
            with self.assertRaisesRegex(ValueError,'FinishState'): parser.talk(items)
            parser=Exporter(); parser.state_key='test'
            with self.assertRaisesRegex(ValueError,'FinishState'): parser.talk(items)
            control['Name']='UnknownControl'
            parser=Exporter(allow_incomplete=True); parser.state_key='test'
            with self.assertRaisesRegex(ValueError,'UnknownControl'): parser.talk(items)

    def test_conditions_and_qte_remain_gates_even_if_not_selected(self):
        for tail in [
            {'Type':'Talk','Id':2,'Conditions':[]},
            {'Type':'QTE','Id':2}]:
            parser=Exporter(allow_incomplete=True); parser.state_key='test'
            with self.assertRaises(ValueError):
                parser.talk([{'Type':'Talk','Id':1,'Actions':[{'Name':'FinishTalk','Params':{}}]},tail])

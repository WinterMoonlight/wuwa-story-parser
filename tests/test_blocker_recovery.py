import copy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.combined_information import inspect_combined_information, matching_dialogue_branches
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.qte_evidence import linear_qte_prefix
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class BlockerRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.states = {row['StateKey']: row for row in cls.source.rows('db_flowState.db', 'flowstate')}
        cls.info_key = '剧情_3_0_主线_拉海洛主线_上半_1_17_1'
        cls.qte_key = '剧情_2_7_黎那汐塔主线_下半_3_6'
        cls.info_actions, _ = flow_actions(cls.states[cls.info_key]['BinData'])
        cls.info = next(action['Params'] for action in cls.info_actions if action['Name'] == 'ShowTalk')
        cls.qte_actions, _ = flow_actions(cls.states[cls.qte_key]['BinData'])
        cls.qte = next(action['Params'] for action in cls.qte_actions if action['Name'] == 'ShowTalk')

    def test_information_branch_and_merge_order_both_choices(self):
        for selected, count, branch in ((0, 22, [7, 8]), (1, 20, [9])):
            parser = Exporter(source=self.source, allow_incomplete=True,
                              choices={f'{self.info_key}:6': selected})
            parser.state_key = self.info_key
            parser.actions(self.info_actions)
            self.assertEqual(len(parser.events), count)
            ids = [event['talk_id'] for event in parser.events if event['kind'] == 'dialogue']
            self.assertEqual(ids, list(range(1, 7)) + branch + list(range(10, 20)))
            self.assertEqual(len(parser.unordered_attachments), 1)
            panel = parser.unordered_attachments[0]
            self.assertEqual(panel['board_id'], 30010011)
            self.assertEqual(panel['call_anchor']['after_event_count'], 6)
            self.assertFalse(panel['interleaving_with_dialogue_verified'])
            self.assertEqual(len(panel['texts']), 2)
            self.assertFalse(parser.missing)
        strict = Exporter(source=self.source)
        strict.state_key = self.info_key
        with self.assertRaises(ValueError):
            strict.actions(self.info_actions)

    def test_sequence_and_option_mismatch_rejected(self):
        for mutation in ('key', 'target', 'duplicate', 'extra_edge', 'condition', 'branch_action'):
            params = copy.deepcopy(self.info)
            item = next(node for node in params['TalkItems'] if node['Id'] == 6)
            if mutation == 'key':
                params['SequenceTransitions']['0'][0]['OptionTextKey'] = 'wrong'
            elif mutation == 'target':
                item['Options'][0]['Actions'][0]['Params']['TalkId'] = 8
            elif mutation == 'duplicate':
                params['TalkSequence'][1].append(7)
            elif mutation == 'extra_edge':
                params['SequenceTransitions']['3'] = []
            elif mutation == 'condition':
                item['Options'][0]['PreCondition'] = {}
            else:
                params['TalkItems'][6]['Options'][0]['Actions'] = [{'Name': 'FinishState', 'Params': {}}]
            self.assertFalse(matching_dialogue_branches(item, params), mutation)

    def test_panel_execution_and_source_rejected_when_uncertain(self):
        for mutation in ('async', 'callback', 'dynamic_type', 'missing', 'dynamic_text'):
            params = copy.deepcopy(self.info)
            item = next(node for node in params['TalkItems'] if node['Id'] == 6)
            action = item['Actions'][0]
            if mutation == 'async':
                action['Async'] = True
            elif mutation == 'callback':
                action['OnFinish'] = []
            elif mutation == 'dynamic_type':
                action['Params']['SystemType'] = 'Enrollment'
            elif mutation == 'missing':
                action['Params']['BoardId'] = -1
            else:
                from unittest.mock import patch
                with patch('wuwa_story.combined_information.render_text', return_value='{unknown}'):
                    with self.assertRaises(ValueError):
                        inspect_combined_information(item, params, self.source.rows)
                continue
            with self.assertRaises(ValueError, msg=mutation):
                inspect_combined_information(item, params, self.source.rows)

    def test_real_reading_segment_and_remaining_enrollment(self):
        result = export_task_backbone(915000001)
        segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == self.info_key)
        self.assertEqual(segment['status'], 'parsed')
        enrollment = next(s for s in result['recap_backbone']['segments'] if s['state_key'].endswith('_1_15_1'))
        self.assertEqual(enrollment['status'], 'parsed')
        self.assertEqual(len(enrollment['events']), 27)
        self.assertEqual(enrollment['events'][1]['kind'], 'ui_reference')
        evidence = next(e for e in enrollment['unverified_content'] if e.get('kind') == 'panel_return_text_route')
        self.assertEqual(evidence['text_event_count'], 26)
        self.assertFalse(evidence['runtime_return_verified'])
        body = reading_text(result)
        self.assertIn('本段资料面板', body)
        self.assertIn('星炬学院交通安全管理条例', body)

    def test_async_showtalk_does_not_establish_panel_order(self):
        actions = copy.deepcopy(self.info_actions)
        next(action for action in actions if action['Name'] == 'ShowTalk')['Async'] = True
        parser = Exporter(source=self.source, allow_incomplete=True)
        parser.state_key = self.info_key
        with self.assertRaisesRegex(ValueError, 'dialogue order'):
            parser.actions(actions)

    def test_qte_prefix_is_still_blocked(self):
        from unittest.mock import patch
        with patch('wuwa_story.qte_text_order.append_configured_qte_text', return_value=False):
            result = export_task_backbone(175000000)
        segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == self.qte_key)
        self.assertEqual(segment['status'], 'blocked')
        self.assertEqual(segment['prefix_event_count'], 2)
        self.assertEqual([e.get('talk_id') for e in segment['events'][:-1]], [1, 2])
        self.assertEqual(segment['events'][-1]['kind'], 'recap_gap')
        self.assertFalse(segment['control_boundary']['boundary_executed'])
        self.assertFalse(segment['control_boundary']['runtime_completion_verified'])
        self.assertEqual(segment['error'], 'QTE runtime outcome evaluator is unsupported')
        records = [record for record in result['batch_coverage']['records']
                   if record.get('order_scope') == 'recap_prefix_only' and not record.get('is_placeholder')]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record['category'] == 'unverified' and not record['order_verified'] for record in records))

    def test_qte_prefix_refuses_ambiguous_or_branching_shapes(self):
        self.assertEqual(len(linear_qte_prefix(self.qte)), 2)
        for mutation in ('sequence', 'condition', 'action', 'option', 'duplicate', 'suffix'):
            params = copy.deepcopy(self.qte)
            if mutation == 'sequence':
                params['TalkSequence'][0].reverse()
            elif mutation == 'condition':
                params['TalkItems'][0]['Condition'] = {}
            elif mutation == 'action':
                params['TalkItems'][0]['Actions'] = [{'Name': 'JumpTalk', 'Params': {'TalkId': 3}}]
            elif mutation == 'option':
                params['TalkItems'][0]['Options'] = [{}]
            elif mutation == 'duplicate':
                params['TalkItems'][1]['Id'] = 1
            else:
                params['TalkItems'][-1]['Type'] = 'Talk'
            self.assertIsNone(linear_qte_prefix(params), mutation)

    def test_qte_capture_requires_explicit_review_mode(self):
        for review, capture, asynchronous in ((False, True, False), (True, False, False), (True, True, True)):
            parser = Exporter(source=self.source, allow_incomplete=review, capture_control_prefix=capture)
            parser.state_key = self.qte_key
            actions = copy.deepcopy(self.qte_actions)
            next(action for action in actions if action['Name'] == 'ShowTalk')['Async'] = asynchronous
            with self.assertRaisesRegex(ValueError, 'QTE runtime'):
                parser.actions(actions)
            self.assertFalse(parser.events)

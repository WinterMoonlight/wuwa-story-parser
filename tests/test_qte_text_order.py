from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.batch import Snapshot
from wuwa_story.database import texts
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.qte_text_order import configured_qte_sequence
from wuwa_story.reading import reading_text
from wuwa_story.rendering import render_text
from wuwa_story.recap_backbone import export_task_backbone


def show(items, order):
    return {'Name': 'ShowTalk', 'Params': {'TalkItems': items, 'TalkSequence': [order],
            'SequenceNames': ['sequence'], 'SequenceTransitions': {}}}


class QteTextOrderTests(unittest.TestCase):
    def setUp(self):
        self.action = show([
            {'Type': 'Talk', 'Id': 30, 'TidTalk': 'test_line_after'},
            {'Type': 'QTE', 'Id': 1, 'QteId': 2, 'TidTalk': 'control_key'},
            {'Type': 'Talk', 'Id': 20, 'TidTalk': 'test_line_before'}], [20, 1, 30])

    def test_uses_declared_sequence_and_keeps_original_source(self):
        original = deepcopy(self.action)
        with patch.dict(texts, {'test_line_before': 'before', 'test_line_after': 'after'}):
            parser = Exporter(allow_incomplete=True, configured_text_order=True)
            parser.state_key = 'test'
            parser.actions([self.action])
        self.assertEqual([e['kind'] for e in parser.events], ['dialogue', 'qte_reference', 'dialogue'])
        self.assertEqual([e['talk_id'] for e in parser.events if e['kind'] == 'dialogue'], [20, 30])
        self.assertEqual(parser.events[0]['source_item'], original['Params']['TalkItems'][2])
        self.assertEqual(parser.events[1]['source_items'], [original['Params']['TalkItems'][1]])
        proof = parser.unverified_content[-1]
        self.assertEqual(proof['declared_talk_ids'], [20, 1, 30])
        self.assertFalse(proof['qte_result_selected'])
        self.assertFalse(proof['all_runtime_outcomes_verified'])
        self.assertEqual(proof['source_action'], original)
        self.assertEqual(self.action, original)

    def test_runtime_or_strict_modes_retain_qte_boundary(self):
        for incomplete, ordered in ((False, False), (False, True), (True, False)):
            parser = Exporter(allow_incomplete=incomplete, configured_text_order=ordered)
            parser.state_key = 'test'
            with self.assertRaisesRegex(ValueError, 'QTE runtime'):
                parser.actions([self.action])
            self.assertEqual(parser.events, [])

    def test_outcome_edges_conditions_and_actions_are_rejected(self):
        for change in ('async', 'edge', 'option', 'condition', 'action', 'duplicate', 'missing', 'boolean_id', 'unknown'):
            action = deepcopy(self.action)
            params = action['Params']
            item = params['TalkItems'][1]
            if change == 'async': action['Async'] = True
            elif change == 'edge': params['SequenceTransitions'] = {'0': [{'NextSequenceIndex': 1}]}
            elif change == 'option': item['Options'] = [{'TypeParams': {'Type': 'QteSucceed'}}]
            elif change == 'condition': item['Condition'] = {}
            elif change == 'action': item['Actions'] = [{'Name': 'JumpTalk', 'Params': {'TalkId': 30}}]
            elif change == 'duplicate': params['TalkSequence'][0] = [20, 1, 1, 30]
            elif change == 'missing': params['TalkSequence'][0] = [20, 1]
            elif change == 'boolean_id': item['QteId'] = True
            else: item['OnFinish'] = []
            self.assertIsNone(configured_qte_sequence(action), change)

    def test_missing_speech_keeps_its_place_and_is_reported(self):
        parser = Exporter(allow_incomplete=True, configured_text_order=True)
        parser.state_key = 'test'
        parser.actions([self.action])
        self.assertEqual(set(parser.missing), {'test_line_before', 'test_line_after'})
        self.assertEqual([e.get('text_id') for e in parser.events], ['test_line_before', None, 'test_line_after'])

    def test_pure_qte_block_is_preserved_without_inventing_dialogue(self):
        parser = Exporter(allow_incomplete=True, configured_text_order=True)
        parser.state_key = 'test'
        parser.actions([show([{'Type': 'QTE', 'Id': 0, 'QteId': 1}], [0])])
        self.assertEqual(len(parser.events), 1)
        self.assertEqual(parser.events[0]['kind'], 'qte_reference')
        self.assertTrue(parser.events[0]['content_deferred'])
        self.assertEqual(parser.unverified_content[-1]['ordered_text_ids'], [])

    def test_empty_qte_group_preserves_following_showtalk_group_number(self):
        parser = Exporter(allow_incomplete=True, configured_text_order=True)
        parser.state_key = 'test'
        with patch.dict(texts, {'after': 'after'}):
            parser.actions([show([{'Type': 'QTE', 'Id': 1, 'QteId': 1}], [1]),
                            show([{'Type': 'Talk', 'Id': 1, 'TidTalk': 'after'}], [1])])
        self.assertEqual([event['talk_group'] for event in parser.events], [1, 2])
        self.assertEqual(len(parser.talk_coverage), 2)

    def test_all_four_real_recap_cases_use_configured_text_order(self):
        source = Snapshot()
        states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
        cases = [(175000000, '剧情_2_7_黎那汐塔主线_下半_3_6', 2),
                 (936000002, '剧情_3_0_拉海洛主线_下半_2_4_5', 0),
                 (114000031, '剧情_3_1_拉梅洛地上主线_高达流程_3_1', 1),
                 (114000031, '剧情_3_1_拉梅洛地上主线_高达流程_10_1', 2)]
        results = {}
        for quest, key, count in cases:
            if quest not in results:
                results[quest] = export_task_backbone(quest)
            result = results[quest]
            segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == key)
            self.assertEqual(segment['status'], 'parsed')
            self.assertNotIn('prefix_event_count', segment)
            self.assertEqual(segment['source_actions'], flow_actions(states[key]['BinData'])[0])
            self.assertEqual(sum(e['kind'] == 'dialogue' for e in segment['events']), count)
            self.assertIn('qte_reference', [e['kind'] for e in segment['events']])
            self.assertEqual([e['text'] for e in segment['events'] if e['kind'] == 'dialogue'],
                             [render_text(texts[e['text_id']]) for e in segment['events'] if e['kind'] == 'dialogue'])
            self.assertFalse(result['batch_coverage']['text_order_review']['whole_task_text_order_verified'])
            body = reading_text({'title': '', 'events': segment['events'], 'validation': {}})
            self.assertIn('操作结果未模拟', body)


if __name__ == '__main__':
    unittest.main()

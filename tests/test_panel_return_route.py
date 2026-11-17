from copy import deepcopy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.pending_boundary import PendingDialogueBoundary, enrollment_return_route
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text
from wuwa_story.speakers import SpeakerResolver


class PanelReturnRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.key = '剧情_3_0_主线_拉海洛主线_上半_1_15_1'
        row = next(r for r in cls.source.rows('db_flowState.db', 'flowstate') if r['StateKey'] == cls.key)
        cls.actions = flow_actions(row['BinData'])[0]
        cls.items = next(a for a in cls.actions if a['Name'] == 'ShowTalk')['Params']['TalkItems']
        cls.boundary = PendingDialogueBoundary('enrollment', cls.items[0]['Actions'][0], cls.key, cls.items[0])
        cls.names = SpeakerResolver().records

    def test_both_dialogue_branches_rejoin_and_keep_original_items(self):
        original = deepcopy(self.actions)
        for choice, branch in ((0, [19, 20]), (1, [21, 22])):
            parser = enrollment_return_route(self.actions, self.boundary, self.source, self.names,
                                              {self.key + ':18': choice})
            self.assertIsNotNone(parser)
            ids = [e['talk_id'] for e in parser.events if e['kind'] == 'dialogue']
            self.assertEqual(ids, list(range(1, 19)) + branch + [23, 24])
            self.assertEqual(len(parser.events), 27)
            self.assertEqual(parser.events[1]['kind'], 'ui_reference')
            self.assertTrue(parser.events[1]['content_deferred'])
            expected = {item['Id']: item for item in self.items}
            for event in parser.events:
                if event['kind'] == 'dialogue':
                    self.assertEqual(event['source_item'], expected[event['talk_id']])
            selections = {d['choice_key']: d['selected_index'] for d in parser.decisions}
            self.assertEqual(selections[self.key + ':18'], choice)
            proof = parser.unverified_content[-1]
            self.assertEqual(proof['text_event_count'], 26)
            self.assertTrue(proof['local_text_order_verified'])
            self.assertTrue(proof['conditional_on_panel_return'])
            self.assertFalse(proof['runtime_return_verified'])
            self.assertFalse(proof['panel_display_timing_verified'])
            self.assertEqual(proof['original_boundary'], self.boundary.as_dict())
        self.assertEqual(self.actions, original)

    def test_unproven_conditions_controls_suffix_or_repeated_visit_are_rejected(self):
        for change in ('condition', 'variable', 'missing_jump', 'cycle', 'second_ui', 'suffix_control', 'second_show', 'async_show'):
            actions = deepcopy(self.actions)
            show = next(a for a in actions if a['Name'] == 'ShowTalk')
            items = show['Params']['TalkItems']
            if change == 'condition':
                items[1]['Condition'] = {}
            elif change == 'variable':
                items[1]['Actions'] = [{'Name': 'SetVar', 'Params': {}}]
            elif change == 'missing_jump':
                items[19]['Actions'][0]['Params']['TalkId'] = -999
            elif change == 'cycle':
                items[19]['Actions'][0]['Params']['TalkId'] = 18
            elif change == 'second_ui':
                items[1]['Actions'] = deepcopy(items[0]['Actions'])
            elif change == 'suffix_control':
                actions.append({'Name': 'ChangeState', 'Params': {}})
            elif change == 'second_show':
                actions.append(deepcopy(show))
            else:
                show['Async'] = True
            self.assertIsNone(enrollment_return_route(actions, self.boundary, self.source, self.names, None), change)

    def test_ui_metadata_and_explicit_invalid_choice_are_rejected(self):
        for change in ('async', 'callback', 'board', 'option_action'):
            actions = deepcopy(self.actions)
            first = next(a for a in actions if a['Name'] == 'ShowTalk')['Params']['TalkItems'][0]
            if change == 'async':
                first['Actions'][0]['Async'] = True
            elif change == 'callback':
                first['Actions'][0]['OnFinish'] = []
            elif change == 'board':
                first['Actions'][0]['Params']['BoardId'] = 1
            else:
                first['Options'][0]['Actions'] = [{'Name': 'FinishState', 'Params': {}}]
            self.assertIsNone(enrollment_return_route(actions, self.boundary, self.source, self.names, None), change)
        self.assertIsNone(enrollment_return_route(self.actions, self.boundary, self.source, self.names,
                                                  {self.key + ':18': 9}))

    def test_batch_reading_entry_point_keeps_condition_and_deduplicates_old_fragment(self):
        result = export_task_backbone(915000001)
        segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == self.key)
        self.assertEqual(segment['status'], 'parsed')
        self.assertNotIn('local_fragments', segment)
        self.assertNotIn('prefix_event_count', segment)
        self.assertEqual(segment['source_actions'], self.actions)
        body = reading_text({'title': 'test', 'events': segment['events'], 'validation': {}})
        self.assertEqual(body.count('【入学界面】'), 1)
        self.assertNotIn('界面调用后的配置对白', reading_text(result))
        records = [r for r in result['batch_coverage']['records'] if r.get('order_scope') == 'panel_return_recap_segment']
        self.assertEqual(len(records), 27)
        self.assertEqual(sum(not r['is_placeholder'] for r in records), 26)
        self.assertTrue(all(not r['order_verified'] for r in records))
        self.assertEqual(result['batch_coverage']['text_order_review']['categories'], {'panel_return_text_ordered': 1})
        self.assertFalse(result['batch_coverage']['text_order_review']['whole_task_text_order_verified'])

    def test_regular_parser_retains_original_boundary(self):
        parser = Exporter(source=self.source, allow_incomplete=True, capture_control_prefix=True)
        parser.state_key = self.key
        with self.assertRaises(PendingDialogueBoundary):
            parser.actions(self.actions)
        self.assertEqual(len(parser.events), 1)


if __name__ == '__main__':
    unittest.main()

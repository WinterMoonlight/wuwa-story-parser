from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.batch import Snapshot
from wuwa_story.conditional_route import conditional_text_route
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.reading import reading_text
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.speakers import SpeakerResolver
from wuwa_story.text_order import deferred_sequence


class TextOrderScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.states = {r['StateKey']: r for r in cls.source.rows('db_flowState.db', 'flowstate')}
        cls.key = '剧情_尤诺线npc生态_5_1'
        cls.actions = flow_actions(cls.states[cls.key]['BinData'])[0]
        cls.names = SpeakerResolver().records

    def test_conditional_routes_keep_selected_indices_and_original_sources(self):
        original = deepcopy(self.actions)
        items = next(a for a in original if a['Name'] == 'ShowTalk')['Params']['TalkItems']
        by_id = {i['Id']: i for i in items}
        for selected, ids in ((0, [1, 2, 3, 4, 5, 6, 7]), (1, [1, 2, 12, 8, 9, 10, 11])):
            choices = {self.key + ':2': selected}
            parser = conditional_text_route(self.actions, self.key, self.source, self.names, choices)
            self.assertIsNotNone(parser)
            self.assertEqual(len(parser.events), 8)
            self.assertEqual([e['talk_id'] for e in parser.events if e['kind'] == 'dialogue'], ids)
            self.assertEqual(parser.decisions[0]['selected_index'], selected)
            self.assertEqual(len(parser.decisions[0]['options']), 2)
            self.assertEqual(parser.decisions[0]['choice_key'], self.key + ':2')
            for event in parser.events:
                if event['kind'] == 'dialogue':
                    self.assertEqual(event['source_item'], by_id[event['talk_id']])
            proof = parser.unverified_content[-1]
            self.assertTrue(proof['local_text_order_verified'])
            self.assertFalse(proof['witness_is_current_state'])
            self.assertFalse(proof['runtime_route_verified'])
            self.assertEqual(len(proof['symbolic_effects']), 3)
            self.assertEqual(proof['end_basis'], 'FinishTalk' if selected == 0 else 'array_end')
        self.assertEqual(self.actions, original)

    def test_conditional_route_refuses_unproven_shapes(self):
        for change in ('global', 'cycle', 'later_read', 'second_show', 'extra_guard', 'early_write'):
            actions = deepcopy(self.actions)
            show = next(a for a in actions if a['Name'] == 'ShowTalk')
            items = show['Params']['TalkItems']
            option = items[1]['Options'][0]
            if change == 'global':
                option['PreCondition']['Conditions']['Conditions'][0]['Var1']['Source'] = 'Global'
            elif change == 'cycle':
                option['Actions'][0]['Params']['TalkId'] = 1
            elif change == 'later_read':
                items[5]['Actions'] = [deepcopy(items[4]['Actions'][1])]
            elif change == 'second_show':
                actions.append(deepcopy(show))
            elif change == 'extra_guard':
                option['PreCondition']['Conditions']['Type'] = 1
            else:
                actions.insert(0, deepcopy(items[4]['Actions'][0]))
            self.assertIsNone(conditional_text_route(actions, self.key, self.source, self.names,
                                                    {self.key + ':2': 0}), change)
        self.assertIsNone(conditional_text_route(self.actions, self.key, self.source, self.names,
                                                {self.key + ':2': 99}))

    def test_ambiguous_owner_is_rejected(self):
        class DuplicateOwner:
            def rows(inner, file, table):
                values = self.source.rows(file, table)
                if file == 'db_level_entity.db':
                    row = next(r for r in values if r['MapId'] == 8 and r['EntityId'] == 185750018)
                    return values + [row]
                return values
        self.assertIsNone(conditional_text_route(self.actions, self.key, DuplicateOwner(), self.names))

    def test_target_component_callbacks_are_not_hidden_by_visual_projection(self):
        from wuwa_story.database import embedded
        def unreviewed_config(blob):
            values = deepcopy(embedded(blob))
            for _, value in values:
                if isinstance(value, dict) and set(value) == {'BaseInfoComponent', 'EntityStateComponent', 'SceneActorRefComponent'}:
                    value['EntityStateComponent']['Actions'] = [{'Name': 'PlayFlow', 'Params': {}}]
            return values
        with patch('wuwa_story.conditional_route.embedded', side_effect=unreviewed_config):
            self.assertIsNone(conditional_text_route(self.actions, self.key, self.source, self.names))

    def test_reading_entry_point_uses_condition_and_retains_fallback_contract(self):
        result = export_task_backbone(886000001)
        segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == self.key)
        self.assertEqual(segment['status'], 'parsed')
        self.assertEqual(len(segment['events']), 8)
        self.assertEqual(segment['source_actions'], self.actions)
        self.assertNotIn('prefix_event_count', segment)
        self.assertIn('【条件路线】', reading_text(result))
        self.assertEqual(result['batch_coverage']['text_order_review']['categories']['conditional_text_ordered'], 1)
        for review in (False, True):
            parser = Exporter(source=self.source, allow_incomplete=review)
            parser.state_key = self.key
            with self.assertRaises(ValueError):
                parser.actions(self.actions)

    def test_deferred_media_rejects_later_dialogue_or_unknown_callbacks(self):
        actions = [{'Name': 'SetPlotMode', 'Params': {'Mode': 'LevelB'}},
                   {'Name': 'PlaySequenceData', 'Params': {'Path': '/Game/Example.Example',
                    'FrameEvents': [{'EventKey': 'A', 'EventActions': [
                        {'Name': 'UnlockEntity', 'Params': {'EntityIds': [1]}}]}]}}]
        proof = deferred_sequence(actions, 'test')
        self.assertIsNotNone(proof)
        self.assertFalse(proof['frame_order_verified'])
        for change in ('suffix', 'async', 'unknown', 'duplicate', 'boolean_id', 'old_supported'):
            copy = deepcopy(actions)
            frame = copy[-1]['Params']['FrameEvents'][0]
            if change == 'suffix':
                copy.append({'Name': 'ShowTalk', 'Params': {'TalkItems': []}})
            elif change == 'async':
                copy[-1]['Async'] = True
            elif change == 'unknown':
                frame['EventActions'][0]['Name'] = 'PlayFlow'
            elif change == 'duplicate':
                copy[-1]['Params']['FrameEvents'].append(deepcopy(frame))
            elif change == 'boolean_id':
                frame['EventActions'][0]['Params']['EntityIds'] = [True]
            else:
                frame['EventActions'] = []
            self.assertIsNone(deferred_sequence(copy, 'test'), change)

    def test_four_media_cases_are_deferred_without_counting_placeholder_as_text(self):
        cases = [(125900000, '剧情_1_1_乘宵山主线_岩壁遗迹_5_2'),
                 (114000030, '剧情_2_0_主线_金库上层副本_2_19'),
                 (114000030, '剧情_2_0_主线_金库上层副本_2_20'),
                 (139000031, '剧情_第四章_26_2')]
        cache = {}
        for quest_id, key in cases:
            if quest_id not in cache:
                cache[quest_id] = export_task_backbone(quest_id)
            result = cache[quest_id]
            segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == key)
            self.assertEqual(segment['status'], 'parsed')
            self.assertEqual(segment['source_actions'], flow_actions(self.states[key]['BinData'])[0])
            self.assertTrue(segment['events'][0]['content_deferred'])
            self.assertEqual(segment['unverified_content'][-1]['local_dialogue_count'], 0)
            entry = next(e for e in result['batch_coverage']['text_order_review']['entries'] if e['state_key'] == key)
            self.assertEqual(entry['category'], 'media_content_deferred')
            self.assertEqual(entry['local_event_count'], 0)
            self.assertIn('【演出】内部内容后置。', reading_text(result))


if __name__ == '__main__':
    unittest.main()

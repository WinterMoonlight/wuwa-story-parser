from sqlite3 import OperationalError
import unittest
from unittest.mock import Mock

from wuwa_story.chapter_recap import _place_groups, _task_window, recover_chapter_recap
from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
from wuwa_story.recap_backbone import export_task_backbone


class ChapterRecapTests(unittest.TestCase):
    def test_chapter_draft_reorders_existing_selected_events(self):
        document = export_task_backbone(125000120)
        recap = document['chapter_recap_order']
        self.assertEqual(recap['recap_quest_id'], 125900000)
        self.assertEqual([e['entry_index'] for e in recap['flow_entries']], [1, 2, 4, 8, 10])
        view = build_mainline_reading(document)
        self.assertEqual(view['status'], 'ordered_draft')
        self.assertEqual(view['retained_text_events'], 85)
        self.assertEqual(view['omission_markers'], 0)
        self.assertFalse(recap['runtime_order_verified'])
        self.assertFalse(document['batch_coverage']['order']['selected_route_verified'])
        self.assertFalse(document['events'])
        self.assertEqual(len(document['task_local_sequences']), 5)

    def test_unplaced_gameplay_stays_separate_from_complete_task_draft(self):
        document = export_task_backbone(146000002)
        view = build_mainline_reading(document)
        self.assertEqual(view['status'], 'ordered_draft_with_gaps')
        self.assertEqual(view['retained_text_events'], 51)
        recap = document['chapter_recap_order']
        self.assertTrue(recap['gameplay_outside_recap'])
        self.assertTrue(recap['covers_task_groups'])
        self.assertFalse(recap['covers_all_reading_groups'])
        self.assertEqual(recap['flow_entries'][0]['entry_index'], 135)
        scopes = [block['scope'] for block in view['blocks']]
        self.assertLess(scopes.index('chapter_recap_flow'), scopes.index('local_gameplay_flow'))
        self.assertIn('玩法局部片段列在后面，具体位置待确认', mainline_reading_text(document))

    def test_master_of_time_places_opening_before_first_tip(self):
        document = export_task_backbone(125000123)
        placed = [e['entry_index'] for e in document['chapter_recap_order']['flow_entries']
                  if e['local_segment'] is not None]
        self.assertEqual(placed, [150, 151, 152, 154, 155])
        view = build_mainline_reading(document)
        self.assertEqual(view['status'], 'ordered_draft_with_gaps')
        self.assertEqual(view['retained_text_events'], 111)

    def test_three_task_drafts_restore_chapter_dialogue_with_exact_triggers(self):
        chapter = export_task_backbone(125900000)
        chapter_events = {s['entry_index']: s['events'] for s in chapter['recap_backbone']['segments']}
        cases = (
            (125000121, 52, 141, 'optional_interaction_unlocked_after_flow', 223, 1),
            (125000122, 113, 47, 'task_interaction', 77, 0),
            (125000123, 160, 26, 'dungeon_combat_state', 111, 3),
        )
        for task, entry_index, node_id, trigger_kind, count, omissions in cases:
            with self.subTest(task=task):
                result = export_task_backbone(task)
                slots = result['chapter_recap_order']['flow_entries']
                entry = next(x for x in slots if 'recap_segment' in x)
                self.assertEqual(entry['entry_index'], entry_index)
                restored = entry['recap_segment']
                fields = ('kind', 'text_id', 'raw_text', 'display_name')
                projection = lambda events: [tuple(e.get(k) for k in fields) for e in events]
                self.assertEqual(projection(restored['events']), projection(chapter_events[entry_index]))
                self.assertEqual((restored['trigger']['kind'], restored['trigger']['node_id']),
                                 (trigger_kind, node_id))
                self.assertFalse(restored['runtime_order_verified'])
                view = build_mainline_reading(result)
                self.assertEqual((view['retained_text_events'], view['omission_markers']), (count, omissions))
                if task == 125000123:
                    missing = next(i for i, slot in enumerate(slots) if slot['entry_index'] == 162)
                    pointer = f'/chapter_recap_order/flow_entries/{missing}'
                    self.assertTrue(any(b['scope'] == 'chapter_recap_gap' and b['source_pointer'] == pointer
                                        for b in view['blocks']))

    def test_chapter_wide_recap_adds_final_seal_dialogue_before_archive(self):
        from wuwa_story.reading_cases.chengxiao import ARCHIVE, SEAL, WATER

        result = export_task_backbone(125900000)
        segments = result['recap_backbone']['segments']
        index = next(i for i, s in enumerate(segments) if s['state_key'] == WATER)
        self.assertEqual(segments[index + 1]['state_key'], ARCHIVE)
        continuation = segments[index]['current_task_continuation']
        self.assertEqual(continuation['state_key'], SEAL)
        self.assertEqual([event['text_id'] for event in continuation['events']],
                         [f'Chengxiaoshan_main_1_1_372_{i}' for i in range(1, 4)])
        proof = continuation['placement']
        self.assertEqual((proof['owner_quest_id'], proof['levelplay_id']), (146000002, 146000053))
        self.assertEqual(proof['selected_threshold']['node_id'], 12)
        self.assertEqual(proof['selected_threshold']['threshold'], 3)
        self.assertEqual([t['entry_index'] for t in proof['recap_tips']], [145, 146, 147])
        self.assertFalse(proof['dialogue_completion_order_verified'])
        view = build_mainline_reading(result)
        self.assertEqual(view['retained_text_events'], 736)
        self.assertEqual(view['omission_markers'], 10)
        blocks = view['blocks']
        added = next(i for i, b in enumerate(blocks) if b['scope'] == 'current_task_continuation')
        self.assertEqual(blocks[added + 1]['parts'][0]['kind'], 'omission')

    def test_window_rejects_interleaved_or_ambiguous_ownership(self):
        owners = {'a': {1}, 'b': {2}, 'shared': {1, 2}}
        for tips in (('a', 'b', 'a'), ('a', 'shared', 'b')):
            with self.subTest(tips=tips):
                entries = [{'TidTip': tip} for tip in tips]
                self.assertIsNone(_task_window(entries, [1, 2], 1, owners))

    def test_window_moves_only_the_unique_consecutive_leading_flow(self):
        first = {'Flow': {'FlowListName': 'test', 'FlowId': 1, 'StateId': 1}}
        second = {'Flow': {'FlowListName': 'test', 'FlowId': 1, 'StateId': 2}}
        tips = {'a': {1}, 'b': {2}}
        entries = [{'TidTip': 'a'}, first, second, {'TidTip': 'b'}]
        owners = {'test_1_1': {1}, 'test_1_2': {2}}
        self.assertEqual(_task_window(entries, [1, 2], 1, tips, owners), (0, 2, [0]))
        self.assertEqual(_task_window(entries, [1, 2], 2, tips, owners), (2, 4, [3]))
        self.assertEqual(_task_window(entries, [1, 2], 2, tips, {'test_1_2': {1, 2}}), (3, 4, [3]))
        self.assertEqual(_task_window([*entries, second], [1, 2], 2, tips, owners), (3, 5, [3]))

    def test_flow_placement_rejects_conflicting_or_repeated_states(self):
        first = {'Flow': {'FlowListName': 'test', 'FlowId': 1, 'StateId': 1}}
        second = {'Flow': {'FlowListName': 'test', 'FlowId': 1, 'StateId': 2}}
        groups = [{'local_order_verified': True, 'segments': [{'state_key': key}]}
                  for key in ('test_1_1', 'test_1_2')]
        edges = [{'from_state': 'test_1_1', 'to_state': 'test_1_2'}]
        self.assertIsNotNone(_place_groups([first, second], 0, 2, groups, edges))
        self.assertIsNone(_place_groups([second, first], 0, 2, groups, edges))
        self.assertIsNone(_place_groups([first, second, first], 0, 3, groups, edges))

    def test_missing_optional_recall_database_leaves_fragments_unchanged(self):
        source = Mock()
        source.rows.side_effect = OperationalError('unable to open database file')
        quest = {'Id': 1, 'Type': 1, 'ChapterId': 10}
        self.assertIsNone(recover_chapter_recap(quest, [], [{}], {}, source))

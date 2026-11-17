from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.sequence_task_review import review_sequence_task


class SequenceTaskReviewTests(unittest.TestCase):
    def fixture(self):
        nodes = [{'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 20, 'Type': 'ChildQuest', 'ParentNodeId': 1,
                  'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'f', 'FlowId': 8, 'StateId': 1}},
                  'FinishActions': [{'Name': 'TeleportDungeon', 'Params': {'DungeonId': 77}}]},
                 {'Id': 3, 'Type': 'ChildQuest', 'ParentNodeId': 1,
                  'Condition': {'Type': 'FinishDungeon', 'Condition': {'Type': 'DungeonId', 'DungeonId': 77, 'Count': 1}}},
                 {'Id': 4, 'Type': 'QuestSucceed', 'ParentNodeId': 1}]
        segment = {'state_key': 'f_8_1', 'events': [{'kind': 'dialogue', 'text': '正文'}],
                   'route': {'choices': []}, 'missing_text_ids': []}
        return nodes, segment

    def test_local_flow_and_dungeon_relation_do_not_create_sibling_order(self):
        nodes, segment = self.fixture()
        original = deepcopy(nodes)
        with patch('wuwa_story.sequence_task_review._flow_segment', return_value=segment):
            groups, review = review_sequence_task({}, nodes, {'f_8_1': {}}, None)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['order_scope'], 'single_flow_without_task_order')
        self.assertFalse(review['whole_task_order_verified'])
        self.assertFalse(review['sequence_groups'][0]['child_order_verified'])
        self.assertEqual(review['sequence_groups'][0]['child_node_ids'], [20, 3, 4])
        self.assertEqual(review['dungeon_completion_relations'][0]['from_node'], 20)
        self.assertEqual(review['dungeon_completion_relations'][0]['to_node'], 3)
        self.assertEqual(nodes, original)

    def test_branch_or_invalid_parent_not_silently_flattened(self):
        for mode in ('parallel', 'condition', 'cycle', 'duplicate'):
            with self.subTest(mode=mode):
                nodes, _ = self.fixture()
                if mode == 'parallel':
                    nodes[0]['Type'] = 'ParallelSelect'
                elif mode == 'condition':
                    nodes[0]['Condition'] = {'Type': 'Unknown'}
                elif mode == 'cycle':
                    nodes[1]['ParentNodeId'] = 20
                else:
                    nodes.append(deepcopy(nodes[1]))
                self.assertEqual(review_sequence_task({}, nodes, {}, None), ([], None))

    def test_existing_local_sequence_and_shared_reference_not_duplicated(self):
        nodes, _ = self.fixture()
        self.assertEqual(review_sequence_task({}, nodes, {}, None, [{'state_keys': ['f_8_1']}]), ([], None))
        quest = {'Flow': deepcopy(nodes[1]['Condition']['Flow'])}
        self.assertEqual(review_sequence_task(quest, nodes, {'f_8_1': {}}, None), ([], None))

    def test_missing_or_failed_flow_preserves_successful_other_segment(self):
        nodes, segment = self.fixture()
        nodes.append({'Id': 50, 'ParentNodeId': 1, 'Type': 'ChildQuest',
                      'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'f', 'FlowId': 9, 'StateId': 1}}})
        with patch('wuwa_story.sequence_task_review._flow_segment', return_value=segment):
            groups, review = review_sequence_task({}, nodes, {'f_8_1': {}}, None)
        self.assertEqual(len(groups), 1)
        self.assertEqual(review['flow_failures'][0]['state_key'], 'f_9_1')

    def test_visibility_is_evidence_only(self):
        nodes, segment = self.fixture()
        nodes[1]['FinishActions'].append({'Name': 'SetEntityVisible', 'Params': {'Visible': True, 'EntityIds': [80]}})
        nodes.append({'Id': 5, 'Type': 'ChildQuest', 'ParentNodeId': 1,
                      'Condition': {'Type': 'DoInteract', 'AddOptions': [{'EntityId': 80}]}})
        with patch('wuwa_story.sequence_task_review._flow_segment', return_value=segment):
            _, review = review_sequence_task({}, nodes, {'f_8_1': {}}, None)
        self.assertEqual(review['visibility_candidates'][0]['to_node'], 5)
        self.assertFalse(review['visibility_candidates'][0]['order_verified'])

    def test_real_master_of_time_keeps_unknown_global_order(self):
        from collections import Counter
        from wuwa_story.reading import reading_text
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(125000123)
        groups = result['task_local_sequences']
        self.assertEqual(len(groups), 5)
        kinds = Counter(e['kind'] for g in groups for s in g['segments'] for e in s['events'])
        self.assertEqual(kinds, {'dialogue': 99, 'choice': 6, 'media_reference': 1})
        review = result['sequence_execution_review']
        self.assertFalse(review['whole_task_order_verified'])
        self.assertEqual([r['node_id'] for r in review['sequence_groups']], [1, 2, 76])
        self.assertEqual(review['dungeon_completion_relations'][0]['from_node'], 78)
        self.assertEqual(review['dungeon_completion_relations'][0]['to_node'], 79)
        self.assertEqual(review['visibility_candidates'][0]['from_node'], 83)
        self.assertEqual(review['visibility_candidates'][0]['to_node'], 65)
        self.assertIn('【顺序缺口】', reading_text(result))
        selected = {(s['state_key'], e.get('text_id')) for g in groups for s in g['segments'] for e in s['events'] if e.get('text_id')}
        self.assertFalse(any((r.get('origin'), r.get('text_id')) in selected for r in result['batch_coverage']['records'] if r.get('origin')))


if __name__ == '__main__':
    unittest.main()

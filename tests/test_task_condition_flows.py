from copy import deepcopy
import struct
import unittest
from unittest.mock import patch

from wuwa_story.task_condition_flows import condition_task_sequences


class TaskConditionFlowTests(unittest.TestCase):
    def node(self, node_id, parent_id, state_id):
        return {'Id': node_id, 'ParentNodeId': parent_id, 'Type': 'ChildQuest',
                'Condition': {'Type': 'PlayFlow', 'Flow': {
                    'FlowListName': 'f', 'FlowId': 1, 'StateId': state_id}}}

    def fixture(self):
        female = {'Id': 4, 'Type': 'Sequence', 'Children': [self.node(5, 4, 2)]}
        male = {'Id': 6, 'Type': 'Sequence', 'Children': [self.node(7, 6, 3)]}
        slots = [{'Condition': {'Type': 0, 'Conditions': [
                    {'Type': 'CheckPlayerGender', 'Gender': gender}]}, 'Node': node}
                 for gender, node in [('女', female), ('男', male)]]
        nodes = [{'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0},
                 self.node(2, 1, 1),
                 {'Id': 3, 'Type': 'ConditionSelector', 'ParentNodeId': 1, 'Slots': slots},
                 {'Id': 4, 'Type': 'Sequence', 'ParentNodeId': 3}, deepcopy(female['Children'][0]),
                 {'Id': 6, 'Type': 'Sequence', 'ParentNodeId': 3}, deepcopy(male['Children'][0])]
        return deepcopy(nodes)

    def collect(self, nodes, existing=(), quest=None, choices=None, error=None):
        segment = {'events': [{'kind': 'dialogue', 'text': '正文'}], 'missing_text_ids': []}
        with patch('wuwa_story.task_condition_flows._flow_segment',
                   side_effect=error, return_value=segment) as parser:
            groups, review = condition_task_sequences(quest or {}, nodes,
                {f'f_1_{i}': {} for i in (1, 2, 3)}, None, existing, choices)
        return groups, review, parser

    def test_female_inline_copies_are_verified_and_counted_once(self):
        nodes = self.fixture()
        original = deepcopy(nodes)
        choices = {'f_1_2:1': 1}
        groups, review, parser = self.collect(nodes, choices=choices)
        self.assertEqual([g['node_id'] for g in groups], [2, 5])
        self.assertEqual([g['state_keys'] for g in groups], [['f_1_1'], ['f_1_2']])
        self.assertEqual(review['gender_selections'][0]['excluded_node_ids'], [6, 7])
        self.assertEqual(groups[1]['proof']['gender_selections'][0]['selected_slot'], 0)
        self.assertEqual(parser.call_args.args[-1], choices)
        self.assertEqual(nodes, original)
        self.assertTrue(all(g['local_order_verified'] and not g['mainline_placement_verified'] for g in groups))
        self.assertFalse(review['whole_task_order_verified'])

    def test_ambiguous_gender_or_conflicting_copies_keep_branch_unresolved(self):
        for mode in ('inline_mismatch', 'inline_parent', 'same_gender', 'extra_condition', 'missing_flat_node', 'extra_root'):
            with self.subTest(mode=mode):
                nodes = self.fixture()
                if mode == 'inline_mismatch':
                    nodes[2]['Slots'][0]['Node']['Children'][0]['Condition']['Flow']['StateId'] = 99
                elif mode == 'inline_parent':
                    nodes[2]['Slots'][0]['Node']['Children'][0]['ParentNodeId'] = 999
                elif mode == 'same_gender':
                    nodes[2]['Slots'][1]['Condition']['Conditions'][0]['Gender'] = '女'
                elif mode == 'extra_condition':
                    nodes[2]['Slots'][0]['Condition']['Conditions'].append({'Type': 'Unknown'})
                elif mode == 'missing_flat_node':
                    nodes = [n for n in nodes if n['Id'] != 5]
                else:
                    nodes.append({'Id': 8, 'Type': 'Sequence', 'ParentNodeId': 3})
                groups, review, _ = self.collect(nodes)
                self.assertEqual([g['node_id'] for g in groups], [2])
                self.assertFalse(review['gender_selections'])
                self.assertTrue(review['rejected_selectors'])

    def test_existing_groups_and_distinct_calls_are_not_duplicated(self):
        nodes = self.fixture()
        groups, _, _ = self.collect(nodes, existing=[{'state_keys': ['f_1_1']}])
        self.assertEqual([g['node_id'] for g in groups], [5])
        nodes.append(self.node(8, 1, 1))
        groups, _, _ = self.collect(nodes)
        self.assertEqual([g['node_id'] for g in groups], [5])

    def test_failed_disabled_and_invalid_ancestry_are_rejected(self):
        for mode in ('failed', 'disabled', 'cycle', 'conditional_parent', 'duplicate_node'):
            with self.subTest(mode=mode):
                nodes = self.fixture()[:2]
                if mode == 'failed':
                    nodes[1]['FailedCondition'] = {'Type': 'Fail'}
                elif mode == 'disabled':
                    nodes[1]['Disabled'] = True
                elif mode == 'cycle':
                    nodes[0]['ParentNodeId'] = 2
                elif mode == 'conditional_parent':
                    nodes[0]['Condition'] = {'Type': 'Unknown'}
                else:
                    nodes.append(deepcopy(nodes[1]))
                self.assertFalse(self.collect(nodes)[0])

    def test_corrupt_flow_is_diagnostic_and_does_not_drop_other_evidence(self):
        groups, review, _ = self.collect(self.fixture(), error=struct.error('invalid binary'))
        self.assertFalse(groups)
        self.assertEqual(len(review['flow_failures']), 2)
        self.assertEqual(len(review['gender_selections']), 1)

    def test_real_wind_female_conversation_and_ending_are_present(self):
        from wuwa_story.recap_backbone import export_task_backbone
        from wuwa_story.mainline_reading import build_mainline_reading
        result = export_task_backbone(125000124)
        groups = result['task_local_sequences']
        keys = [k for group in groups for k in group['state_keys']]
        self.assertEqual(set(keys), {f'剧情_1_1_乘宵山主线_8_{i}' for i in (1, 2, 3)})
        self.assertEqual(len(keys), 3)
        view = build_mainline_reading(result)
        self.assertEqual(view['retained_text_events'], 67)
        self.assertEqual(view['status'], 'local_fragments_only')
        self.assertFalse(result['condition_flow_review']['whole_task_order_verified'])
        female = next(g for g in groups if g['node_id'] == 84)
        self.assertEqual(female['proof']['gender_selections'][0]['selector_id'], 89)

    def test_real_dream_dust_retains_female_branch_and_all_selected_flows(self):
        from wuwa_story.recap_backbone import export_task_backbone
        from wuwa_story.mainline_reading import build_mainline_reading
        result = export_task_backbone(125000120)
        self.assertEqual(build_mainline_reading(result)['retained_text_events'], 85)
        self.assertTrue(any(g['node_id'] == 105 for g in result['task_local_sequences']))
        self.assertFalse(any(g['node_id'] == 114 for g in result['task_local_sequences']))


if __name__ == '__main__':
    unittest.main()

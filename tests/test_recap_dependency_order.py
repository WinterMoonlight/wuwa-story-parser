from copy import deepcopy
import unittest

from wuwa_story.dependencies import dependency_report
from wuwa_story.recap_dependency_order import repair_dependency_order


class RecapDependencyOrderTests(unittest.TestCase):
    def fixture(self):
        before = {'FlowListName': 'flow', 'FlowId': 1, 'StateId': 1}
        after = {'FlowListName': 'flow', 'FlowId': 1, 'StateId': 2}
        nodes = [{'Id': 10, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 20, 'Type': 'ChildQuest', 'ParentNodeId': 10,
                  'Condition': {'Type': 'PlayFlow', 'Flow': before},
                  'FinishActions': [{'Name': 'AwakeEntity', 'Params': {'EntityIds': [7]}},
                                    {'Name': 'PlayFlow', 'Params': after, 'Async': True}]}]
        keys = ['flow_1_2', 'flow_1_3', 'flow_1_1']
        backbone = {'segments': [{'state_key': key, 'entry_index': i, 'status': 'parsed',
                                 'events': [{'text': key}]} for i, key in enumerate(keys)],
                    'order_source': {'entries': [{'name': key} for key in keys]}}
        return nodes, backbone, dependency_report({}, nodes, keys)

    def test_completed_flow_precedes_async_invocation_with_stable_other_order(self):
        nodes, backbone, dependencies = self.fixture()
        original = deepcopy(backbone)
        proofs = repair_dependency_order({}, nodes, backbone, dependencies)
        self.assertEqual(len(proofs), 1)
        self.assertEqual([s['state_key'] for s in backbone['segments']], ['flow_1_3', 'flow_1_1', 'flow_1_2'])
        self.assertTrue(proofs[0]['invocation_async'])
        self.assertFalse(proofs[0]['runtime_executed'])
        self.assertFalse(proofs[0]['completion_order_verified'])
        self.assertEqual(backbone['order_source'], original['order_source'])
        self.assertEqual(sorted(backbone['segments'], key=lambda s: s['entry_index']), original['segments'])

    def test_sync_invocation_uses_same_completion_dependency(self):
        nodes, backbone, dependencies = self.fixture()
        nodes[1]['FinishActions'][-1]['Async'] = False
        proofs = repair_dependency_order({}, nodes, backbone, dependencies)
        self.assertEqual(len(proofs), 1)
        self.assertFalse(proofs[0]['invocation_async'])

    def test_ambiguous_references_or_recap_occurrences_remain_unchanged(self):
        for mode in ('reference', 'recap'):
            with self.subTest(mode=mode):
                nodes, backbone, dependencies = self.fixture()
                if mode == 'reference':
                    nodes[0]['ExtraFlow'] = nodes[1]['Condition']['Flow']
                else:
                    backbone['segments'].append(deepcopy(backbone['segments'][0]))
                old = deepcopy(backbone)
                self.assertFalse(repair_dependency_order({}, nodes, backbone, dependencies))
                self.assertEqual(backbone, old)

    def test_unknown_control_branch_or_incomplete_segment_rejected(self):
        for mode in ('prefix', 'async_value', 'parallel', 'condition', 'prefix_segment', 'broken_parent'):
            with self.subTest(mode=mode):
                nodes, backbone, dependencies = self.fixture()
                if mode == 'prefix':
                    nodes[1]['FinishActions'][0] = {'Name': 'FinishState', 'Params': {}}
                elif mode == 'async_value':
                    nodes[1]['FinishActions'][-1]['Async'] = 1
                elif mode == 'parallel':
                    nodes[0]['Type'] = 'ParallelSelect'
                elif mode == 'condition':
                    nodes[0]['Condition'] = {'Type': 'Unknown'}
                elif mode == 'prefix_segment':
                    backbone['segments'][-1]['prefix_event_count'] = 1
                else:
                    nodes[1]['ParentNodeId'] = 999
                old = deepcopy(backbone)
                self.assertFalse(repair_dependency_order({}, nodes, backbone, dependencies))
                self.assertEqual(backbone, old)

    def test_crossed_phone_anchor_or_new_dependency_conflict_rejected(self):
        for mode in ('phone', 'dependency'):
            with self.subTest(mode=mode):
                nodes, backbone, dependencies = self.fixture()
                if mode == 'phone':
                    backbone['phone_tip_insertions'] = [{'entry_index': 1}]
                else:
                    dependencies['edges'].append({'from_state': 'flow_1_2', 'to_state': 'flow_1_3'})
                old = deepcopy(backbone)
                self.assertFalse(repair_dependency_order({}, nodes, backbone, dependencies))
                self.assertEqual(backbone, old)

    def test_no_conflict_no_change(self):
        nodes, backbone, dependencies = self.fixture()
        dependencies['recap_dependency_conflicts'] = []
        old = deepcopy(backbone)
        self.assertEqual(repair_dependency_order({}, nodes, backbone, dependencies), [])
        self.assertEqual(backbone, old)

    def test_real_glory_dark_side_pair_and_intermediate_segment(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(125000125)
        backbone = result['recap_backbone']
        keys = [s['state_key'] for s in backbone['segments']]
        prefix = '剧情_2_4_七丘主线_上1_'
        self.assertEqual(keys[30:33], [prefix + '8_2', prefix + '8_3', prefix + '8_1'])
        correction = backbone['dependency_order_corrections']['proofs'][0]
        self.assertEqual(correction['node_id'], 117)
        self.assertEqual(correction['from_positions'], [32])
        self.assertEqual(correction['to_positions'], [30])
        self.assertFalse(any(g['kind'] == 'recap_dependency_conflict' for g in result['batch_coverage']['gaps']))
        self.assertTrue(any(g['kind'] == 'recap_dependency_corrected' for g in result['batch_coverage']['gaps']))


if __name__ == '__main__':
    unittest.main()

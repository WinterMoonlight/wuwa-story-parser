import unittest
from copy import deepcopy
from wuwa_story.dependencies import dependency_report
from wuwa_story.export_task import Exporter
from wuwa_story.reading import reading_text


class DependenciesTests(unittest.TestCase):
    def setUp(self):
        self.inner = {'FlowListName': 'f', 'FlowId': 7, 'StateId': 1}
        self.outer = {'FlowListName': 'f', 'FlowId': 6, 'StateId': 1}
        self.nodes = [
            {'Id': 1, 'Type': 'ParallelSelect', 'Count': 1, 'ParentNodeId': 0},
            {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 1,
             'Condition': {'Type': 'ReachArea', 'Pos': {'X': 1, 'Y': 2, 'Z': 3}, 'Range': 2500},
             'FinishActions': [{'Name': 'PlayFlow', 'Params': self.inner}]},
            {'Id': 3, 'Type': 'AlwaysFalse', 'ParentNodeId': 1},
            {'Id': 4, 'Type': 'ChildQuest', 'ParentNodeId': 3,
             'Condition': {'Type': 'ReachArea', 'Pos': {'X': 1, 'Y': 2, 'Z': 3}, 'Range': 4000},
             'FinishActions': [{'Name': 'PlayFlow', 'Params': self.outer, 'Async': True}]}]

    def test_parallel_radii_do_not_create_temporal_edge(self):
        d = dependency_report({}, self.nodes, ['f_7_1'])
        self.assertEqual(d['separate_state_keys'], ['f_6_1'])
        self.assertEqual(d['edges'], [])
        self.assertEqual(d['parallel_relations'][0]['mandatory'], 'unverified')
        self.assertFalse(d['global_order_verified'])

    def test_recap_reversal_is_an_explicit_conflict(self):
        node = {'Id': 1, 'Type': 'ChildQuest', 'ParentNodeId': 0,
                'Condition': {'Type': 'PlayFlow', 'Flow': self.inner},
                'FinishActions': [{'Name': 'PlayFlow', 'Params': self.outer}]}
        d = dependency_report({}, [node], ['f_6_1', 'f_7_1'])
        self.assertEqual(len(d['recap_dependency_conflicts']), 1)

    def test_ambiguous_recap_source_cannot_establish_dependency_order(self):
        node = {'Id': 1, 'Type': 'ChildQuest', 'ParentNodeId': 0,
                'Condition': {'Type': 'PlayFlow', 'Flow': self.inner},
                'FinishActions': [{'Name': 'PlayFlow', 'Params': self.outer}]}
        for ordered in (['f_6_1', 'f_7_1'], ['f_7_1', 'f_6_1']):
            d = dependency_report({}, [node], ordered, order_source_unique=False)
            self.assertFalse(d['recap_dependency_conflicts'])
            self.assertFalse(d['recap_dependency_consistent'])
            self.assertEqual(d['recap_dependency_unresolved'][0]['reason'], 'ambiguous_recap_order_source')

    def test_real_original_conflict_is_preserved_with_reading_order_correction(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(125000125)
        self.assertFalse(result['batch_coverage']['order']['selected_route_verified'])
        conflicts = result['batch_coverage']['order']['dependencies']['recap_dependency_conflicts']
        self.assertTrue(any(c['node_id'] == 117 for c in conflicts))
        self.assertIn('【顺序修正】', reading_text(result))
        corrections = result['recap_backbone']['dependency_order_corrections']['proofs']
        self.assertEqual(corrections[0]['node_id'], 117)
        self.assertFalse(corrections[0]['runtime_executed'])

    def test_changed_pattern_and_shared_call_not_separated(self):
        for mode in ('center', 'count', 'async', 'shared', 'failure'):
            ns = deepcopy(self.nodes); quest = {}
            if mode == 'center': ns[3]['Condition']['Pos']['X'] = 9
            if mode == 'count': ns[0]['Count'] = 2
            if mode == 'async': ns[3]['FinishActions'][0]['Async'] = False
            if mode == 'shared': quest['Flow'] = self.outer
            if mode == 'failure':
                ns[0]['ParentNodeId'] = 5
                ns.append({'Id': 5, 'Type': 'QuestFailed', 'ParentNodeId': 0})
            self.assertEqual(dependency_report(quest, ns, ['f_7_1'])['separate_state_keys'], [], mode)

    def test_same_node_completion_dependency_is_not_global_order(self):
        node = {'Id': 1, 'Type': 'ChildQuest', 'ParentNodeId': 0,
                'Condition': {'Type': 'PlayFlow', 'Flow': self.inner},
                'FinishActions': [{'Name': 'PlayFlow', 'Params': self.outer, 'Async': True}]}
        d = dependency_report({}, [node], [])
        self.assertEqual(d['edges'][0]['from_event'], 'condition_flow_completed')
        self.assertEqual(d['edges'][0]['to_event'], 'finish_action_invoked')
        self.assertFalse(d['global_order_verified'])

    def test_real_task_keeps_parallel_text_phone_and_missing_key(self):
        r = Exporter(allow_incomplete=True).export(936800000)
        self.assertEqual(len(r['events']), 95)
        detail = r['source']['recap_reference_resolution']['dependencies']
        self.assertEqual(len(detail['parallel_relations']), 1)
        self.assertTrue(any(e['from_state'].endswith('_8_1') and e['to_state'].endswith('_9_1') for e in detail['edges']))
        entry = next(e for e in r['external_content'] if 'parallel_flow' in e)
        self.assertEqual(len(entry['texts']), 1)
        self.assertNotIn(entry['parallel_flow']['state_key'], [s['state_key'] for s in r['source']['scenes']])
        phone = next(e['phone'] for e in r['external_content'] if 'phone' in e)
        self.assertEqual(phone['contacts'][0]['name'], '清宵')
        self.assertTrue(phone['message_bin_data_base64'])
        self.assertNotIn('Flow_936000004_147', r['validation']['missing_text_ids'])
        self.assertFalse(r['validation']['complete_for_supported_task_shape'])
        text = reading_text(r)
        self.assertNotIn('{PlayerName}', text)
        self.assertIn(entry['texts'][0]['text'], text)
        self.assertNotIn('手机消息正文尚未解析', text)
        with self.assertRaises(ValueError): Exporter().export(936800000)


if __name__ == '__main__': unittest.main()

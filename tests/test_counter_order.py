from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.counter_order import counter_sequences, counter_writes, equality_gate


class CounterOrderTests(unittest.TestCase):
    def reference(self):
        return {'Type': 'Int', 'Source': 'Self', 'Name': 'counter'}

    def constant(self, value):
        return {'Type': 'Int', 'Source': 'Constant', 'Value': value}

    def nodes(self):
        return [
            {'Id': 50, 'Type': 'ParallelSelect', 'Count': 0, 'ParentNodeId': 1},
            {'Id': 90, 'Type': 'ChildQuest', 'ParentNodeId': 50, 'FinishActions': [
                {'Name': 'CalculateVar', 'Params': {'Var1': self.reference(),
                 'Var2': self.constant(1), 'Op': 'Add', 'Result': self.reference()}}]},
            *[{'Id': node_id, 'Type': 'ChildQuest', 'ParentNodeId': 50,
               'Condition': {'Type': 'CompareVar', 'Count': 0, 'Conditions': [
                   {'Var1': self.constant(value), 'Var2': self.reference(), 'Compare': 'Eq'}]},
               'FinishActions': [{'Name': 'PlayFlow', 'Async': True,
                   'Params': {'FlowListName': 'test', 'FlowId': 1, 'StateId': value}}]}
              for node_id, value in [(4, 3), (9, 1), (2, 2)]]]

    def collect(self, nodes):
        links = [{'levelplay_id': 8, 'state_key': f'test_1_{i}'} for i in (1, 2, 3)]
        states = {link['state_key']: {} for link in links}
        with patch('wuwa_story.counter_order._flow_segment', side_effect=lambda key, *args:
                   {'state_key': key, 'events': [{'kind': 'dialogue', 'text': key}]}):
            return counter_sequences([{'levelplay_id': 8, 'nodes': nodes}], links,
                                     states, None, set(states))

    def test_thresholds_order_independent_of_ids_and_rows(self):
        original = self.nodes()
        groups = self.collect(list(reversed(original)))
        self.assertEqual(groups[0]['state_keys'], ['test_1_1', 'test_1_2', 'test_1_3'])
        self.assertFalse(groups[0]['proof']['initial_value_assumed'])
        self.assertFalse(groups[0]['proof']['all_thresholds_reached_verified'])
        self.assertFalse(groups[0]['dialogue_completion_order_verified'])
        self.assertFalse(groups[0]['placement_verified'])
        self.assertEqual(original, self.nodes())

    def test_reset_decrement_unknown_writer_and_callbacks_are_rejected(self):
        for mutation in ('reset', 'decrement', 'unknown', 'nested', 'async'):
            nodes = self.nodes()
            action = nodes[1]['FinishActions'][0]
            if mutation == 'reset':
                nodes[1]['FinishActions'].append({'Name': 'SetVar', 'Params': {
                    'VarLeft': self.reference(), 'VarRight': self.constant(0)}})
            elif mutation == 'decrement':
                action['Params']['Var2'] = self.constant(-1)
            elif mutation == 'unknown':
                action['Name'] = 'UnknownWrite'
            elif mutation == 'nested':
                nodes[1]['FinishActions'] = [{'Name': 'If', 'Params': {'Actions': [action]}}]
            else:
                action['Async'] = True
            self.assertEqual(self.collect(nodes), [], mutation)

    def test_malformed_or_global_conditions_are_rejected(self):
        self.assertIsNone(equality_gate({'Type': 'CompareVar', 'Count': 0, 'Conditions': [None]}))
        self.assertIsNone(equality_gate({'Type': 'CompareVar', 'Var1': self.reference(),
                                        'Compare': 'Eq', 'Var2': self.constant(True)}))
        ref = {**self.reference(), 'Source': 'Global'}
        self.assertIsNone(equality_gate({'Type': 'CompareVar', 'Var1': ref,
                                        'Compare': 'Eq', 'Var2': self.constant(1)}))

    def test_duplicate_threshold_and_competing_parallel_are_rejected(self):
        nodes = self.nodes()
        nodes[-1]['Condition'] = deepcopy(nodes[-2]['Condition'])
        self.assertEqual(self.collect(nodes), [])
        nodes = self.nodes()
        nodes[0]['Count'] = 1
        self.assertEqual(self.collect(nodes), [])

    def test_unknown_initial_value_is_preserved(self):
        writes = counter_writes(self.nodes(), 'counter')
        self.assertEqual([write['increment'] for write in writes], [1])

    def test_mianlong_real_counter_and_reading_projection(self):
        from wuwa_story.recap_backbone import export_task_backbone
        from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
        result = export_task_backbone(146000002)
        group = next(item for item in result['batch_coverage']['levelplay_local_sequences']
                     if item.get('order_scope') == 'increasing_counter_invocations')
        self.assertEqual([value['threshold'] for value in group['proof']['thresholds']], [1, 2, 3])
        self.assertEqual([key.rsplit('_', 1)[-1] for key in group['state_keys']], ['9', '4', '13'])
        text = mainline_reading_text(result)
        self.assertLess(text.index('还有两个'), text.index('还剩下最后一个'))
        self.assertLess(text.index('还剩下最后一个'), text.index('岁主应该可以脱困'))
        self.assertEqual(build_mainline_reading(result)['status'], 'ordered_draft_with_gaps')
        self.assertFalse(group['proof']['initial_value_assumed'])


if __name__ == '__main__':
    unittest.main()

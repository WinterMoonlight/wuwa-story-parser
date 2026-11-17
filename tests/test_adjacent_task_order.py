from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.batch import Snapshot
from wuwa_story.reading import reading_text
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.task_local_order import adjacent_task_sequences


class AdjacentTaskOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.states = {r['StateKey']: r for r in cls.source.rows('db_flowState.db', 'flowstate')}

    def nodes(self):
        return [{'Id': 90, 'Type': 'Sequence', 'ParentNodeId': 0},
                {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 90,
                 'Condition': {'Type': 'DoInteract'},
                 'FinishActions': [
                     {'Name': 'PlayFlow', 'Params': {
                         'FlowListName': '剧情_1.2同行插曲支线2', 'FlowId': 1, 'StateId': 1}},
                     {'Name': 'PlayFlow', 'Params': {
                         'FlowListName': '剧情_1.2同行插曲支线2', 'FlowId': 1, 'StateId': 2}}]}]

    def groups(self, nodes, states=None):
        return adjacent_task_sequences({}, nodes, states or self.states, self.source)

    def test_call_array_order_and_sources_are_preserved(self):
        nodes = self.nodes()
        original = deepcopy(nodes)
        groups = self.groups(list(reversed(nodes)))
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual([len(s['events']) for s in group['segments']], [5, 24])
        self.assertEqual(group['order_scope'], 'adjacent_synchronous_finish_calls')
        self.assertFalse(group['mainline_placement_verified'])
        self.assertFalse(group['runtime_executed'])
        self.assertEqual(group['proof']['source_actions'], original[1]['FinishActions'])
        self.assertEqual(nodes, original)
        nodes[1]['FinishActions'].reverse()
        self.assertEqual(self.groups(nodes)[0]['state_keys'], list(reversed(group['state_keys'])))

    def test_async_unknown_gap_and_repeated_calls_are_rejected(self):
        for change in ('async_first', 'async_second', 'interposed', 'third_call', 'metadata'):
            with self.subTest(change=change):
                nodes = self.nodes()
                actions = nodes[1]['FinishActions']
                if change == 'async_first':
                    actions[0]['Async'] = True
                elif change == 'async_second':
                    actions[1]['Async'] = True
                elif change == 'interposed':
                    actions.insert(1, {'Name': 'Unknown', 'Params': {}})
                elif change == 'third_call':
                    actions.append(deepcopy(actions[0]))
                else:
                    actions[0]['Unknown'] = True
                self.assertEqual(self.groups(nodes), [])

    def test_untrusted_ancestors_and_repeated_calls_are_rejected(self):
        for change in ('parallel', 'condition', 'failure', 'cycle', 'missing_parent', 'duplicate_id', 'repeated_call'):
            with self.subTest(change=change):
                nodes = self.nodes()
                if change == 'parallel':
                    nodes[0]['Type'] = 'ParallelSelect'
                elif change == 'condition':
                    nodes[0]['Condition'] = {'Type': 'Unknown'}
                elif change == 'failure':
                    nodes[1]['FailedCondition'] = {'Type': 'Unknown'}
                elif change == 'cycle':
                    nodes[0]['ParentNodeId'] = 2
                elif change == 'missing_parent':
                    nodes[1]['ParentNodeId'] = 999
                elif change == 'duplicate_id':
                    nodes.append(deepcopy(nodes[1]))
                else:
                    nodes.append({**deepcopy(nodes[1]), 'Id': 3})
                self.assertEqual(self.groups(nodes), [])

    def test_decode_failure_or_missing_definition_does_not_leak_prefix(self):
        states = dict(self.states)
        del states['剧情_1.2同行插曲支线2_1_2']
        self.assertEqual(self.groups(self.nodes(), states), [])
        with patch('wuwa_story.task_local_order.flow_actions', side_effect=ValueError('invalid')):
            self.assertEqual(self.groups(self.nodes()), [])

    def test_parallel_context_preserves_local_order_without_selecting_a_branch(self):
        for count in (0, 1, 2):
            nodes = self.nodes()
            nodes[0].update(Type='ParallelSelect', Count=count)
            original = deepcopy(nodes)
            group = self.groups(nodes)[0]
            self.assertEqual(len(group['segments']), 2)
            self.assertEqual(group['proof']['parallel_ancestors'], [original[0]])
            self.assertFalse(group['proof']['cross_branch_order_verified'])
            self.assertFalse(group['runtime_executed'])
            self.assertEqual(nodes, original)
        for count in (-1, True, '1'):
            nodes = self.nodes()
            nodes[0].update(Type='ParallelSelect', Count=count)
            self.assertEqual(self.groups(nodes), [])

    def test_long_chain_is_merged_once(self):
        nodes = self.nodes()
        nodes[1]['FinishActions'].append({'Name': 'PlayFlow', 'Params': {
            'FlowListName': '剧情_1_1_乘宵山主线_岩壁遗迹', 'FlowId': 10, 'StateId': 1}})
        groups = self.groups(nodes)
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual([len(s['events']) for s in group['segments']], [5, 24, 12])
        self.assertEqual(group['proof']['action_indices'], [0, 1, 2])
        self.assertEqual(len(group['proof']['run_dependencies']), 2)
        self.assertEqual(group['proof']['to_state'], group['state_keys'][-1])
        self.assertEqual(group['proof']['source_actions'], nodes[1]['FinishActions'])

    def test_world_action_splits_two_runs_without_linking_them(self):
        nodes = self.nodes()
        nodes[1]['FinishActions'].extend([
            {'Name': 'Unknown', 'Params': {}},
            {'Name': 'PlayFlow', 'Params': {
                'FlowListName': '剧情_1_1_乘宵山主线_岩壁遗迹', 'FlowId': 1, 'StateId': 1}},
            {'Name': 'PlayFlow', 'Params': {
                'FlowListName': '剧情_1_1_乘宵山主线_岩壁遗迹', 'FlowId': 10, 'StateId': 1}}])
        groups = self.groups(nodes)
        self.assertEqual(len(groups), 2)
        self.assertEqual([g['proof']['action_indices'] for g in groups], [[0, 1], [3, 4]])
        self.assertEqual(groups[0]['proof']['following_actions'][0]['Name'], 'Unknown')
        self.assertEqual(groups[1]['proof']['preceding_actions'][-1]['Name'], 'Unknown')
        self.assertTrue(all(not g['mainline_placement_verified'] for g in groups))

    def test_real_parallel_task_restores_two_more_call_sequences(self):
        result = export_task_backbone(121700004)
        groups = {g['node_id']: g for g in result['task_local_sequences']
                  if g['order_scope'] == 'adjacent_synchronous_finish_calls'}
        self.assertEqual(set(groups), {5, 28, 71, 76})
        self.assertEqual(sum(len(s['events']) for s in groups[5]['segments']), 61)
        self.assertEqual(sum(len(s['events']) for s in groups[76]['segments']), 33)
        self.assertEqual(groups[5]['proof']['action_indices'], [4, 5])
        self.assertEqual(groups[76]['proof']['action_indices'], [10, 11])
        self.assertTrue(groups[5]['proof']['parallel_ancestors'])
        self.assertFalse(groups[5]['proof']['cross_branch_order_verified'])
        self.assertNotIn('剧情_2_0_黎那汐塔主线_第三幕上_帕尔米罗_4_27', groups[5]['state_keys'])
        text = reading_text(result)
        self.assertEqual(text.count('【条件片段】'), 2)
        self.assertIn('小姑娘', text)
        self.assertNotIn('{Male=', text)
        self.assertFalse(result['batch_coverage']['order']['selected_route_verified'])

    def test_no_recap_task_retains_choices_and_displays_each_event_once(self):
        result = export_task_backbone(32750022)
        self.assertNotIn('recap_backbone', result)
        all_groups = result['task_local_sequences']
        groups = [group for group in all_groups if group['order_scope'] == 'adjacent_synchronous_finish_calls']
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(sum(len(s['events']) for s in group['segments']), 29)
        self.assertTrue(any(s['route']['choices'] for s in group['segments']))
        records = result['batch_coverage']['records']
        local = [r for r in records if r.get('order_scope') == group['order_scope']]
        self.assertEqual(len(local), 29)
        self.assertTrue(all(not r['order_verified'] and r['local_order_verified'] for r in local))
        selected = {(s['state_key'], e.get('text_id')) for s in group['segments'] for e in s['events']}
        self.assertFalse(any((r.get('origin'), r.get('text_id')) in selected for r in records))
        text = reading_text(result)
        self.assertEqual(text.count('【局部有序对白】'), len(all_groups))
        first = group['segments'][0]['events'][0]['text']
        last = group['segments'][1]['events'][-1]['text']
        self.assertEqual(text.count(first), 1)
        self.assertEqual(text.count(last), 1)
        self.assertLess(text.index(first), text.index(last))
        self.assertEqual(result['batch_coverage']['status'], 'inventory_only')
        self.assertFalse(result['batch_coverage']['text_order_review']['whole_task_text_order_verified'])

    def test_media_placeholder_preserves_subsequent_dialogue(self):
        result = export_task_backbone(133000009)
        group = result['task_local_sequences'][0]
        self.assertEqual(group['segments'][0]['events'][0]['kind'], 'unparsed_content')
        self.assertEqual(len(group['segments'][1]['events']), 12)
        self.assertFalse(group['mainline_placement_verified'])
        records = [r for r in result['batch_coverage']['records']
                   if r.get('order_scope') == 'adjacent_synchronous_finish_calls']
        self.assertEqual(sum(r['is_placeholder'] for r in records), 1)
        self.assertEqual(sum(not r['is_placeholder'] for r in records), 12)
        text = reading_text(result)
        self.assertLess(text.index('演出'), text.index('石门上有星辰流光跃动'))
        self.assertEqual(text.count('……石门上有星辰流光跃动，是「曜纹」。'), 1)


if __name__ == '__main__':
    unittest.main()

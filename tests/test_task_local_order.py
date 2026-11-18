from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.batch import Snapshot
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.task_local_order import (
    bridge_actions_valid, connect_condition_followups, local_task_sequences, independent_task_sequences,
)
from wuwa_story.reading import reading_text


class TaskLocalOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.states = {r['StateKey']: r for r in cls.source.rows('db_flowState.db', 'flowstate')}
        cls.first = '剧情_2_0_黎那汐塔主线_第一幕_11_1'
        cls.second = '剧情_2_0_黎那汐塔主线_第一幕_12_1'

    def nodes(self):
        return [{'Type': 'Sequence', 'Id': 90, 'ParentNodeId': 0},
                {'Type': 'ChildQuest', 'Id': 2, 'ParentNodeId': 90,
                 'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': '剧情_2_0_黎那汐塔主线_第一幕', 'FlowId': 11, 'StateId': 1}},
                 'FinishActions': [{'Name': 'UnlockTeleportTrigger', 'Params': {'TeleportId': 1}},
                                   {'Name': 'PlayFlow', 'Params': {'FlowListName': '剧情_2_0_黎那汐塔主线_第一幕', 'FlowId': 12, 'StateId': 1}}]}]

    def test_explicit_relation_preserves_sources_and_ignores_node_storage_order(self):
        nodes = self.nodes()
        original = deepcopy(nodes)
        groups = local_task_sequences({}, list(reversed(nodes)), {'segments': []}, self.states, self.source)
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group['state_keys'], [self.first, self.second])
        self.assertEqual([len(s['events']) for s in group['segments']], [18, 22])
        self.assertTrue(group['local_order_verified'])
        self.assertFalse(group['mainline_placement_verified'])
        self.assertFalse(group['proof']['intermediate_callback_content_verified'])
        self.assertEqual(nodes, original)

    def test_async_repeated_or_untrusted_paths_are_rejected(self):
        for change in ('async', 'condition', 'parallel', 'cycle', 'repeated', 'bridge', 'second_call', 'missing'):
            nodes = self.nodes()
            node = nodes[1]
            states = self.states
            if change == 'async': node['FinishActions'][1]['Async'] = True
            elif change == 'condition': node['ExitCondition'] = {'Type': 'Other'}
            elif change == 'parallel': nodes[0]['Type'] = 'ParallelSelect'
            elif change == 'cycle': nodes[0]['ParentNodeId'] = 2
            elif change == 'repeated': nodes.append({**deepcopy(node), 'Id': 3})
            elif change == 'bridge': node['FinishActions'][0] = {'Name': 'SetVar', 'Params': {}}
            elif change == 'second_call': node['FinishActions'].append(deepcopy(node['FinishActions'][1]))
            else: states = {key: value for key, value in self.states.items() if key != self.second}
            self.assertEqual(local_task_sequences({}, nodes, {'segments': []}, states, self.source), [], change)

    def test_existing_recap_anchor_and_decode_failure_are_not_reclassified(self):
        self.assertEqual(local_task_sequences({}, self.nodes(), {'segments': [{'state_key': self.first}]}, self.states, self.source), [])
        with patch('wuwa_story.task_local_order.flow_actions', side_effect=ValueError('ambiguous')):
            self.assertEqual(local_task_sequences({}, self.nodes(), {'segments': []}, self.states, self.source), [])

    def test_bridge_shape_validation(self):
        good = [{'Name': 'ChangeEntityState', 'Params': {'Type': 'Directly', 'EntityId': 1, 'State': 'active'}}]
        self.assertTrue(bridge_actions_valid(good))
        for actions in ([None], [{'Name': 'UnlockTeleportTrigger', 'Params': {'TeleportId': True}}],
                        [{**good[0], 'Async': True}], [{'Name': 'Unknown', 'Params': {}}]):
            self.assertFalse(bridge_actions_valid(actions))

    def test_parallel_condition_completion_precedes_async_followup(self):
        nodes = self.nodes()
        nodes.insert(1, {'Type': 'ParallelSelect', 'Id': 91, 'ParentNodeId': 90, 'Count': 1})
        nodes[2]['ParentNodeId'] = 91
        nodes[2]['FinishActions'][1]['Async'] = True
        original = deepcopy(nodes)
        groups = local_task_sequences({}, nodes, {'segments': []}, self.states, self.source,
                                      allow_parallel_async=True)
        self.assertEqual(groups[0]['state_keys'], [self.first, self.second])
        self.assertEqual(groups[0]['order_scope'], 'condition_completion_to_async_call')
        self.assertTrue(groups[0]['proof']['invocation_async'])
        self.assertFalse(groups[0]['proof']['cross_branch_order_verified'])
        self.assertFalse(groups[0]['proof']['followup_completion_order_verified'])
        self.assertEqual(groups[0]['proof']['parallel_ancestors'][0]['Id'], 91)
        self.assertEqual(nodes, original)
        nodes[1]['Count'] = 'unknown'
        self.assertEqual(local_task_sequences({}, nodes, {'segments': []}, self.states, self.source,
                                             allow_parallel_async=True), [])

    def test_join_reuses_segments_and_is_idempotent(self):
        nodes = self.nodes()
        nodes[1]['FinishActions'][1]['Async'] = True
        segment_a = {'state_key': self.first, 'events': [{'kind': 'dialogue', 'text': '前文'}]}
        segment_b = {'state_key': self.second, 'events': [{'kind': 'dialogue', 'text': '后文'}]}
        old = [{'node_id': 2, 'state_keys': [self.second], 'segments': [segment_b]},
               {'node_id': 2, 'state_keys': [self.first], 'segments': [segment_a]}]
        original = deepcopy(old)
        groups = connect_condition_followups({}, nodes, self.states, self.source, old)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['state_keys'], [self.first, self.second])
        self.assertEqual(groups[0]['segments'], [segment_a, segment_b])
        self.assertEqual(old, original)
        self.assertEqual(connect_condition_followups({}, nodes, self.states, self.source, groups), groups)

    def test_join_rejects_unknown_bridge_and_overlapping_later_chain(self):
        nodes = self.nodes()
        nodes[1]['FinishActions'][0] = {'Name': 'SetVar', 'Params': {}}
        old = [{'node_id': 2, 'state_keys': [self.first], 'segments': []}]
        self.assertEqual(connect_condition_followups({}, nodes, self.states, self.source, old), old)
        nodes = self.nodes()
        old = [{'node_id': 2, 'state_keys': [self.first, 'unrelated'], 'segments': []}]
        self.assertEqual(connect_condition_followups({}, nodes, self.states, self.source, old), old)

    def test_async_followup_rejects_invalid_flag_disabled_call_and_corrupt_flow(self):
        for mode in ('invalid_flag', 'disabled', 'corrupt'):
            with self.subTest(mode=mode):
                nodes = self.nodes()
                states = self.states
                if mode == 'invalid_flag':
                    nodes[1]['FinishActions'][1]['Async'] = 1
                elif mode == 'disabled':
                    nodes[1]['FinishActions'][1]['Disabled'] = True
                else:
                    states = {**states, self.second: {'BinData': b'x'}}
                self.assertEqual(local_task_sequences({}, nodes, {'segments': []}, states, self.source,
                                                     allow_parallel_async=True), [])

    def test_real_departure_joins_six_lines_without_global_order_claim(self):
        from wuwa_story.mainline_reading import mainline_reading_text
        result = export_task_backbone(125000121)
        group = next(g for g in result['task_local_sequences'] if g['node_id'] == 150)
        self.assertEqual(group['state_keys'], ['剧情_1_1_乘宵山主线_6_13', '剧情_1_1_乘宵山主线_6_9'])
        self.assertEqual([len(s['events']) for s in group['segments']], [4, 2])
        self.assertFalse(group['mainline_placement_verified'])
        text = mainline_reading_text(result)
        self.assertEqual(text.count('这些残星会的人遭到了什么人的反击'), 1)
        self.assertEqual(text.count('长离，这里有印记'), 1)
        self.assertLess(text.index('可她这么做'), text.index('长离，这里有印记'))
        between = text[text.index('可她这么做'):text.index('长离，这里有印记')]
        self.assertNotIn('【局部剧情片段】', between)

    def test_independent_call_in_complex_task_keeps_scope(self):
        nodes = [{'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence'},
                 {'Id': 7, 'ParentNodeId': 1, 'Type': 'ParallelSelect', 'Count': 0},
                 {'Id': 9, 'ParentNodeId': 7, 'Type': 'Action', 'Actions': [
                     {'Name': 'UnknownVisualEffect', 'Params': {}},
                     {'Name': 'PlayFlow', 'Async': True, 'Params': {
                         'FlowListName': '剧情_2_0_黎那汐塔主线_第一幕', 'FlowId': 11, 'StateId': 1}}]}]
        groups = independent_task_sequences({}, list(reversed(nodes)), self.states, self.source)
        self.assertEqual(groups[0]['state_keys'], [self.first])
        self.assertTrue(groups[0]['proof']['invocation_async'])
        self.assertFalse(groups[0]['mainline_placement_verified'])
        self.assertEqual(len(groups[0]['segments'][0]['events']), 18)
        self.assertEqual(independent_task_sequences({}, nodes, self.states, self.source, groups), [])
        nodes.append({**deepcopy(nodes[-1]), 'Id': 10})
        self.assertEqual(independent_task_sequences({}, nodes, self.states, self.source), [])

    def test_real_task_groups_text_without_double_display_or_false_anchor(self):
        result = export_task_backbone(114000027)
        groups = result['recap_backbone']['task_local_sequences']
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group['node_id'], 24)
        self.assertEqual(group['state_keys'], [self.first, self.second])
        text = reading_text(result)
        self.assertEqual(text.count('【局部有序对白】'), 1)
        for line in ('哇……那些，全都是声骸吗？', '这上面写的是什么意思？救赎来自起源……？'):
            self.assertEqual(text.count(line), 1)
        records = result['batch_coverage']['records']
        self.assertEqual(sum(r.get('order_scope') == 'same_node_condition_to_finish' for r in records), 40)
        self.assertFalse(any(r.get('origin') in {self.first, self.second} and r.get('text_id') in {
            event['text_id'] for segment in group['segments'] for event in segment['events']} for r in records))
        self.assertFalse(group['mainline_placement_verified'])

    def test_multiple_direct_calls_are_recovered_separately(self):
        first = {'Name': 'PlayFlow', 'Params': {'FlowListName': '剧情_2_0_黎那汐塔主线_第一幕',
                 'FlowId': 11, 'StateId': 1}, 'Async': True}
        second = {**deepcopy(first), 'Params': {**first['Params'], 'FlowId': 12}}
        nodes = [{'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence'},
                 {'Id': 2, 'ParentNodeId': 1, 'Type': 'ChildQuest',
                  'Condition': {'Type': 'ReachArea'}, 'EnterActions': [first], 'FinishActions': [second]}]
        original = deepcopy(nodes)
        groups = independent_task_sequences({}, nodes, self.states, self.source)
        self.assertEqual([g['state_keys'] for g in groups], [[self.first], [self.second]])
        self.assertEqual([g['proof']['phase'] for g in groups], ['EnterActions', 'FinishActions'])
        self.assertTrue(all(g['proof']['multiple_direct_calls'] for g in groups))
        self.assertTrue(all(not g['proof']['inter_group_order_verified'] for g in groups))
        self.assertEqual(nodes, original)
        remaining = independent_task_sequences({}, nodes, self.states, self.source, groups[:1])
        self.assertEqual([g['state_keys'] for g in remaining], [[self.second]])
        nodes[1]['FinishActions'][0]['Async'] = 1
        self.assertEqual([g['state_keys'] for g in independent_task_sequences({}, nodes, self.states, self.source)],
                         [[self.first]])

    def information_nodes(self):
        nodes = self.nodes()
        nodes[1]['FinishActions'][0] = {'Name': 'OpenSystemBoard',
            'Params': {'SystemType': 'InformationView', 'BoardId': 120101006}}
        return nodes

    def test_information_bridge_uses_real_board_between_unchanged_flows(self):
        nodes = self.information_nodes()
        original = deepcopy(nodes)
        self.assertEqual(local_task_sequences({}, nodes, {'segments': []}, self.states, self.source), [])
        groups = local_task_sequences({}, nodes, {'segments': []}, self.states, self.source,
                                      allow_information_bridge=True)
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group['order_scope'], 'condition_completion_via_information_board')
        self.assertEqual(group['state_keys'], [self.first, self.second])
        between = group['intermediate_content'][0]
        self.assertEqual(between['before_segment_index'], 1)
        event = between['events'][0]
        self.assertIsNone(event['state_key'])
        self.assertIn('小满的心愿纸条', event['text'])
        self.assertEqual(event['information_board']['board_id'], 120101006)
        self.assertFalse(group['proof']['panel_close_timing_verified'])
        self.assertFalse(group['mainline_placement_verified'])
        self.assertEqual(nodes, original)

    def test_information_bridge_rejects_untrusted_or_incomplete_panel(self):
        for mode in ('async', 'disabled', 'missing_board', 'invalid_id', 'unknown_action', 'extra_params'):
            with self.subTest(mode=mode):
                nodes = self.information_nodes()
                action = nodes[1]['FinishActions'][0]
                if mode == 'async': action['Async'] = True
                elif mode == 'disabled': action['Disabled'] = True
                elif mode == 'missing_board': action['Params']['BoardId'] = 999999999
                elif mode == 'invalid_id': action['Params']['BoardId'] = True
                elif mode == 'unknown_action': action['Name'] = 'Unknown'
                else: action['Params']['Extra'] = True
                self.assertEqual(local_task_sequences({}, nodes, {'segments': []}, self.states, self.source,
                                                     allow_information_bridge=True), [])
        with patch('wuwa_story.information_boards.inspect_information', side_effect=ValueError('bad row')):
            self.assertEqual(local_task_sequences({}, self.information_nodes(), {'segments': []},
                self.states, self.source, allow_information_bridge=True), [])

    def test_information_bridge_combines_once_and_preserves_original_segments(self):
        nodes = self.information_nodes()
        first = {'state_key': self.first, 'events': [{'kind': 'dialogue', 'text': 'before'}]}
        second = {'state_key': self.second, 'events': [{'kind': 'dialogue', 'text': 'after'}]}
        old = [{'node_id': 2, 'state_keys': [self.second], 'segments': [second]},
               {'node_id': 2, 'state_keys': [self.first], 'segments': [first]}]
        result = connect_condition_followups({}, nodes, self.states, self.source, old)
        self.assertEqual(result[0]['segments'], [first, second])
        self.assertEqual(len(result[0]['intermediate_content']), 1)
        self.assertEqual(connect_condition_followups({}, nodes, self.states, self.source, result), result)

    def test_real_third_wish_places_note_between_dialogue_and_narration(self):
        from wuwa_story.mainline_reading import build_mainline_reading, mainline_reading_text
        result = export_task_backbone(880000025)
        group = next(g for g in result['task_local_sequences'] if g['node_id'] == 26)
        self.assertEqual(group['state_keys'], ['剧情_V1.2追月节主线明线_10_10', '剧情_V1.2追月节主线明线_32_1'])
        self.assertEqual(len(group['intermediate_content']), 1)
        text = mainline_reading_text(result)
        self.assertEqual(text.count('小满的心愿纸条'), 1)
        self.assertLess(text.index('第三张心愿纸'), text.index('小满的心愿纸条'))
        self.assertLess(text.index('小满的心愿纸条'), text.index('在你思考关于'))
        self.assertEqual(build_mainline_reading(result)['status'], 'ordered_draft_with_gaps')
        external_records = [r for r in result['batch_coverage']['records']
                            if r.get('pointer', '').startswith('/external_content/0/texts/')]
        self.assertEqual(len(external_records), 2)
        self.assertTrue(all(r.get('counted_elsewhere') and r.get('text_duplicate_of') for r in external_records))
        self.assertEqual(result['external_content'][0]['information_board'],
                         group['intermediate_content'][0]['events'][0]['information_board'])

    def test_repeated_calls_and_disabled_ancestors_do_not_duplicate_text(self):
        call = {'Name': 'PlayFlow', 'Params': {'FlowListName': '剧情_2_0_黎那汐塔主线_第一幕',
                'FlowId': 11, 'StateId': 1}}
        nodes = [{'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence'},
                 {'Id': 2, 'ParentNodeId': 1, 'Type': 'ChildQuest',
                  'EnterActions': [call], 'FinishActions': [deepcopy(call)]}]
        self.assertEqual(independent_task_sequences({}, nodes, self.states, self.source), [])
        nodes[1]['FinishActions'] = []
        nodes[0]['Type'] = 'AlwaysFalse'
        self.assertEqual(independent_task_sequences({}, nodes, self.states, self.source), [])

    def test_real_departure_recovers_waterfall_and_barrier_calls_without_joining_pool(self):
        from wuwa_story.mainline_reading import mainline_reading_text
        result = export_task_backbone(125000121)
        groups = [g for g in result['task_local_sequences'] if g['node_id'] == 35]
        self.assertEqual([g['state_keys'] for g in groups],
                         [['剧情_1_1_乘宵山主线_6_11'], ['剧情_1_1_乘宵山主线_6_12']])
        self.assertEqual([len(g['segments'][0]['events']) for g in groups], [2, 2])
        text = mainline_reading_text(result)
        self.assertEqual(text.count('瀑布后面，有东西'), 1)
        self.assertEqual(text.count('这里也有「绝缘光幕」'), 1)
        self.assertIn('进入步骤时调用的局部对白', text)
        self.assertIn('完成步骤时调用的局部对白', text)
        pair = next(g for g in result['task_local_sequences'] if g['node_id'] == 150)
        self.assertEqual(len(pair['segments']), 2)
        relation = next(r for r in result['sequence_dependency_review']['flow_progression']['phase_relations']
                        if r['node_id'] == 35)
        self.assertTrue(relation['invocation_order_verified'])
        self.assertFalse(relation['flow_completion_before_followup_verified'])
        self.assertFalse(relation['whole_task_order_verified'])
        self.assertTrue(any(g['kind'] == 'recap_dependency_unresolved' for g in result['batch_coverage']['gaps']))


if __name__ == '__main__':
    unittest.main()

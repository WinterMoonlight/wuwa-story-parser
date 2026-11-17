from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from wuwa_story.recap_order import anchored_finish_flows
from wuwa_story.tip_finish_flow import insert_tip_finish_flows


class TipFinishFlowTests(unittest.TestCase):
    def fixture(self):
        ref = {'FlowListName': 'tip_flow', 'FlowId': 2, 'StateId': 1}
        call = {'Name': 'PlayFlow', 'Params': ref}
        nodes = [{'Id': 10, 'ParentNodeId': 0, 'Type': 'Sequence'},
                 {'Id': 20, 'ParentNodeId': 10, 'Type': 'Sequence'},
                 {'Id': 3, 'ParentNodeId': 20, 'Type': 'ChildQuest', 'TidTip': 'unique',
                  'Condition': {'Type': 'ReachArea', 'Pos': {'X': 0, 'Y': 1, 'Z': 2}, 'Range': 30},
                  'FinishActions': [call, {'Name': 'DestroyEntity', 'Params': {'EntityIds': [22]}}]}]
        entries = [{'Flow': {'FlowListName': 'previous', 'FlowId': 1, 'StateId': 1}},
                   {'TidTip': 'unique'}, {'TidTip': 'next'},
                   {'Flow': {'FlowListName': 'next', 'FlowId': 3, 'StateId': 1}}]
        backbone = {'order_source': {'entries': entries}, 'parsed_segments': 2,
                    'blocked_segments': 0,
                    'segments': [{'state_key': 'previous_1_1', 'entry_index': 0, 'events': [], 'status': 'parsed'},
                                 {'state_key': 'next_3_1', 'entry_index': 3, 'events': [], 'status': 'parsed'}],
                    'task_only_review': [{'state_key': 'tip_flow_2_1', 'placement_verified': False}]}
        return nodes, backbone

    def parsed(self):
        return {'state_key': 'tip_flow_2_1', 'events': [{'kind': 'dialogue', 'text': '正文'}],
                'route': {'choices': []}, 'source_actions': [], 'action_fields': [1],
                'sha256': 'hash', 'unverified_content': [], 'missing_text_ids': []}

    def test_nested_sequence_exact_tip_and_position(self):
        nodes, backbone = self.fixture()
        before = deepcopy((nodes, backbone['order_source']))
        self.assertEqual(anchored_finish_flows({}, nodes, backbone['order_source']['entries'])[1], [])
        _, proofs = anchored_finish_flows({}, nodes, backbone['order_source']['entries'], allow_nested=True)
        self.assertEqual(proofs[0]['recap_entry_index'], 1)
        self.assertEqual(proofs[0]['ancestor_ids'], [20, 10])
        self.assertEqual((nodes, backbone['order_source']), before)
        with patch('wuwa_story.tip_finish_flow._flow_segment', return_value=self.parsed()):
            inserted = insert_tip_finish_flows({}, nodes, backbone, {'tip_flow_2_1': {}}, None)
        self.assertEqual(len(inserted), 1)
        self.assertEqual([s['state_key'] for s in backbone['segments']], ['previous_1_1', 'tip_flow_2_1', 'next_3_1'])
        self.assertEqual(backbone['parsed_segments'], 3)
        self.assertEqual(backbone['segments'][1]['source_entry'], {'TidTip': 'unique'})
        self.assertFalse(inserted[0]['runtime_verified'])
        with patch('wuwa_story.tip_finish_flow._flow_segment') as parser:
            self.assertEqual(insert_tip_finish_flows({}, nodes, backbone, {'tip_flow_2_1': {}}, None), [])
            parser.assert_not_called()

    def test_ambiguous_populated_or_shared_tip_rejected(self):
        for mode in ('duplicate_tip', 'populated', 'shared_tip', 'shared_flow'):
            with self.subTest(mode=mode):
                nodes, backbone = self.fixture()
                entries = backbone['order_source']['entries']
                quest = {}
                if mode == 'duplicate_tip':
                    entries.append({'TidTip': 'unique'})
                elif mode == 'populated':
                    entries.insert(2, {'Flow': {'FlowListName': 'extra', 'FlowId': 7, 'StateId': 1}})
                elif mode == 'shared_tip':
                    nodes.append({'Id': 4, 'ParentNodeId': 20, 'Type': 'ChildQuest', 'TidTip': 'unique'})
                else:
                    quest['Flow'] = nodes[-1]['FinishActions'][0]['Params']
                self.assertEqual(anchored_finish_flows(quest, nodes, entries, allow_nested=True)[1], [])

    def test_parallel_conditional_broken_or_duplicate_ancestry_rejected(self):
        for mode in ('parallel', 'conditional', 'broken', 'duplicate', 'cyclic'):
            with self.subTest(mode=mode):
                nodes, backbone = self.fixture()
                if mode == 'parallel':
                    nodes[1].update(Type='ParallelSelect', Count=1)
                elif mode == 'conditional':
                    nodes[1]['Condition'] = {'Type': 'Unknown'}
                elif mode == 'broken':
                    nodes[1]['ParentNodeId'] = 999
                elif mode == 'cyclic':
                    nodes[1]['ParentNodeId'] = 3
                else:
                    nodes.append(deepcopy(nodes[1]))
                self.assertFalse(anchored_finish_flows({}, nodes, backbone['order_source']['entries'], allow_nested=True)[1])

    def test_async_preceding_action_invalid_range_or_multiple_calls_rejected(self):
        for mode in ('async', 'prefix', 'multiple', 'range'):
            with self.subTest(mode=mode):
                nodes, backbone = self.fixture()
                node = nodes[-1]
                if mode == 'async':
                    node['FinishActions'][0]['Async'] = True
                elif mode == 'prefix':
                    node['FinishActions'].insert(0, {'Name': 'Wait', 'Params': {'Time': 1}})
                elif mode == 'multiple':
                    node['FinishActions'].append(deepcopy(node['FinishActions'][0]))
                else:
                    node['Condition']['Range'] = float('nan')
                self.assertFalse(anchored_finish_flows({}, nodes, backbone['order_source']['entries'], allow_nested=True)[1])

    def test_failed_missing_text_or_unresolved_control_does_not_change_backbone(self):
        for mode in ('failure', 'missing', 'control', 'unverified'):
            with self.subTest(mode=mode):
                nodes, backbone = self.fixture()
                parsed = self.parsed()
                if mode == 'failure':
                    parsed = None
                elif mode == 'missing':
                    parsed['missing_text_ids'] = ['missing']
                elif mode == 'control':
                    parsed['events'].append({'kind': 'recap_gap'})
                else:
                    parsed['unverified_content'] = [{'kind': 'unknown'}]
                original = deepcopy(backbone)
                with patch('wuwa_story.tip_finish_flow._flow_segment', return_value=parsed):
                    self.assertFalse(insert_tip_finish_flows({}, nodes, backbone, {'tip_flow_2_1': {}}, None))
                self.assertEqual(backbone, original)

    def interaction(self):
        condition = {'Type': 0, 'Conditions': [{'Type': 'CheckChildQuestFinished', 'QuestId': 99,
                                              'ChildQuestId': 3, 'Compare': 'Eq'}]}
        return {'state_key': 'previous_1_1', 'component': 'InteractComponent', 'entity_id': 22,
                'map_id': 9, 'source_component': {'Options': [{'Condition': condition,
                    'Type': {'Type': 'Flow', 'Flow': {'FlowListName': 'previous', 'FlowId': 1, 'StateId': 1}}}]}}

    def test_completion_gate_precedes_interaction_despite_later_tip(self):
        nodes, backbone = self.fixture()
        nodes[-1]['TrackTarget'] = {'TrackType': {'Type': 'Entities', 'EntityIds': [22]}}
        source = SimpleNamespace(rows=lambda *args: [{'Id': 9, 'MapConfigId': 9}])
        with patch('wuwa_story.tip_finish_flow.declared_entity_content', return_value=([self.interaction()], [])), \
                patch('wuwa_story.tip_finish_flow._flow_segment', return_value=self.parsed()):
            inserted = insert_tip_finish_flows({'Id': 99, 'DungeonId': 9}, nodes, backbone,
                                              {'tip_flow_2_1': {}}, source)
        self.assertEqual([s['state_key'] for s in backbone['segments']], ['tip_flow_2_1', 'previous_1_1', 'next_3_1'])
        self.assertEqual(inserted[0]['recap_entry_index'], 0)
        self.assertEqual(inserted[0]['tip_entry_index'], 1)
        self.assertEqual(inserted[0]['before_state'], 'previous_1_1')
        self.assertEqual(backbone['segments'][0]['source_entry'], {'TidTip': 'unique'})

    def test_ambiguous_completion_gate_does_not_fall_back_to_later_tip(self):
        for mode in ('wrong_map', 'wrong_entity', 'negated', 'multiple_options', 'compound', 'duplicate_anchor'):
            with self.subTest(mode=mode):
                nodes, backbone = self.fixture()
                nodes[-1]['TrackTarget'] = {'TrackType': {'Type': 'Entities', 'EntityIds': [22]}}
                link = self.interaction()
                option = link['source_component']['Options'][0]
                if mode == 'wrong_map':
                    link['map_id'] = 8
                elif mode == 'wrong_entity':
                    link['entity_id'] = 23
                elif mode == 'negated':
                    option['Condition']['Conditions'][0]['Compare'] = 'Ne'
                elif mode == 'multiple_options':
                    link['source_component']['Options'].append(deepcopy(option))
                elif mode == 'compound':
                    option['Condition']['Conditions'].append({'Type': 'Unknown'})
                else:
                    backbone['segments'].append(deepcopy(backbone['segments'][0]))
                source = SimpleNamespace(rows=lambda *args: [{'Id': 9, 'MapConfigId': 9}])
                old = deepcopy(backbone)
                with patch('wuwa_story.tip_finish_flow.declared_entity_content', return_value=([link], [])):
                    self.assertFalse(insert_tip_finish_flows({'Id': 99, 'DungeonId': 9}, nodes, backbone,
                                                            {'tip_flow_2_1': {}}, source))
                self.assertEqual(backbone, old)

    def test_real_linnae_epilogue_default_and_alternative(self):
        from wuwa_story.recap_backbone import export_task_backbone
        key = '剧情_3_0_主线_拉海洛主线_上半_1_27_1'
        normal = export_task_backbone(915000004)
        chosen = export_task_backbone(915000004, {key + ':8': 1, key + ':11': 1})
        for result in (normal, chosen):
            backbone = result['recap_backbone']
            segment = next(s for s in backbone['segments'] if s['state_key'] == key)
            self.assertEqual(segment['entry_index'], 44)
            self.assertEqual(segment['placement_proof']['tip_entry_index'], 45)
            self.assertEqual(segment['order_origin'], 'task_finish_before_interaction')
            self.assertEqual(backbone['segments'][-2]['state_key'], key)
            self.assertEqual(len(segment['events']), 23)
            self.assertEqual(segment['events'][0]['display_name'], '琳奈')
            self.assertEqual(segment['events'][0]['text'], '你来啦！')
            self.assertEqual(segment['events'][-1]['text'], '从现在开始的，就是属于琳奈的人生！')
            selected_ids = {e['text_id'] for e in segment['events']}
            leftovers = [r for r in result['batch_coverage']['records'] if r.get('origin') == key]
            self.assertTrue(all(r['text_id'] not in selected_ids for r in leftovers))
        self.assertNotEqual(normal['recap_backbone']['segments'][-2]['route']['choices'][3]['selected_index'],
                            chosen['recap_backbone']['segments'][-2]['route']['choices'][3]['selected_index'])


if __name__ == '__main__':
    unittest.main()

import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.sync_prefix import bridge_action, insert_qte_prefix, insert_sync_dialogue_prefix


class SyncPrefixTests(unittest.TestCase):
    def dialogue_fixture(self):
        calls = [{'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 1, 'StateId': i}}
                 for i in (1, 2)]
        nodes = [{'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 2, 'Type': 'Action', 'ParentNodeId': 1, 'Actions': calls}]
        review = {'state_key': 'f_1_1', 'owner_nodes': [nodes[1]], 'placement_verified': False}
        backbone = {'segments': [{'state_key': 'f_1_2', 'status': 'parsed',
                                  'events': [{'text': '后文'}]}]}
        parsed = {'events': [{'kind': 'dialogue', 'text': '前文', 'text_id': 't'}],
                  'source_actions': [], 'action_fields': [6], 'sha256': 'hash',
                  'route': {'choices': []}, 'unverified_content': [], 'missing_text_ids': []}
        return review, nodes, backbone, parsed

    def insert_dialogue(self, review, nodes, backbone, parsed, quest=None, choices=None):
        with patch('wuwa_story.task_local_order._flow_segment', return_value=parsed) as parser:
            insert_sync_dialogue_prefix(review, quest or {}, nodes, backbone,
                                        {'f_1_1': {}}, None, choices)
        return parser

    def test_complete_dialogue_before_unique_action_anchor(self):
        review, nodes, backbone, parsed = self.dialogue_fixture()
        original = deepcopy(nodes)
        choices = {'f_1_1:1': 1}
        parser = self.insert_dialogue(review, nodes, backbone, parsed, choices=choices)
        self.assertEqual([e['text'] for e in backbone['segments'][0]['events']], ['前文', '后文'])
        self.assertEqual(review['classification'], 'placed_sync_dialogue_prefix')
        self.assertTrue(review['proof']['relative_order_verified'])
        self.assertFalse(review['proof']['runtime_verified'])
        self.assertEqual(parser.call_args.args[-1], choices)
        self.assertEqual(nodes, original)
        self.assertEqual(parsed['events'], [{'kind': 'dialogue', 'text': '前文', 'text_id': 't'}])
        self.insert_dialogue(review, nodes, backbone, parsed)
        self.assertEqual(len(backbone['segments'][0]['events']), 2)

    def test_complete_dialogue_before_child_finish_anchor(self):
        review, nodes, backbone, parsed = self.dialogue_fixture()
        nodes[1]['Type'] = 'ChildQuest'
        nodes[1]['FinishActions'] = nodes[1].pop('Actions')
        self.insert_dialogue(review, nodes, backbone, parsed)
        self.assertTrue(review['placement_verified'])
        self.assertEqual(review['proof']['phase'], 'FinishActions')

    def test_dialogue_prefix_rejects_async_and_intervening_actions(self):
        for mode in ('first_async', 'second_async', 'intervening', 'prefix_action', 'invalid_id'):
            with self.subTest(mode=mode):
                review, nodes, backbone, parsed = self.dialogue_fixture()
                calls = nodes[1]['Actions']
                if mode == 'first_async':
                    calls[0]['Async'] = True
                elif mode == 'second_async':
                    calls[1]['Async'] = True
                elif mode == 'intervening':
                    calls.insert(1, {'Name': 'SetVar', 'Params': {}})
                elif mode == 'prefix_action':
                    calls.insert(0, {'Name': 'Wait', 'Params': {'Time': 1}})
                else:
                    calls[1]['Params']['StateId'] = True
                old = deepcopy(backbone)
                self.insert_dialogue(review, nodes, backbone, parsed)
                self.assertFalse(review['placement_verified'])
                self.assertEqual(backbone, old)

    def test_dialogue_prefix_rejects_ambiguous_or_conditional_ownership(self):
        for mode in ('duplicate_call', 'duplicate_recap', 'parallel', 'condition', 'failure', 'cycle', 'duplicate_node'):
            with self.subTest(mode=mode):
                review, nodes, backbone, parsed = self.dialogue_fixture()
                quest = {}
                if mode == 'duplicate_call':
                    quest['Flow'] = deepcopy(nodes[1]['Actions'][0]['Params'])
                elif mode == 'duplicate_recap':
                    backbone['segments'].append(deepcopy(backbone['segments'][0]))
                elif mode == 'parallel':
                    nodes[0]['Type'] = 'ParallelSelect'
                elif mode == 'condition':
                    nodes[0]['Condition'] = {'Type': 'CompareVar'}
                elif mode == 'failure':
                    nodes[1]['FailedCondition'] = {'Type': 'Fail'}
                elif mode == 'cycle':
                    nodes[0]['ParentNodeId'] = 2
                else:
                    nodes.append(deepcopy(nodes[0]))
                old = deepcopy(backbone)
                self.insert_dialogue(review, nodes, backbone, parsed, quest=quest)
                self.assertFalse(review['placement_verified'])
                self.assertEqual(backbone, old)

    def test_dialogue_prefix_requires_complete_parse_and_anchor(self):
        for mode in ('blocked_anchor', 'prefix_anchor', 'existing_insert', 'failed_parse', 'missing_text', 'unverified', 'media'):
            with self.subTest(mode=mode):
                review, nodes, backbone, parsed = self.dialogue_fixture()
                target = backbone['segments'][0]
                if mode == 'blocked_anchor':
                    target['status'] = 'blocked'
                elif mode == 'prefix_anchor':
                    target['prefix_event_count'] = 1
                elif mode == 'existing_insert':
                    target['inserted_task_flows'] = [{'state_key': 'other'}]
                elif mode == 'failed_parse':
                    parsed = None
                elif mode == 'missing_text':
                    parsed['missing_text_ids'] = ['t']
                elif mode == 'unverified':
                    parsed['unverified_content'] = [{'kind': 'unknown'}]
                else:
                    parsed['events'][0]['kind'] = 'media_reference'
                old = deepcopy(backbone)
                self.insert_dialogue(review, nodes, backbone, parsed)
                self.assertFalse(review['placement_verified'])
                self.assertEqual(backbone, old)

    def test_real_palmiro_prefix_in_mainline_once(self):
        from wuwa_story.recap_backbone import export_task_backbone
        from wuwa_story.mainline_reading import mainline_reading_text
        result = export_task_backbone(140000011)
        prefix = '剧情_2_0_黎那汐塔主线_第三幕上_帕尔米罗_1_9'
        anchor = '剧情_2_0_黎那汐塔主线_第三幕上_帕尔米罗_1_2'
        segment = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == anchor)
        self.assertEqual([e['state_key'] for e in segment['events'][:5]], [prefix] * 4 + [anchor])
        self.assertEqual(segment['events'][1]['display_name'], '洛可可')
        self.assertEqual(segment['events'][4]['display_name'], '？？？')
        self.assertEqual(len([e for e in segment['events'] if e['state_key'] == prefix]), 4)
        self.assertFalse(any(r.get('origin') == prefix for r in result['batch_coverage']['records']))
        placed = [r for r in result['batch_coverage']['records'] if r.get('order_scope') == 'task_sync_prefix_order']
        self.assertEqual(len(placed), 4)
        text = mainline_reading_text(result)
        self.assertEqual(text.count('别害怕，佩洛是在和你打招呼。'), 1)
        self.assertLess(text.index('别害怕，佩洛是在和你打招呼。'), text.index('佩洛，我不擅长和别人打招呼'))

    def test_bridge_rejects_async_and_unknown_params(self):
        a = {'Name': 'AwakeEntity', 'Params': {'EntityIds': [1]}}
        self.assertTrue(bridge_action(a))
        self.assertFalse(bridge_action(dict(a, Async=True)))
        self.assertFalse(bridge_action({'Name': 'SetVar', 'Params': {}}))
        self.assertFalse(bridge_action({'Name': 'AwakeEntity', 'Params': {'EntityIds': [1], 'Extra': True}}))

    def test_prefix_retains_gap_and_does_not_choose_qte_outcome(self):
        flow = lambda i: {'FlowListName': 'f', 'FlowId': 1, 'StateId': i}
        n = {'Id': 2, 'Type': 'ChildQuest', 'FinishActions': [
            {'Name': 'PlayFlow', 'Params': flow(1)},
            {'Name': 'AwakeEntity', 'Params': {'EntityIds': [1]}},
            {'Name': 'PlayFlow', 'Params': flow(2)}]}
        raw = [{'Name': 'ShowTalk', 'Params': {'TalkItems': [
            {'Type': 'Talk', 'Id': 1, 'TidTalk': 't'}, {'Type': 'QTE', 'Id': 2, 'QteId': 12}],
            'TalkSequence': [[1, 2]]}}]
        def run(node, source=raw, duplicate=False):
            r = {'state_key': 'f_1_1', 'owner_nodes': [node],
                 'ancestor_chains': [{'ancestors': [{'type': 'Sequence'}]}]}
            b = {'segments': [{'state_key': 'f_1_2', 'status': 'parsed', 'events': []}]}
            if duplicate: b['segments'] *= 2
            with patch('wuwa_story.sync_prefix.flow_actions', return_value=(source, [6])), \
                 patch('wuwa_story.export_task.texts', {'t': '正文'}):
                insert_qte_prefix(r, {}, [node], b, {'f_1_1': {'BinData': b'x'}}, None)
            return r, b
        r, b = run(n)
        self.assertEqual(r['visible_event_count'], 1)
        self.assertFalse(r['complete'])
        self.assertEqual(b['segments'][0]['events'][-1]['kind'], 'recap_gap')
        bad = deepcopy(n); bad['FinishActions'][0]['Async'] = True
        self.assertNotIn('proof', run(bad)[0])
        self.assertNotIn('proof', run(n, duplicate=True)[0])
        bad = deepcopy(raw); bad[0]['Params']['TalkSequence'] = [[2, 1]]
        self.assertNotIn('proof', run(n, bad)[0])

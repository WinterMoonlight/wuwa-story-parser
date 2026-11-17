from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.task_finish_supplement import insert_task_finish_supplements


class TaskFinishSupplementTests(unittest.TestCase):
    def fixture(self):
        nodes = [{'Id': 10, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 10,
                  'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'f', 'FlowId': 1, 'StateId': 1}},
                  'FinishActions': [{'Name': 'SetPlayerPos', 'Params': {'TelePortConfig': {
                      'Type': 0, 'TargetPos': {'X': 1, 'Y': 2, 'Z': 3, 'A': 0}}}},
                      {'Name': 'DestroyEntity', 'Params': {'EntityIds': [1]}},
                      {'Name': 'ShowHidedGroup', 'Params': {'GroupKey': 'g', 'DelayShow': True}},
                      {'Name': 'FadeOutScreen', 'Params': {'Ease': {'Type': 2, 'Duration': 1}}},
                      {'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 2, 'StateId': 1}, 'Async': True}]}]
        backbone = {'segments': [{'state_key': 'f_1_1', 'status': 'parsed', 'events': [{'text': 'before'}]}],
                    'task_only_review': [{'state_key': 'f_2_1', 'placement_verified': False}]}
        parsed = {'state_key': 'f_2_1', 'events': [{'kind': 'dialogue', 'text': 'after'}],
                  'source_actions': [], 'action_fields': [1], 'sha256': 'hash', 'route': {'choices': []},
                  'unverified_content': [], 'missing_text_ids': []}
        return nodes, backbone, parsed

    def insert(self, nodes, backbone, parsed, quest=None, choices=None):
        with patch('wuwa_story.task_finish_supplement._flow_segment', return_value=parsed) as parser:
            result = insert_task_finish_supplements(quest or {}, nodes, backbone, {'f_2_1': {}}, None, choices)
        return result, parser

    def test_async_tail_call_recognizes_scene_actions(self):
        nodes, backbone, parsed = self.fixture()
        original = deepcopy(nodes)
        result, _ = self.insert(nodes, backbone, parsed)
        self.assertEqual(len(result), 1)
        self.assertEqual([e['text'] for e in backbone['segments'][0]['events']], ['before', 'after'])
        self.assertEqual(nodes, original)
        self.assertTrue(result[0]['invocation_async'])
        self.assertFalse(result[0]['later_async_completion_order_verified'])
        self.assertTrue(backbone['task_only_review'][0]['placement_verified'])
        self.assertEqual(self.insert(nodes, backbone, parsed)[0], [])

    def test_async_nonterminal_call_still_requires_order_evidence(self):
        nodes, backbone, parsed = self.fixture()
        backbone['segments'].append({'state_key': 'f_3_1', 'status': 'parsed', 'events': []})
        old = deepcopy(backbone)
        self.assertEqual(self.insert(nodes, backbone, parsed)[0], [])
        self.assertEqual(backbone, old)
        nodes[1]['FinishActions'][-1]['Async'] = False
        self.assertEqual(len(self.insert(nodes, backbone, parsed)[0]), 1)

    def test_unknown_action_and_invalid_payload_rejected(self):
        for mode in ('action', 'position', 'entity', 'delay', 'duration', 'async'):
            with self.subTest(mode=mode):
                nodes, backbone, parsed = self.fixture()
                actions = nodes[1]['FinishActions']
                if mode == 'action':
                    actions[0] = {'Name': 'SetVar', 'Params': {}}
                elif mode == 'position':
                    actions[0]['Params']['TelePortConfig']['TargetPos']['X'] = float('nan')
                elif mode == 'entity':
                    actions[1]['Params']['EntityIds'] = [True]
                elif mode == 'delay':
                    actions[2]['Params']['DelayShow'] = 1
                elif mode == 'duration':
                    actions[3]['Params']['Ease']['Duration'] = -1
                else:
                    actions[-1]['Async'] = 'true'
                self.assertEqual(self.insert(nodes, backbone, parsed)[0], [])

    def test_duplicate_reference_and_conditional_ancestor_rejected(self):
        nodes, backbone, parsed = self.fixture()
        quest = {'Flow': nodes[1]['FinishActions'][-1]['Params']}
        self.assertEqual(self.insert(nodes, backbone, parsed, quest)[0], [])
        nodes[0]['Type'] = 'ParallelSelect'
        self.assertEqual(self.insert(nodes, backbone, parsed)[0], [])

    def test_failed_or_uncertain_parse_keeps_original_body(self):
        for mode in ('failure', 'missing', 'unverified', 'placeholder'):
            with self.subTest(mode=mode):
                nodes, backbone, parsed = self.fixture()
                old = deepcopy(backbone)
                if mode == 'failure':
                    parsed = None
                elif mode == 'missing':
                    parsed['missing_text_ids'] = ['x']
                elif mode == 'unverified':
                    parsed['unverified_content'] = [{'kind': 'unknown'}]
                else:
                    parsed['events'][0]['kind'] = 'media_reference'
                self.assertEqual(self.insert(nodes, backbone, parsed)[0], [])
                self.assertEqual(backbone, old)

    def test_requested_choices_are_forwarded(self):
        nodes, backbone, parsed = self.fixture()
        choices = {'f_2_1:1': 1}
        _, parser = self.insert(nodes, backbone, parsed, choices=choices)
        self.assertEqual(parser.call_args.args[-1], choices)

    def test_real_augusta_followup_is_in_body(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(311000001)
        key = '剧情_2_6_狄斯台地主线_上半_1_40_1'
        events = [e for s in result['recap_backbone']['segments'] for e in s['events'] if e.get('state_key') == key]
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0]['display_name'], '奥古斯塔')
        self.assertEqual(events[-1]['text'], '遵从您的指令。')
        self.assertFalse(any(r.get('origin') == key for r in result['batch_coverage']['records']))
        self.assertTrue(all(r['order_scope'] == 'task_finish_call_order' for r in result['batch_coverage']['records']
                            if r.get('pointer', '').startswith('/recap_backbone/') and r.get('text') in {e['text'] for e in events}))


if __name__ == '__main__':
    unittest.main()

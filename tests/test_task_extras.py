import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.task_extras import review_extras, interaction_evidence


class TaskExtrasTests(unittest.TestCase):
    def test_screen_text_before_synchronous_anchor(self):
        flow = lambda n: {'FlowListName': 'f', 'FlowId': 1, 'StateId': n}
        nodes = [{'Id': 1, 'Type': 'Sequence'}, {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 1,
                  'FinishActions': [{'Name': 'PlayFlow', 'Params': flow(2)},
                                    {'Name': 'PlayFlow', 'Params': flow(1), 'Async': False}]}]
        raw = [{'Name': 'ShowTalk', 'Params': {'TalkItems': [
            {'Type': 'CenterText', 'Id': 1, 'TidTalk': 't'}]}}]
        def run(ns, actions=raw, duplicate=False):
            b = {'segments': [{'state_key': 'f_1_1', 'status': 'parsed', 'events': []}]}
            if duplicate: b['segments'] *= 2
            with patch('wuwa_story.task_extras.flow_actions', return_value=(actions, [6])), \
                 patch('wuwa_story.export_task.texts', {'t': '修复完成'}):
                r = review_extras({}, ns, b, {'f_1_2': {'BinData': b'x'}}, None)[0]
            return r, b
        r, b = run(nodes)
        self.assertEqual(r['classification'], 'placed_screen_text')
        self.assertEqual(b['segments'][0]['events'][0]['display_name'], '画面文字')
        self.assertEqual(r['proof']['before_state'], 'f_1_1')
        for phase in (0, 1):
            bad = deepcopy(nodes); bad[1]['FinishActions'][phase]['Async'] = True
            self.assertFalse(run(bad)[0]['placement_verified'])
        self.assertFalse(run(nodes, duplicate=True)[0]['placement_verified'])
        bad = deepcopy(nodes); bad[0]['Type'] = 'ParallelSelect'
        self.assertFalse(run(bad)[0]['placement_verified'])
        bad = deepcopy(nodes); bad.append({'Id': 3, 'Type': 'ChildQuest', 'Condition': flow(1)})
        self.assertFalse(run(bad)[0]['placement_verified'])
        bad_raw = deepcopy(raw); bad_raw[0]['Params']['TalkItems'][0]['Type'] = 'Talk'
        self.assertFalse(run(nodes, bad_raw)[0]['placement_verified'])

    def test_interaction_region_is_not_an_execution_anchor(self):
        nodes = [
            {'Id': 1, 'Type': 'ParallelSelect'},
            {'Id': 2, 'Type': 'AlwaysFalse', 'ParentNodeId': 1},
            {'Id': 3, 'Type': 'ChildQuest', 'ParentNodeId': 2, 'TidTip': 'local',
             'Condition': {'Type': 'DoInteract', 'AddOptions': [{'EntityId': 42}]}},
            {'Id': 4, 'Type': 'ChildQuest', 'ParentNodeId': 1, 'TidTip': 'main',
             'EnterActions': [{'Name': 'AwakeEntity', 'Params': {'EntityIds': [42]}}]},
            {'Id': 5, 'Type': 'ChildQuest', 'TidTip': 'unrelated'}]
        entries = [{'TidTip': 'main'}, {'TidTip': 'main'}, {'TidTip': 'unrelated'}]
        evidence = interaction_evidence(nodes[2], nodes, entries)
        self.assertFalse(evidence['placement_verified'])
        self.assertEqual(evidence['direct_tip_matches'], [])
        self.assertEqual([m['entry_index'] for m in evidence['recap_region_evidence']['matches']], [0, 1])
        self.assertEqual(evidence['entity_lifecycle'][0]['node_id'], 4)
        self.assertIsNone(interaction_evidence(nodes[4], nodes, entries))

    def test_transition_is_placed_only_after_unique_synchronous_anchor(self):
        flow = lambda n: {'FlowListName': 'f', 'FlowId': 1, 'StateId': n}
        nodes = [{'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 1, 'FinishActions': [
                     {'Name': 'PlayFlow', 'Params': flow(1)},
                     {'Name': 'TeleportDungeon', 'Params': {'TransitionOption': {
                         'Type': 'CenterText', 'CenterTextFlow': flow(2)}}}]}]
        def run(ns, repeat=False, text="翌日"):
            b = {'segments': [{'state_key': 'f_1_1', 'status': 'parsed', 'events': []}]}
            if repeat: b['segments'] *= 2
            with patch('wuwa_story.task_extras.flow_actions', return_value=([
                {'Name': 'ShowCenterText', 'Params': {'TidCenterText': 't'}}], [1])), \
                 patch('wuwa_story.export_task.texts', {'t': text}):
                review = review_extras({}, ns, b, {'f_1_2': {'BinData': b'x'}}, None)
            return review, b
        review, b = run(nodes)
        self.assertTrue(review[0]['placement_verified'])
        self.assertEqual(b['segments'][0]['events'][0]['text'], '翌日')
        empty, empty_b = run(nodes, text='')
        self.assertEqual(empty[0]['classification'], 'placed_empty_transition')
        self.assertEqual(empty_b['segments'][0]['events'], [])
        self.assertEqual(empty[0]['text_evidence'][0]['raw_text'], '')
        bad = deepcopy(nodes); bad[1]['FinishActions'][0]['Async'] = True
        self.assertFalse(run(bad)[0][0]['placement_verified'])
        bad = deepcopy(nodes); bad.append({'Id': 3, 'Type': 'ChildQuest', 'ParentNodeId': 1,
                                         'FinishActions': [deepcopy(nodes[1]['FinishActions'][0])]})
        self.assertFalse(run(bad)[0][0]['placement_verified'])
        self.assertFalse(run(nodes, True)[0][0]['placement_verified'])

    def test_parallel_ancestor_does_not_prove_placement(self):
        nodes = [{'Id': 1, 'Type': 'AlwaysFalse', 'ParentNodeId': 0},
                 {'Id': 2, 'Type': 'ChildQuest', 'ParentNodeId': 1, 'FinishActions': [
                     {'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 1, 'StateId': 2}}]}]
        r = review_extras({}, nodes, {'segments': []}, {}, None)[0]
        self.assertEqual(r['classification'], 'parallel_conditioned')
        self.assertFalse(r['placement_verified'])

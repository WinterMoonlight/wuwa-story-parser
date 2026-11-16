import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.sync_prefix import bridge_action, insert_qte_prefix


class SyncPrefixTests(unittest.TestCase):
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

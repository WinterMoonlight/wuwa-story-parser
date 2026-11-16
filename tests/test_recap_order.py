import unittest
from copy import deepcopy
from wuwa_story.recap_order import anchored_finish_flows
from wuwa_story.export_task import Exporter


class RecapOrderTests(unittest.TestCase):
    def setUp(self):
        self.nodes = [{'Id': 90, 'Type': 'Sequence', 'ParentNodeId': 0},
                      {'Id': 1, 'ParentNodeId': 90, 'Type': 'ChildQuest', 'TidTip': 'tip',
                       'Condition': {'Type': 'ReachArea', 'Pos': {'X': 0, 'Y': 0, 'Z': 0}, 'Range': 10},
                       'FinishActions': [{'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 7, 'StateId': 1}}]}]
        self.entries = [{'Flow': {'FlowListName': 'f', 'FlowId': 2, 'StateId': 1}}, {'TidTip': 'tip'}]

    def test_exact_anchor_not_node_id_order(self):
        order, proof = anchored_finish_flows({}, self.nodes, self.entries)
        self.assertEqual(order, ['f_2_1', 'f_7_1'])
        self.assertEqual(proof[0]['recap_entry_index'], 1)
        self.assertFalse(proof[0]['runtime_verified'])

    def test_ambiguous_or_populated_anchors_rejected(self):
        for entries in [self.entries + [{'TidTip': 'tip'}], self.entries + [self.entries[0]], []]:
            self.assertEqual(anchored_finish_flows({}, self.nodes, entries)[1], [])

    def test_branches_async_shared_and_conditional_steps_rejected(self):
        for change in ('branch', 'async', 'conditional', 'shared'):
            nodes = deepcopy(self.nodes);quest = {}
            if change == 'branch': nodes[0]['Type'] = 'ParallelSelect'
            if change == 'async': nodes[1]['FinishActions'][0]['Async'] = True
            if change == 'conditional': nodes[1]['Condition']['PreConditions'] = {'Type': 0}
            if change == 'shared': quest['Flow'] = nodes[1]['FinishActions'][0]['Params']
            self.assertFalse(anchored_finish_flows(quest, nodes, self.entries)[1])

    def test_real_task_appends_missing_normal_flow_with_evidence(self):
        r = Exporter(allow_incomplete=True).export(192750000)
        self.assertEqual([s['state_key'].rsplit('_', 2)[1] for s in r['source']['scenes']], ['2','3','4','5','6','7'])
        self.assertEqual(len(r['events']), 123)
        self.assertEqual(r['validation']['missing_text_ids'], [])
        self.assertFalse(r['validation']['complete_for_supported_task_shape'])
        self.assertEqual(r['source']['recap_reference_resolution']['anchored_insertions'][0]['node_id'], 6)
        with self.assertRaises(ValueError): Exporter().export(192750000)


if __name__ == '__main__': unittest.main()

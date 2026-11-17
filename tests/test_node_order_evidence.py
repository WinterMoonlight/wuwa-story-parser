import unittest
from wuwa_story.node_order_evidence import pair_evidence, storage_evidence


class NodeOrderTests(unittest.TestCase):
    def test_row_order_does_not_define_execution(self):
        nodes = [{'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0},
                 {'Id': 135, 'Type': 'ChildQuest', 'ParentNodeId': 1},
                 {'Id': 3, 'Type': 'QuestSucceed', 'ParentNodeId': 1}]
        a = pair_evidence(nodes, 135, 3)
        self.assertEqual(a, pair_evidence(list(reversed(nodes)), 135, 3))
        self.assertFalse(a['execution_order_verified'])
        self.assertEqual(a['common_ancestor']['node_id'], 1)

    def test_broken_chain_is_not_order_evidence(self):
        r = pair_evidence([{'Id': 1, 'ParentNodeId': 8}], 1, 3)
        self.assertEqual(r['reason'], 'invalid_ancestry')
        self.assertFalse(r['execution_order_verified'])

    def test_bad_binary_is_not_silently_accepted(self):
        r = storage_evidence({'Key': 'x', 'BinData': b'bad'})
        self.assertFalse(r['storage_schema_verified'])

    def test_real_night_two_requested_relationships(self):
        from wuwa_story.recap_backbone import export_task_backbone
        d = export_task_backbone(119000000)
        f = next(f for f in d['batch_coverage']['levelplay_local_sequences'] if f['status']=='local_order_only')
        evidence = f['node_execution_evidence']
        p = next(p for p in evidence['gameplay_to_success'] if p['to_node']==3)
        self.assertEqual(p['from_ancestry'], [135, 125, 124, 1])
        self.assertEqual(p['to_ancestry'], [3, 1])
        endings = [r for r in evidence['task_gate_to_recap_conditions'] if r['to_node'] in [122, 123]]
        self.assertEqual(len(endings), 2)
        self.assertTrue(all(r['from_node']==120 and r['recap_entry_indices']==[93] for r in endings))
        self.assertTrue(all(not r['execution_order_verified'] for r in endings))
        self.assertTrue(all(r['storage_schema_verified'] for r in evidence['node_storage']))
        self.assertTrue(all(r['present_fields']==[0,1] for r in evidence['node_storage']))


if __name__ == '__main__':
    unittest.main()

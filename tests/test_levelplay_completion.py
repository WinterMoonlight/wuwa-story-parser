import unittest
from wuwa_story.levelplay_completion import ancestry, completion_evidence


class CompletionTests(unittest.TestCase):
    def evidence(self, condition=None, entries=None):
        node = {'Id': 20, 'ParentNodeId': 10, 'Type': 'ChildQuest', 'TidTip': 'tip',
                'Condition': condition or {'Type': 'CheckLevelPlay', 'LevelPlayIds': [7], 'CompleteNumber': 1}}
        audit = {'levelplay_id': 7, 'task_conditions': [{'source_node': node}],
                 'nodes': [{'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence'},
                           {'Id': 2, 'ParentNodeId': 1, 'Type': 'ChildQuest'},
                           {'Id': 3, 'ParentNodeId': 1, 'Type': 'QuestSucceed'}]}
        return completion_evidence(audit, 2, [node, {'Id': 10, 'ParentNodeId': 0, 'Type': 'Sequence'}], entries or [])

    def test_single_completion_does_not_prove_mandatory_or_order(self):
        r = self.evidence()
        self.assertTrue(r['task_gates'][0]['single_target_completion_gate'])
        self.assertFalse(r['placement_verified'])
        self.assertFalse(r['mandatory_verified'])
        self.assertFalse(r['single_execution_verified'])

    def test_multi_target_gate_not_single_play_proof(self):
        r = self.evidence({'Type': 'CheckLevelPlay', 'LevelPlayIds': [7, 8], 'CompleteNumber': 1})
        self.assertFalse(r['task_gates'][0]['single_target_completion_gate'])

    def test_tip_match_is_region_only_even_when_unique(self):
        r = self.evidence(entries=[{'TidTip': 'tip'}])
        self.assertEqual(r['task_gates'][0]['ancestor_tip_matches'][0]['entry_indices'], [0])
        self.assertFalse(r['placement_verified'])

    def test_duplicate_tips_not_collapsed(self):
        r = self.evidence(entries=[{'TidTip': 'tip'}, {'TidTip': 'tip'}])
        self.assertEqual(r['task_gates'][0]['ancestor_tip_matches'][0]['entry_indices'], [0, 1])

    def test_invalid_and_duplicate_ancestry(self):
        self.assertEqual(ancestry(1, [{'Id': 1, 'ParentNodeId': 1}])[1], 'invalid_ancestry')
        self.assertEqual(ancestry(1, [{'Id': 1}, {'Id': 1}])[1], 'duplicate_node_id')

    def test_real_night_completion_barriers(self):
        from wuwa_story.recap_backbone import export_task_backbone
        d = export_task_backbone(119000000)
        r = next(f for f in d['batch_coverage']['levelplay_local_sequences'] if f['status']=='local_order_only')['completion_dependency']
        self.assertEqual([n['node_id'] for n in r['gameplay_ancestry']], [135, 125, 124, 1])
        self.assertEqual(r['success_node_ids'], [3])
        self.assertEqual([n['node_id'] for n in r['recovery_nodes']], [124])
        self.assertEqual(r['parallel_boundaries'][0]['node_id'], 124)
        self.assertIn(139, [c['node_id'] for c in r['parallel_boundaries'][0]['children'] if c['type']=='QuestFailed'])
        gate = r['task_gates'][0]
        self.assertEqual([n['node_id'] for n in gate['task_ancestry']], [120, 119, 1])
        self.assertEqual(gate['ancestor_tip_matches'], [])
        self.assertTrue(gate['single_target_completion_gate'])
        self.assertEqual([c['phase'] for c in gate['lifecycle_calls']], ['EnterActions', 'FinishActions'])
        self.assertFalse(r['placement_verified'])


if __name__ == '__main__':
    unittest.main()

import unittest
from wuwa_story.paths import DATABASE_DIR

HAS_DATA = (DATABASE_DIR / 'db_QuestData.db').exists()


@unittest.skipUnless(HAS_DATA, 'Local ConfigDB required')
class ComplexTaskTests(unittest.TestCase):
    def test_core_recap_coverage_menu_exit_and_alternative(self):
        from wuwa_story.export_task import Exporter
        result = Exporter().export(139000029)
        self.assertEqual(len(result['source']['task_nodes']), 73)
        self.assertEqual(len(result['source']['scenes']), 24)
        self.assertEqual(result['validation']['referenced_flow_count'], 24)
        self.assertEqual(result['validation']['missing_text_ids'], [])
        self.assertEqual(len(result['events']), 321)
        self.assertEqual(len(result['route']['choices']), 54)
        menu = [c for c in result['route']['choices'] if c['choice_key'].endswith('_1_23:20')]
        self.assertEqual([c['selected_index'] for c in menu], [0, 1, 2, 3, 4])
        self.assertEqual([c['visit'] for c in menu], [1, 2, 3, 4, 5])
        alternate = Exporter({menu[0]['choice_key']: 4}).export(139000029)
        self.assertLess(len(alternate['events']), len(result['events']))
        self.assertEqual(alternate['events'][-1]['text_id'], result['events'][-1]['text_id'])
        self.assertTrue(any(e['kind'] == 'narration' and e['text_id'] == 'Flow_139000007_491'
                            for e in result['events']))
        self.assertTrue(all(t['all_branch_text_and_jump_references_checked'] for t in result['validation']['talk_groups']))
        self.assertFalse(result['source']['task_audit']['runtime_graph_executed'])

    def test_unselected_broken_jump_fails(self):
        from wuwa_story.export_task import Exporter
        e = Exporter()
        e.state_key = 'test'
        e.text = lambda key: key
        with self.assertRaisesRegex(ValueError, 'Missing JumpTalk target'):
            e.talk([{'Id': 1, 'Options': [{'TidTalkOption': 'ok'},
                    {'TidTalkOption': 'bad', 'Actions': [{'Name': 'JumpTalk', 'Params': {'TalkId': 999}}]}]}])

    def test_infinite_loops_fail_instead_of_truncating(self):
        from wuwa_story.export_task import Exporter
        for item in [
            {'Id': 1, 'Actions': [{'Name': 'JumpTalk', 'Params': {'TalkId': 1}}]},
            {'Id': 1, 'Options': [{'TidTalkOption': 'again', 'Actions': [{'Name': 'JumpTalk', 'Params': {'TalkId': 1}}]}]},
        ]:
            e = Exporter()
            e.state_key = 'test'
            e.text = lambda key: key
            with self.assertRaisesRegex(ValueError, 'loop'):
                e.talk([item])

    def test_parent_cycle_and_orphan_are_rejected(self):
        from wuwa_story.coverage import audit_task
        base = [{'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence'},
                {'Id': 2, 'ParentNodeId': 1, 'Type': 'QuestSucceed'}]
        for node in [{'Id': 3, 'ParentNodeId': 3, 'Type': 'Sequence'},
                     {'Id': 3, 'ParentNodeId': 99, 'Type': 'Sequence'}]:
            with self.assertRaises(ValueError):
                audit_task({}, base + [node])

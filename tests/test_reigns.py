import unittest
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_Reigns.db').exists(), 'Local ConfigDB required')
class ReignsTests(unittest.TestCase):
    def test_real_task_variables_and_inventory(self):
        from wuwa_story.export_task import Exporter
        d = Exporter(allow_incomplete=True).export(164000000)
        self.assertEqual(len(d['events']), 156)
        self.assertEqual(d['validation']['status'], 'needs_review')
        self.assertEqual(d['validation']['confirmed_missing_text_ids'], [])
        assigns = [e for e in d['external_content'] if 'variable' in e]
        self.assertEqual({e['assigned_value'] for e in assigns}, {2, 3, 4, 5})
        self.assertTrue(all({r['node_id'] for r in e['readers']} == {14, 22, 27, 32} for e in assigns))
        games = [e for e in d['external_content'] if 'gameplay' in e]
        self.assertEqual(len(games), 5)
        self.assertEqual({e['gameplay']['reigns_id'] for e in games}, {700001, 700002, 700003, 700004})
        self.assertTrue(all(not e['gameplay']['route_simulated'] for e in games))
        self.assertTrue(all('text' in t for e in games for t in e['texts']))
        self.assertTrue(any(c['status'] == 'reference_unresolved' for c in games[0]['gameplay']['cards']))
        with self.assertRaises(ValueError):
            Exporter().export(164000000)

    def test_missing_gameplay_and_wrong_type_rejected(self):
        from wuwa_story.reigns import inspect_reigns
        with self.assertRaises(ValueError):
            inspect_reigns({'Type': 'Reigns', 'ReignsId': 700001}, lambda *args: [])
        with self.assertRaises(ValueError):
            inspect_reigns({'Type': 'Other', 'ReignsId': 700001}, lambda *args: [])

    def test_nonconstant_assignment_rejected(self):
        from wuwa_story.external import inspect_task_content
        n = {'Id': 1, 'ParentNodeId': 0, 'Type': 'Sequence', 'Actions': [{'Name': 'SetVar', 'Params': {
             'VarLeft': {'Type': 'Int', 'Source': 'Self', 'Name': 'x'},
             'VarRight': {'Type': 'Int', 'Source': 'Self', 'Name': 'y'}}}]}
        with self.assertRaises(ValueError):
            inspect_task_content([n], lambda *args: [])

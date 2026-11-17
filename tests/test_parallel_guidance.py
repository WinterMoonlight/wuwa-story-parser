import copy
import json
from pathlib import Path
import unittest

from wuwa_story.parallel_guidance import guidance_evidence


class ParallelGuidanceTests(unittest.TestCase):
    def setUp(self):
        from wuwa_story.database import embedded, rows
        self.nodes = [embedded(row['BinData'])[0][1]
                      for row in rows('db_QuestNodeData.db', 'questnodedata')
                      if row['Key'].startswith('139000027_')]
        row = next(row for row in rows('db_PlotHandBook.db', 'plothandbookconfig')
                   if row['QuestId'] == 139000027)
        self.entries = next(value for _, value in embedded(row['BinData']) if isinstance(value, list))

    def test_real_teaching_pair_only(self):
        evidence = guidance_evidence(self.nodes, self.entries)
        self.assertEqual(len(evidence), 2)
        self.assertEqual({value['entry_index'] for value in evidence.values()}, {33, 34})
        self.assertTrue(all(value['guide_id'] == 10057 for value in evidence.values()))
        self.assertTrue(all(not value['order_verified'] for value in evidence.values()))

    def test_hidden_flag_alone_and_extra_owner_rejected(self):
        nodes = copy.deepcopy(self.nodes)
        next(node for node in nodes if node['Id'] == 211)['Type'] = 'Sequence'
        self.assertFalse(guidance_evidence(nodes, self.entries))
        nodes = copy.deepcopy(self.nodes)
        other = next(node for node in nodes if node['Id'] == 268)
        call = next(node for node in nodes if node['Id'] == 324)['FinishActions'][1]
        other['FinishActions'].append(copy.deepcopy(call))
        self.assertFalse(guidance_evidence(nodes, self.entries))

    def test_guide_and_ui_conditions_required(self):
        for field in ('guide', 'ui', 'visibility', 'duplicate_recap'):
            nodes, entries = copy.deepcopy(self.nodes), copy.deepcopy(self.entries)
            second = next(node for node in nodes if node['Id'] == 324)
            if field == 'guide':
                second['FinishActions'][0]['Name'] = 'Unknown'
            elif field == 'ui':
                second['Condition'] = {'Type': 'AlwaysTrue'}
            elif field == 'visibility':
                second['HideTip'] = False
            else:
                entries.append(copy.deepcopy(entries[33]))
            self.assertFalse(guidance_evidence(nodes, entries))


if __name__ == '__main__':
    unittest.main()

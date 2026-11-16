import unittest
from copy import deepcopy
from wuwa_story.batch import Snapshot
from wuwa_story.export_task import Exporter
from wuwa_story.database import embedded
from wuwa_story.unplaced import completion_only_flows
from wuwa_story.entity_links import linked_entity_flows
from wuwa_story.reading import reading_text


class EpilogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.q = next(embedded(r['BinData'])[0][1] for r in cls.source.rows('db_QuestData.db', 'questdata') if r['QuestId'] == 168850009)
        cls.ns = [embedded(r['BinData'])[0][1] for r in cls.source.rows('db_QuestNodeData.db', 'questnodedata') if r['Key'].startswith('168850009_')]

    def test_nested_entity_ownership_and_lock_preserved(self):
        keys = {f'剧情_3_7_心相迷宫&后日谈_5_{i}' for i in range(1, 5)}
        links = linked_entity_flows(self.q, self.ns, keys, self.source.rows)
        self.assertEqual(len(links), 4)
        self.assertTrue(all(l['awake_calls'][0]['ancestor_chain'] for l in links))
        bad = deepcopy(self.ns)
        next(n for n in bad if n['Id'] == 13)['Type'] = 'AlwaysFalse'
        self.assertEqual(linked_entity_flows(self.q, bad, keys, self.source.rows), [])

    def test_normal_completion_extras_not_dropped_or_sorted_as_route(self):
        keys = {f'剧情_3_7_心相迷宫&后日谈_3_{i}' for i in (10, 11, 13)}
        self.assertEqual(len(completion_only_flows(self.q, self.ns, keys)), 3)
        bad = deepcopy(self.ns)
        next(n for n in bad if n['Id'] == 7)['FailedCondition'] = {'Type': 'Test'}
        self.assertEqual(completion_only_flows(self.q, bad, keys), [])

    def test_real_partial_export_keeps_all_bodies(self):
        result = Exporter(source=self.source, allow_incomplete=True).export(168850009)
        self.assertEqual(len(result['events']), 51)
        self.assertEqual(result['validation']['unplaced_flow_count'], 3)
        self.assertFalse(result['validation']['complete_for_supported_task_shape'])
        extras = [e for e in result['external_content'] if 'unplaced_flow' in e]
        self.assertEqual(sum(len(e['texts']) for e in extras), 76)
        self.assertEqual(result['validation']['missing_text_ids'], [])
        text = reading_text(result)
        self.assertEqual(text.count('正常剧情片段：尚未确定'), 3)
        self.assertIn('整个任务顺序尚未补齐', text)
        self.assertEqual(self.q['ProvideType']['Conditions'], [{'Type': 'PreQuest', 'PreQuest': 168000003}])

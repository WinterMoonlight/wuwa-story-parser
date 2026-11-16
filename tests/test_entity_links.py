import unittest
from copy import deepcopy
from unittest.mock import patch
from wuwa_story.database import embedded
from wuwa_story.batch import Snapshot
from wuwa_story.entity_links import linked_entity_flows
from wuwa_story.export_task import Exporter
from wuwa_story.reading import reading_text


class EntityLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Snapshot()
        cls.quest = next(embedded(r['BinData'])[0][1] for r in cls.source.rows('db_QuestData.db', 'questdata') if r['QuestId'] == 168000003)
        cls.nodes = [embedded(r['BinData'])[0][1] for r in cls.source.rows('db_QuestNodeData.db', 'questnodedata') if r['Key'].startswith('168000003_')]
        cls.missing = {f'剧情_3_7_心相迷宫&后日谈_3_{i}' for i in (6, 7)}

    def test_exact_owned_awakened_entities(self):
        links = linked_entity_flows(self.quest, self.nodes, self.missing, self.source.rows)
        self.assertEqual({l['entity_id'] for l in links}, {168850015, 168000053})
        self.assertTrue(all(l['map_id'] == 8 for l in links))
        self.assertTrue(all(l['equivalent_json_fields'] == [1, 10] for l in links))

    def test_declaration_and_awake_required(self):
        self.assertEqual(linked_entity_flows({**self.quest, 'Children': []}, self.nodes, self.missing, self.source.rows), [])
        nodes = deepcopy(self.nodes)
        for n in nodes:
            n['EnterActions'] = []
        self.assertEqual(linked_entity_flows(self.quest, nodes, self.missing, self.source.rows), [])

    def test_ambiguous_or_conditional_entity_not_admitted(self):
        original = self.source.rows
        def duplicates(file, table):
            values = original(file, table)
            return values * 2
        self.assertEqual(linked_entity_flows(self.quest, self.nodes, self.missing, duplicates), [])
        def conditional(blob):
            values = deepcopy(embedded(blob))
            for _, obj in values:
                if isinstance(obj, dict) and 'InteractComponent' in obj:
                    obj['InteractComponent']['Condition'] = {'Unknown': True}
            return values
        with patch('wuwa_story.entity_links.embedded', side_effect=conditional):
            self.assertEqual(linked_entity_flows(self.quest, self.nodes, self.missing, original), [])

    def test_real_reading_order_and_limits(self):
        result = Exporter(source=self.source, allow_incomplete=True).export(168000003)
        self.assertEqual([s['state_key'].rsplit('_', 1)[1] for s in result['source']['scenes']], ['2', '6', '7', '4', '12'])
        self.assertEqual(len(result['events']), 50)
        self.assertEqual(result['validation']['missing_text_ids'], [])
        self.assertEqual(result['validation']['status'], 'needs_review')
        self.assertEqual(len(result['source']['recap_reference_resolution']['linked_entities']), 2)
        text = reading_text(result)
        self.assertIn('实际触发先后及是否必经尚未核验', text)
        self.assertIn('过场字幕', text)
        self.assertIn('御者，城中佳夜已至，同我赴这场朝月喜事吧。', text)
        self.assertTrue(any(e.get('video_name') == 'M0391' for e in result['validation']['unverified_content']))

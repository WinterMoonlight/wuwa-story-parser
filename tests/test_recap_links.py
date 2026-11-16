import unittest
from unittest.mock import patch
from wuwa_story.recap_links import linked_levelplays, reconcile
from wuwa_story.export_task import Exporter
from wuwa_story.batch import Snapshot


class RecapLinksTests(unittest.TestCase):
    def test_reconciliation_requires_exact_union_and_unique_order(self):
        links = [{'flow_references': ['b']}]
        self.assertTrue(reconcile({'a'}, ['b', 'a'], links))
        self.assertFalse(reconcile({'a', 'missing'}, ['a', 'b'], links))
        self.assertFalse(reconcile({'a'}, ['a', 'b', 'b'], links))
        self.assertFalse(reconcile({'a'}, ['a', 'b', 'unknown'], links))
        self.assertFalse(reconcile(set(), ['b'], []))

    def test_real_dungeon_relation_and_mismatched_evidence(self):
        source = Snapshot()
        from wuwa_story.database import embedded
        ns = [embedded(r['BinData'])[0][1] for r in source.rows('db_QuestNodeData.db', 'questnodedata')
              if r['Key'].startswith('121850000_')]
        entries = next(embedded(r['BinData'])[0][1] for r in source.rows('db_PlotHandBook.db', 'plothandbookconfig') if r['QuestId'] == 121850000)
        links = linked_levelplays(ns, entries, source.rows)
        self.assertEqual([x['levelplay_id'] for x in links], [121850006])
        self.assertEqual(len(links[0]['flow_references']), 7)
        self.assertEqual(links[0]['dungeon_ids'], [1603])
        self.assertEqual(links[0]['map_id'], 907)
        self.assertEqual(linked_levelplays(ns, [{'TidTip': 'unrelated'}], source.rows), [])
        def wrong_map(file, table):
            values = source.rows(file, table)
            if table == 'instancedungeon':
                return [{**r, 'MapConfigId': -1} for r in values]
            return values
        self.assertEqual(linked_levelplays(ns, entries, wrong_map), [])

    def test_export_retains_review_and_strict_boundary(self):
        with self.assertRaises(ValueError):
            Exporter().export(121850000)
        result = Exporter(allow_incomplete=True).export(121850000)
        self.assertEqual(len(result['events']), 68)
        self.assertEqual(result['validation']['missing_text_ids'], [])
        self.assertEqual(result['validation']['status'], 'needs_review')
        self.assertFalse(result['validation']['complete_for_supported_task_shape'])
        evidence = result['source']['recap_reference_resolution']
        self.assertEqual(evidence['direct_references'], [])
        self.assertEqual(len(evidence['expanded_references']), 7)
        self.assertTrue(any(x['kind'] == 'media_text' for x in result['validation']['unverified_content']))


if __name__ == '__main__':
    unittest.main()

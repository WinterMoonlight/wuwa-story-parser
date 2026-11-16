import unittest
from unittest.mock import patch
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_guide_new.db').exists(), 'Local ConfigDB required')
class GuideTests(unittest.TestCase):
    def test_real_links_platform_variants_and_page_order(self):
        from wuwa_story.guides import inspect_guide
        from wuwa_story.database import rows
        movement = inspect_guide({'Type': 'BeginnerGuide', 'GuideId': 10001}, rows)
        self.assertEqual(movement['step_ids'], [1, 4, 10001])
        self.assertEqual([s['platform_mask_raw'] for s in movement['steps']], ['TFF', 'FFT', 'FTF'])
        self.assertIn('{0}', movement['texts'][0]['raw_text'])
        self.assertTrue(all(not s['display_verified'] for s in movement['steps']))
        tutorial = inspect_guide({'Type': 'BeginnerGuide', 'GuideId': 30014}, rows)
        self.assertEqual([p['page_id'] for p in tutorial['steps'][0]['pages']], [16, 3001401])
        self.assertTrue(all(not t['missing'] for t in tutorial['texts']))

    def test_missing_duplicate_unknown_refs_and_texts(self):
        from wuwa_story.guides import inspect_guide
        from wuwa_story.database import rows
        params = {'Type': 'BeginnerGuide', 'GuideId': 10001}
        for mode in ('missing', 'duplicate'):
            def source(db, table):
                rs = rows(db, table)
                if table == 'guidestep':
                    return [r for r in rs if r['Id'] != 1] if mode == 'missing' else rs + [next(r for r in rs if r['Id'] == 1)]
                return rs
            with self.assertRaises(ValueError):
                inspect_guide(params, source)
        with patch('wuwa_story.guides.integer', return_value=999):
            with self.assertRaises(ValueError):
                inspect_guide(params, rows)
        with patch('wuwa_story.guides.texts', {}):
            result = inspect_guide(params, rows)
            self.assertTrue(all(t['missing'] for t in result['texts']))
        with self.assertRaises(ValueError):
            inspect_guide({**params, 'Type': 'Unknown'}, rows)

    def test_upper_conditions_and_coverage(self):
        from wuwa_story.export_task import Exporter
        d = Exporter(allow_incomplete=True).export(139000025)
        entries = [e for e in d['external_content'] if 'guide' in e]
        self.assertEqual(len(entries), 25)
        self.assertEqual(sum(len(e['guide']['steps']) for e in entries), 60)
        self.assertEqual(sum(len(e['texts']) for e in entries), 72)
        combat = next(e for e in entries if e['guide_id'] == 10054)
        self.assertEqual(combat['guide']['trigger_conditions'], [{'Type': 'CheckInCombat', 'InCombat': True}])
        self.assertFalse(combat['guide']['display_verified'])
        self.assertTrue(all('text' in t for e in entries for t in e['texts']))
        self.assertEqual(d['validation']['confirmed_missing_text_ids'], [])
        self.assertEqual(d['validation']['status'], 'needs_review')

import unittest
from collections import Counter
from unittest.mock import patch
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_PhoneMsg.db').exists(), 'Local ConfigDB required')
class PhoneTaskTests(unittest.TestCase):
    def test_real_task_and_message_ownership(self):
        from wuwa_story.export_task import Exporter
        d = Exporter(allow_incomplete=True).export(165800001)
        self.assertEqual(Counter(e['kind'] for e in d['events']), {'dialogue': 53, 'choice': 6})
        entry = next(e for e in d['external_content'] if 'phone' in e)
        self.assertEqual((entry['quest_id'], entry['node_id'], entry['phase']), (165800001, 3, 'FinishActions'))
        p = entry['phone']
        self.assertEqual(p['contacts'][0]['name'], '洛瑟菈')
        self.assertEqual(Counter(e['kind'] for e in p['events']), {'dialogue': 12, 'choice': 2})
        self.assertEqual(p['state_key'], '剧情_3_2_拉海洛主线_下半_16_1')
        self.assertNotIn(p['state_key'], [s['state_key'] for s in d['source']['scenes']])
        self.assertFalse(p['read_time_verified'])
        self.assertEqual(p['route']['gender'], 'female')
        self.assertEqual(d['validation']['missing_text_ids'], [])
        self.assertEqual(d['validation']['status'], 'needs_review')
        switch = next(e for e in d['external_content'] if e['source_action']['Name'] == 'SwitchSubLevels')
        self.assertEqual(switch['node_id'], 16)
        self.assertTrue(any(n.get('DungeonId') == 2518 for n in switch['ancestry']))

    def test_missing_ambiguous_and_unknown_phone_type_rejected(self):
        from wuwa_story.phone import inspect_phone
        from wuwa_story.database import rows
        params = {'InteractType': {'Type': 'SendPhoneMessage', 'PhoneRecordActionConfig': {'PhoneMessageId': 32010}}}
        for mode in ('missing', 'duplicate'):
            def source(db, table):
                rs = rows(db, table)
                if table == 'shortmessage':
                    r = next(r for r in rs if r['Id'] == 32010)
                    return [] if mode == 'missing' else [r, r]
                return rs
            with self.assertRaises(ValueError):
                inspect_phone(params, source)
        with patch('wuwa_story.phone.integer', return_value=99999999):
            with self.assertRaises(ValueError):
                inspect_phone(params, rows)

    def test_phone_missing_text_propagates_to_task(self):
        from wuwa_story.export_task import Exporter
        from wuwa_story.database import texts
        key = 'Main_LahaiRoi_YMDDDTY_75_1'
        modified = dict(texts); modified.pop(key)
        with patch('wuwa_story.export_task.texts', modified):
            d = Exporter(allow_incomplete=True).export(165800001)
        self.assertIn(key, d['validation']['confirmed_missing_text_ids'])

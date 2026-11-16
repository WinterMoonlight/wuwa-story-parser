import unittest
from collections import Counter
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_mail.db').exists(), 'Local ConfigDB required')
class MailTaskTests(unittest.TestCase):
    def test_real_mail_ownership_and_incomplete_export(self):
        from wuwa_story.export_task import Exporter
        d = Exporter(allow_incomplete=True).export(171000004)
        self.assertEqual(d['validation']['exported_flow_count'], 7)
        self.assertEqual(len(d['events']), 71)
        self.assertEqual(d['validation']['status'], 'needs_review')
        self.assertEqual(d['validation']['confirmed_missing_text_ids'], [])
        mail = next(e for e in d['external_content'] if e['source_action']['Name'] == 'SendNpcMail')
        self.assertEqual((mail['quest_id'], mail['node_id'], mail['phase']), (171000004, 6, 'EnterActions'))
        self.assertEqual(mail['mail_id'], 250000)
        self.assertEqual(mail['present_fields'], [0])
        self.assertNotIn('texts', mail)
        self.assertEqual(mail['read_condition_nodes'][0]['node_id'], 6)
        self.assertEqual([n['Id'] for n in mail['ancestry']], [6, 5, 2, 1])
        self.assertFalse(mail['global_runtime_order_verified'])
        teleport = next(e for e in d['external_content'] if e['source_action']['Name'] == 'TeleportDungeon')
        self.assertEqual(teleport['phase'], 'Actions')
        self.assertEqual(teleport['transition']['Mp4Path'], 'M0278')
        with self.assertRaises(ValueError):
            Exporter().export(171000004)

    def test_missing_duplicate_and_new_mail_schema_rejected(self):
        from wuwa_story.external import inspect_task_content
        from wuwa_story.database import rows
        node = {'Id': 1, 'Type': 'Sequence', 'ParentNodeId': 0,
                'EnterActions': [{'Name': 'SendNpcMail', 'Params': {'MailId': 250000}}]}
        original = next(r for r in rows('db_mail.db', 'mail') if r['MailId'] == 250000)
        for candidates in ([], [original, original],
                           [{'MailId': 250000, 'BinData': rows('db_guide_new.db', 'guidegroup')[0]['BinData']}]):
            with self.assertRaises(ValueError):
                inspect_task_content([node], lambda *args: candidates)

    def test_icon_action_does_not_change_identity(self):
        from wuwa_story.export_task import Exporter
        e = Exporter(); e.state_key = 'test'
        e.action({'Name': 'SetHeadIconVisible', 'Params': {'HeadStyleConfig': {'Type': 1, 'WhoId': 1413}, 'Visible': True}})
        self.assertEqual(e.events, [])
        self.assertEqual(e.speakers.actors, [])

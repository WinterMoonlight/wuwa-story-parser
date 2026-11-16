import unittest
from wuwa_story.paths import DATABASE_DIR


@unittest.skipUnless((DATABASE_DIR / 'db_QuestData.db').exists(), 'Local ConfigDB required')
class ScanDiagnosticsTests(unittest.TestCase):
    def test_lists_all_unknown_actions_and_nested_content_calls(self):
        from wuwa_story.scan import diagnose_actions
        value = [{'Name': '对话2', 'Id': 2},
                 {'Name': 'UnsupportedFirst', 'Params': {}},
                 {'Name': 'PlayMovie', 'Params': {'VideoName': 'example'}},
                 {'Options': [{'Actions': [{'Name': 'SendNpcMail', 'Params': {'MailId': 7}}]}]}]
        unknown, channels = diagnose_actions(value, set(), 'test_state')
        self.assertEqual([a['name'] for a in unknown], ['UnsupportedFirst', 'PlayMovie', 'SendNpcMail'])
        self.assertEqual([a['channel'] for a in channels], ['视频及字幕', '邮件'])
        self.assertEqual(channels[-1]['params']['MailId'], 7)
        self.assertTrue(all(a['owner'] == 'test_state' for a in unknown))

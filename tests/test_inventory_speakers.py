import unittest
from types import SimpleNamespace
from unittest.mock import patch

from wuwa_story.reading_batch import inventory
from wuwa_story.reading import coverage_reading_text
from wuwa_story.speakers import SpeakerResolver


class InventorySpeakerTests(unittest.TestCase):
    def setUp(self):
        self.speakers = SimpleNamespace(records={
            1: {'name': '秧秧', 'source': 'fixture'},
            2: {'name': '？？？', 'source': 'fixture'},
        })

    def read(self, value):
        with patch('wuwa_story.reading_batch.texts', {'a': '你好', 'b': '好的', 'c': '数日后'}):
            return inventory(value, 'flow', speakers=self.speakers)

    def test_choice_does_not_inherit_npc_and_nested_talk_uses_own_id(self):
        result = self.read({'Type': 'Talk', 'WhoId': 1, 'TidTalk': 'a',
                            'Options': [{'TidTalkOption': 'b', 'Actions': [
                                {'Type': 'Talk', 'WhoId': 2, 'TidTalk': 'a'}]}]})
        self.assertEqual([r['display_name'] for r in result], ['秧秧', '漂泊者', '？？？'])
        self.assertEqual([r['kind'] for r in result], ['dialogue', 'choice', 'dialogue'])
        self.assertIsNone(result[1]['who_id'])
        self.assertEqual(result[1]['inherited_who_id'], 1)
        self.assertTrue(all(not r['order_verified'] for r in result))

    def test_missing_identity_does_not_borrow_parent_or_previous_sibling(self):
        result = self.read({'WhoId': 1, 'Items': [{'TidTalk': 'a'},
                           {'WhoId': 9999, 'TidTalk': 'a'}, {'WhoId': 2, 'TidTalk': 'a'}]})
        self.assertEqual([r['display_name'] for r in result], ['？？？'] * 3)
        self.assertTrue(all(r['identity_status'] == 'unresolved' for r in result))

    def test_screen_qte_and_unknown_options_are_not_player_speech(self):
        result = self.read([{'WhoId': 1, 'TidCenterText': 'c'},
                            {'Type': 'QTE', 'Options': [{'TidTalkOption': 'b'}]},
                            {'Type': 'SystemOption', 'Options': [{'TidTalkOption': 'b'}]},
                            {'Type': 'Unknown', 'Options': [{'TidTalkOption': 'b'}]}])
        self.assertEqual([r['kind'] for r in result],
                         ['screen_text', 'qte_result', 'system_option', 'unknown_option'])
        self.assertEqual([r['display_name'] for r in result],
                         ['画面文字', 'QTE结果文字', '系统选项', '？？？'])

    def test_failure_scope_and_reading_labels_are_preserved(self):
        with patch('wuwa_story.reading_batch.texts', {'a': '再见'}):
            result = inventory({'Type': 'Talk', 'WhoId': 1, 'TidTalk': 'a',
                                'Options': [{'TidTalkOption': 'a'}]}, 'flow',
                               'failure_ending', speakers=self.speakers)
        self.assertTrue(all(r['category'] == 'failure_ending' for r in result))
        text = coverage_reading_text({'title': '测试', 'batch_coverage': {
            'status': 'inventory_only', 'records': result, 'gaps': [],
            'order': {'selected_route_verified': False}}})
        self.assertIn('秧秧：再见', text)
        self.assertIn('漂泊者【选择】：再见', text)
        self.assertIn('失败分支', text)

    def test_real_suisui_name_and_player_option(self):
        speakers = SpeakerResolver()
        result = inventory({'Type': 'Talk', 'WhoId': 350099, 'TidTalk': 'example',
                            'Options': [{'TidTalkOption': 'example'}]}, 'fixture', speakers=speakers)
        self.assertEqual(result[0]['display_name'], '穗穗')
        self.assertEqual(result[0]['name_source']['source'], 'BinData.Name(field3)')
        self.assertEqual(result[1]['display_name'], '漂泊者')


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch

from wuwa_story.reading_batch import inventory, ending_category, analyze, external_inventory
from wuwa_story.reading import reading_text


class ReadingBatchTests(unittest.TestCase):
    def test_inventory_options_and_stale_container(self):
        value = {'Type': 'Option', 'TidTalk': 'stale', 'Options': [{'TidTalkOption': 'choice'}]}
        with patch('wuwa_story.reading_batch.texts', {'choice': '{PlayerName}{MALE=哥;FEMALE=姐}'}):
            records = inventory(value, 'state')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['category'], 'candidate_branch')
        self.assertEqual(records[0]['text'], '漂泊者姐')
        self.assertFalse(records[0]['order_verified'])

    def test_shared_card_not_failure_only(self):
        self.assertEqual(ending_category(5, [{'CardId': 5, 'IsSuccess': False}]), 'failure_ending')
        self.assertEqual(ending_category(5, [{'CardId': 5, 'IsSuccess': False},
                                            {'CardIds': [5], 'IsSuccess': True}]), 'unverified')
        self.assertEqual(ending_category(None, []), 'unverified')

    def test_failed_route_keeps_no_partial_events(self):
        with patch('wuwa_story.reading_batch.Exporter') as cls:
            cls.return_value.events = [{'text': 'partial'}]
            cls.return_value.export.side_effect = ValueError('blocked')
            result = analyze({'Id': 1, 'TidName': 'task'}, [], {}, {}, None, {'status': 'unsupported'})
        self.assertEqual(result['events'], [])
        self.assertFalse(result['validation']['complete_for_supported_task_shape'])
        self.assertEqual(result['batch_coverage']['status'], 'inventory_only')
        self.assertIn('未提取到可阅读正文', reading_text(result))
        self.assertNotIn('blocked', reading_text(result))

    def test_external_failure_does_not_hide_following_call(self):
        nodes = [{'Id': 1, 'Actions': [{'Name': 'SetVar', 'Params': {}},
                                       {'Name': 'CommonTip', 'Params': {}},
                                       {'Name': 'Wait', 'Params': {'Time': 1}}]}]
        class Source:
            rows = None
        with patch('wuwa_story.reading_batch.inspect_task_content', side_effect=[ValueError('bad'), [{'texts': []}] ]):
            entries, gaps = external_inventory(nodes, Source())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['original_action_index'], 1)
        self.assertEqual(entries[0]['original_preceding_actions'], nodes[0]['Actions'][:1])
        self.assertEqual(entries[0]['original_following_actions'], nodes[0]['Actions'][2:])
        self.assertEqual(gaps[0]['action_index'], 0)
        self.assertEqual(len(nodes[0]['Actions']), 3)

    def test_missing_key_is_explicit(self):
        with patch('wuwa_story.reading_batch.texts', {}):
            item = inventory({'TidTalk': 'absent'}, 's')[0]
        self.assertTrue(item['missing'])
        self.assertEqual(item['raw_text'], '')


if __name__ == '__main__':
    unittest.main()

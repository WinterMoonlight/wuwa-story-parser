import unittest
from collections import Counter
from unittest.mock import patch
from wuwa_story.database import rows, integer
from wuwa_story.export_task import Exporter, option_container
from wuwa_story.phone import inspect_phone
from wuwa_story.reading import reading_text


class PhoneDecodingTests(unittest.TestCase):
    def test_all_message_partner_ids_join(self):
        partners = {r['Id'] for r in rows('db_PhoneMsg.db', 'chatpartner')}
        messages = rows('db_PhoneMsg.db', 'shortmessage')
        self.assertTrue(messages)
        self.assertTrue(all(integer(r['BinData'], 1) in partners for r in messages))

    def test_empty_option_is_control_and_wait_is_retained(self):
        item = {'Type': 'Option', 'Id': 0, 'TidTalk': 'not-a-line', 'PlotLineKey': '',
                'Actions': [{'Name': 'Wait', 'Params': {'Time': 2.5}}]}
        self.assertTrue(option_container(item))
        self.assertFalse(option_container({**item, 'TextId': 1}))
        self.assertFalse(option_container({**item, 'PlotLineKey': 'real-line'}))
        parser = Exporter();parser.state_key = 'test'
        parser.talk([item])
        self.assertEqual(parser.events, [])
        self.assertEqual(parser.missing, [])
        self.assertEqual(parser.action_log[0]['Name'], 'Wait')

    def test_real_phone_system_tip_image_and_contact(self):
        params = {'InteractType': {'Type': 'SendPhoneMessage', 'PhoneRecordActionConfig': {'PhoneMessageId': 36009}}}
        phone = inspect_phone(params, rows)
        self.assertEqual(phone['contacts'][0]['id'], 72)
        self.assertEqual(phone['contacts'][0]['name'], '清宵')
        self.assertEqual(phone['state_key'], '剧情_3_6_后日谈生态_2_1')
        self.assertEqual(Counter(e['kind'] for e in phone['events']),
                         {'dialogue': 13, 'choice': 4, 'system_tip': 1, 'attachment': 1})
        self.assertEqual(phone['attachments'][0]['attachment_id'], 800003)
        self.assertFalse(phone['attachments'][0]['visual_content_verified'])
        self.assertEqual(phone['missing_text_ids'], [])
        self.assertFalse(any(e['display_name'].startswith('{message}') for e in phone['events']))
        with patch('wuwa_story.phone.string', wraps=__import__('wuwa_story.phone', fromlist=['string']).string) as read:
            # Unknown image types may not be presented as an image.
            original = read._mock_wraps
            read.side_effect = lambda b, i: 'Unknown' if i == 2 else original(b, i)
            with self.assertRaisesRegex(ValueError, 'attachment type'):
                inspect_phone(params, rows)

    def test_task_false_missing_removed_without_inventing_line(self):
        r = Exporter(allow_incomplete=True).export(936800000)
        self.assertEqual(len(r['events']), 95)
        self.assertEqual(r['validation']['missing_text_ids'], [])
        controls = [n for group in r['validation']['talk_groups'] for n in group['non_dialogue_option_containers']]
        self.assertTrue(any(n.get('TidTalk') == 'Flow_936000004_147' for n in controls))
        text = reading_text(r)
        self.assertIn('对方戳了戳你', text)
        self.assertNotIn('dnt/无文本手机短信类型', text)
        self.assertNotIn('{message}', text)
        self.assertFalse(r['validation']['complete_for_supported_task_shape'])


if __name__ == '__main__': unittest.main()

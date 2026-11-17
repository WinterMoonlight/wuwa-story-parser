import copy
import unittest

from wuwa_story.phone import apply_phone_media_item, inspect_message
from wuwa_story.database import rows


class PhoneMediaTests(unittest.TestCase):
    def test_exact_shapes_preserve_source_and_voice_text(self):
        original = {'kind': 'dialogue', 'text': '正文', 'raw_text': '原文',
                    'source_item': {'TidTalk': 'id', 'MessageType': {'Type': 'Voice'}}}
        event = copy.deepcopy(original)
        self.assertTrue(apply_phone_media_item(event, {'Type': 'Voice'}))
        self.assertEqual(event['source_item'], original['source_item'])
        self.assertEqual(event['text'], '正文')
        self.assertFalse(event['phone_media']['audio_content_verified'])
        self.assertFalse(apply_phone_media_item({}, {'Type': 'Voice', 'Callback': []}))
        self.assertFalse(apply_phone_media_item({}, {'Type': 'Unknown'}))
        for value in (True, 0, -1, '229', None):
            with self.assertRaises(ValueError):
                apply_phone_media_item({}, {'Type': 'Emoji', 'EmojiId': value})
        with self.assertRaises(ValueError):
            apply_phone_media_item({}, {'Type': 'Emoji', 'EmojiId': 229, 'Next': 1})

    def test_emoji_placeholder_does_not_turn_metadata_into_dialogue(self):
        for text in ('dnt/无文本手机短信类型', '期待、求求的表情', '[缺失文本：id]'):
            event = {'raw_text': text, 'text': text, 'source_item': {'MessageType': {'Type': 'Emoji', 'EmojiId': 229}}}
            source = copy.deepcopy(event['source_item'])
            self.assertTrue(apply_phone_media_item(event, source['MessageType']))
            self.assertEqual(event['text'], '【表情：图片内容尚未核验】')
            self.assertEqual(event['raw_text'], text)
            self.assertEqual(event['source_item'], source)
            self.assertFalse(event['phone_media']['visual_content_verified'])

    def test_real_phone_sequences_keep_order_and_missing_evidence(self):
        expected = {32000: 14, 32001: 9, 33003: 3, 34001: 5, 35000: 21,
                    35001: 20, 35002: 29, 35003: 12, 35004: 22, 35005: 27,
                    35006: 32, 35007: 24, 36000: 15, 38005: 31}
        for mid, count in expected.items():
            with self.subTest(message=mid):
                result = inspect_message(mid, rows)
                self.assertEqual(len(result['events']), count)
                self.assertFalse(result['read_time_verified'])
                for event in result['events']:
                    media = event.get('phone_media', {})
                    if media.get('type') == 'Voice':
                        self.assertTrue(event.get('text_id'))
                        self.assertEqual(event['source_item']['TidTalk'], event['text_id'])
                    if media.get('type') == 'Emoji':
                        self.assertEqual(event['text'], '【表情：图片内容尚未核验】')
        result = inspect_message(34001, rows)
        self.assertIn('Main_LahaiRoi_WMXZTK_1_1', result['missing_text_ids'])
        result = inspect_message(38005, rows)
        emoji = next(i for i, e in enumerate(result['events']) if e.get('phone_media', {}).get('type') == 'Emoji')
        self.assertEqual(result['events'][emoji]['talk_id'], 26)
        self.assertEqual(emoji, len(result['events']) - 1)


if __name__ == '__main__':
    unittest.main()

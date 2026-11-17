import unittest
from unittest.mock import patch

from wuwa_story.database import rows, texts
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.reading_batch import inventory
from wuwa_story.text_refs import control_references, non_dialogue_reason
from wuwa_story.rendering import render_result


class TextReferenceTests(unittest.TestCase):
    def test_no_text_preserves_actions_but_never_becomes_dialogue(self):
        item = {'Type': 'NoTextItem', 'Id': 0, 'TextId': 3,
                'PlotLineKey': 'stale-key', 'TidTalk': 'stale-key',
                'Actions': [{'Name': 'Wait', 'Params': {'Time': 2}}]}
        with patch.dict(texts, {'stale-key': 'dnt/无文本演出'}):
            parser = Exporter(); parser.state_key = 'test'
            parser.talk([item])
            self.assertEqual(parser.events, [])
            self.assertEqual(parser.missing, [])
            self.assertEqual(parser.action_log[0]['Name'], 'Wait')
            self.assertEqual(inventory([item], 'test'), [])
            control = parser.talk_coverage[0]['non_dialogue_controls'][0]
            self.assertEqual(control['raw_text'], 'dnt/无文本演出')
            self.assertEqual(control['source_item'], item)

    def test_qte_is_not_an_arbitrary_choice(self):
        item = {'Type': 'QTE', 'Id': 0, 'QteId': 1, 'TidTalk': 'not-a-line',
                'Options': [{'TidTalkOption': 'success-label',
                             'TypeParams': {'Type': 'QteSucceed'}}]}
        parser = Exporter(); parser.state_key = 'test'
        with self.assertRaisesRegex(ValueError, 'QTE runtime'):
            parser.talk([item])
        self.assertEqual(parser.events, [])
        records = inventory([item], 'test')
        self.assertEqual([r['text_id'] for r in records], ['success-label'])
        self.assertEqual(control_references([item], {})[0]['source_item'], item)

    def test_missing_speech_is_not_hidden_by_empty_plot_key(self):
        for kind in ('Talk', 'Unknown'):
            item = {'Type': kind, 'Id': 0, 'TidTalk': 'missing-body', 'PlotLineKey': ''}
            self.assertIsNone(non_dialogue_reason(item))
            self.assertTrue(inventory([item], 'test')[0]['missing'])

    def test_phone_visuals_keep_their_position_without_missing_speech(self):
        for message in ({'Type': 'Emoji', 'EmojiId': 172},
                        {'Type': 'Attachment', 'AttachmentId': 700022}):
            with self.subTest(message=message):
                item = {'Type': 'PhoneMessage', 'Id': 1, 'WhoId': 750088,
                        'TidTalk': 'absent-visual-label', 'MessageType': message}
                parser = Exporter()
                parser.state_key = 'test'
                parser.talk([item])
                result = render_result({'title': 'test', 'events': parser.events,
                                        'route': {'choices': []}})
                self.assertEqual(parser.missing, [])
                self.assertEqual(len(result['events']), 1)
                self.assertEqual(result['events'][0]['source_item'], item)
                self.assertEqual(result['events'][0]['phone_media']['type'], message['Type'])
                record = inventory([item], 'test')[0]
                self.assertFalse(record['missing'])
                self.assertEqual(record['text'], result['events'][0]['text'])

    def test_phone_text_and_unknown_shapes_still_report_missing_body(self):
        for message in ({'Type': 'Voice'}, {'Type': 'Text'},
                        {'Type': 'Emoji', 'EmojiId': True},
                        {'Type': 'Attachment', 'AttachmentId': 0},
                        {'Type': 'Emoji', 'EmojiId': 172, 'Extra': 'unknown'}):
            item = {'Type': 'PhoneMessage', 'Id': 1, 'TidTalk': 'absent-body',
                    'MessageType': message}
            parser = Exporter()
            parser.state_key = 'test'
            parser.talk([item])
            self.assertIn('absent-body', parser.missing)
            self.assertTrue(inventory([item], 'test')[0]['missing'])

    def test_real_seven_task_sources(self):
        states = {r['StateKey']: r for r in rows('db_flowState.db', 'flowstate')}
        expected = {
            '剧情_2_6_狄斯台地主线_上半_1_4_5': 1,
            '剧情_2.8千夏活动主线_17_1': 0,
            '剧情_3_0_拉海洛主线_下半_2_4_5': 0,
            '剧情_3_1_拉海洛主线_上半_3_57_1': 0,
            '剧情_3_4_拉海洛主线_4_3': 0,
            '剧情_3_5_穗穗线_玩法副本_1_1_9': 0,
            '剧情_3_5_穗穗线_玩法副本_1_3_19': 0,
            '剧情_3_5_穗穗线_玩法副本_1_4_1': 0,
            '剧情_3_5_穗穗线_玩法副本_1_6_1': 0,
            '剧情_3_7_主线沙盘_1_3': 0,
        }
        for key, missing in expected.items():
            actions, _ = flow_actions(states[key]['BinData'])
            self.assertEqual(sum(r['missing'] for r in inventory(actions, key)), missing, key)
        actions, _ = flow_actions(states['剧情_3_5_穗穗线_玩法副本_1_6_1']['BinData'])
        controls = control_references(actions, texts)
        self.assertTrue(any(c['source_item'].get('QteId') == 9035003 for c in controls))
        self.assertTrue(any(c['source_item'].get('Actions') for c in controls))


if __name__ == '__main__':
    unittest.main()

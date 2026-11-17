import copy
import json
import tempfile
import unittest
from pathlib import Path
from wuwa_story.paths import DATABASE_DIR


class ReadingTests(unittest.TestCase):
    def test_controls_hidden_and_short_notes_retained(self):
        from wuwa_story.reading import reading_text
        d = {'title': '示例', 'events': [{'kind': 'quest_control', 'text': '内部控制'},
             {'kind': 'dialogue', 'display_name': '甲', 'text': '你好'}],
             'external_content': [{'status': 'mail_body_unavailable_in_row', 'node_id': 9}],
             'validation': {'status': 'needs_review'}}
        text = reading_text(d)
        self.assertIn('甲：你好', text)
        self.assertIn('正文尚未找到', text)
        self.assertNotIn('内部控制', text)
        self.assertNotIn('node_id', text)

    @unittest.skipUnless((DATABASE_DIR / 'db_Reigns.db').exists(), 'Local ConfigDB required')
    def test_reigns_reading_and_json_evidence_preserved(self):
        from wuwa_story.export_task import Exporter, write_result
        d = Exporter(allow_incomplete=True).export(164000000)
        before = copy.deepcopy(d)
        with tempfile.TemporaryDirectory() as temp:
            paths = write_result(d, Path(temp), quiet=True)
            text = paths[1].read_text(encoding='utf-8-sig')
            self.assertEqual(json.loads(paths[0].read_text(encoding='utf-8')), before)
        self.assertEqual(d, before)
        for token in ('FinishActions', 'SetVar', '祖先链', '同阶段前序', 'ReignsAddBuff', '/Game/', 'source_path'):
            self.assertNotIn(token, text)
        self.assertEqual(text.count('【小游戏·第'), 4)
        self.assertIn('可选回应：', text)
        self.assertIn('部分结局卡文本尚未找到', text)
        for event in d['events']:
            self.assertIn(event['text'], text)
        for entry in d['external_content']:
            if 'gameplay' in entry:
                for value in entry['texts']:
                    if value['text']:
                        from wuwa_story.reading_markup import reading_markup
                        self.assertIn(reading_markup(value['text']), text)

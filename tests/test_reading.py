import copy
import json
import tempfile
import unittest
from pathlib import Path
from wuwa_story.paths import DATABASE_DIR
from wuwa_story.reading_markup import reading_markup


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
            document = json.loads(paths[0].read_text(encoding='utf-8'))
            self.assertEqual(document.pop('mainline_reading')['policy'], 'mainline_first')
            self.assertEqual(document, before)
        self.assertEqual(d, before)
        for token in ('FinishActions', 'SetVar', '祖先链', '同阶段前序', 'ReignsAddBuff', '/Game/', 'source_path'):
            self.assertNotIn(token, text)
        self.assertNotIn('【小游戏·第', text)
        self.assertNotIn('【卡牌文本】', text)
        for event in d['events']:
            self.assertIn(reading_markup(event['text']), text)
        self.assertTrue(any('gameplay' in entry for entry in document['external_content']))

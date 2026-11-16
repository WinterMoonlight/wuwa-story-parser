import json
import tempfile
import unittest
from pathlib import Path
from wuwa_story.refresh_reading import refresh_reading


class RefreshReadingTests(unittest.TestCase):
    def test_refresh_preserves_json_and_skips_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = {'quest_id': 1, 'title': '任务', 'events': [
                {'kind': 'dialogue', 'display_name': '角色', 'text': '对白'}],
                'validation': {}, 'source': {'node': 42}}
            file = root / '1.json'
            raw = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8')
            file.write_bytes(raw)
            file.with_suffix('.txt').write_text('旧技术记录', encoding='utf-8')
            report = root / 'report.json'
            report.write_text('[]', encoding='utf-8')
            first = refresh_reading(root)
            self.assertEqual(first['task_files'], 1)
            self.assertEqual(first['txt_changed'], 1)
            self.assertEqual(file.read_bytes(), raw)
            self.assertIn('角色：对白', file.with_suffix('.txt').read_text(encoding='utf-8-sig'))
            self.assertFalse(report.with_suffix('.txt').exists())
            second = refresh_reading(root)
            self.assertEqual(second['txt_changed'], 0)
            self.assertEqual(file.read_bytes(), raw)

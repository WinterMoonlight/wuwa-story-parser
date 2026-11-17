import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wuwa_story.audit_missing import audit


class MissingAuditTests(unittest.TestCase):
    def test_locates_selected_event_pointers_and_classifies_media(self):
        items = [
            {'Type': 'Talk', 'TidTalk': 'body'},
            {'Type': 'PhoneMessage', 'TidTalk': 'image',
             'MessageType': {'Type': 'Attachment', 'AttachmentId': 9}},
        ]
        result = {
            'events': [{'state_key': 'state', 'text_id': item['TidTalk'],
                        'source_item': item} for item in items],
            'batch_coverage': {'records': [
                {'pointer': '/events/0', 'text': '[缺失文本：body]'},
                {'pointer': '/events/1', 'text': '【附件】'},
            ]},
        }
        report = {'tasks': [{'quest_id': 1, 'title': 'test', 'files': ['task.json'],
                             'gaps': [{'kind': 'missing_text', 'text_ids': ['body', 'image']}]}]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'report.json').write_text(json.dumps(report), encoding='utf-8')
            (root / 'task.json').write_text(json.dumps(result), encoding='utf-8')
            with patch('wuwa_story.audit_missing.P', root), \
                    patch('wuwa_story.audit_missing.rows', return_value=[{'StateKey': 'state', 'BinData': b'source'}]):
                evidence = audit(root / 'report.json')
        refs = evidence['tasks'][0]['references']
        self.assertEqual([r['classification'] for r in refs],
                         ['unresolved_body_reference', 'media_reference'])
        self.assertEqual(evidence['tasks'][0]['unlocated_report_keys'], [])
        self.assertEqual(refs[0]['source_item'], items[0])


if __name__ == '__main__':
    unittest.main()

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from wuwa_story.reading_review import export_review


class ReadingReviewTests(unittest.TestCase):
    def test_review_is_bound_to_input_and_survives_reading_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = {'quest_id':1, 'title':'任务', 'events':[], 'route':{'choices':[]},
                      'validation':{}, 'batch_coverage':{'reading_acceptance':{}, 'status':'inventory_only',
                       'records':[], 'gaps':[], 'order':{'selected_route_verified':False}}}
            (root/'a.json').write_text(json.dumps(result), encoding='utf-8')
            (root/'a.txt').write_text('source', encoding='utf-8')
            (root/'覆盖报告.json').write_text(json.dumps({'tasks':[{'quest_id':1,'files':['a.json','a.txt']}]}),encoding='utf-8')
            review={'review_id':'test','tasks':[{'quest_id':1,'verdict':'readable_with_gaps',
                    'summary':'主干已检查', 'limitations':['演出待核验'], 'checks':{'order':'reviewed'},
                    'source_json_sha256':hashlib.sha256((root/'a.json').read_bytes()).hexdigest(),
                    'source_txt_sha256':hashlib.sha256((root/'a.txt').read_bytes()).hexdigest()}]}
            (root/'review.json').write_text(json.dumps(review),encoding='utf-8')
            prepared=export_review(root,root/'review.json',root/'out')
            self.assertFalse(prepared[0]['batch_coverage']['reading_acceptance']['accepted'])
            txt=next((root/'out').glob('*.txt')).read_text(encoding='utf-8-sig')
            self.assertIn('带明确缺口可阅读',txt)
            self.assertIn('演出待核验',txt)
            (root/'a.txt').write_text('changed',encoding='utf-8')
            with self.assertRaises(ValueError):
                export_review(root,root/'review.json',root/'stale')
            self.assertFalse((root/'stale').exists())

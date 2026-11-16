import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from wuwa_story.paths import DATABASE_DIR

HAS_DATA = (DATABASE_DIR / 'db_QuestData.db').exists()


@unittest.skipUnless(HAS_DATA, 'Local ConfigDB required')
class BatchTests(unittest.TestCase):
    def test_mixed_condition_types_are_reportable(self):
        from wuwa_story.batch import observed_features
        data = observed_features([{'Type': 'Condition', 'Condition': {'Type': 0}},
                                  {'Type': 'ChildQuest', 'Condition': {'Type': 'ReachArea'}}])
        self.assertEqual(data['step_conditions'], ['0', 'ReachArea'])

    def test_full_batch_is_partitioned_and_failures_have_no_task_files(self):
        from wuwa_story import batch
        with tempfile.TemporaryDirectory() as temp, patch.object(batch, 'O', Path(temp)):
            root, report = batch.export_mainline()
            records = report['records']
            self.assertEqual(len(records), len({r['quest_id'] for r in records}))
            self.assertTrue(any(r['status'] == 'unsupported' for r in records))
            success = [r for r in records if r['status'] == 'exported']
            self.assertIn(880000013, [r['quest_id'] for r in success])
            expected = {root / f for r in success for f in r['files']}
            actual = set(root.rglob('*.txt')) | {p for p in root.rglob('*.json') if p.parent != root}
            self.assertEqual(actual, expected)
            failed = json.loads((root / '暂不支持任务.json').read_text(encoding='utf-8'))
            self.assertEqual(len(failed) + len(success), len(records))
            for r in success:
                result = json.loads((root / r['files'][0]).read_text(encoding='utf-8'))
                self.assertEqual(result['classification']['chapter']['id'], r['chapter']['id'])
                self.assertEqual(result['rendering']['gender'], 'female')
                self.assertEqual(result['validation']['missing_text_ids'], [])

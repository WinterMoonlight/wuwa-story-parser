import unittest

from wuwa_story.database import rows, texts
from wuwa_story.reference_diagnostics import audio_index, diagnose_missing


class ReferenceDiagnosticsTests(unittest.TestCase):
    def test_real_missing_speech_kept_despite_matching_voice(self):
        key = 'Main_Linaxita_2_9_605_1'
        state = '剧情_2_6_狄斯台地主线_上半_1_4_5'
        record = {'missing': True, 'text_id': key, 'origin': state, 'source_path': [1]}
        result = diagnose_missing([record], set(), {state}, rows)[0]
        self.assertNotIn(key, texts)
        self.assertFalse(result['replacement_applied'])
        self.assertFalse(result['task_referenced'])
        self.assertTrue(result['recap_referenced'])
        self.assertEqual(result['audio_source']['audio_event'], 'vo_Main_Linaxita_2_9_60_1')
        self.assertEqual(result['shared_audio_candidates'][0]['raw_text'], '这个声音是……')
        self.assertNotIn(key, texts)

    def test_shared_audio_is_not_a_text_equivalence_relation(self):
        _, events = audio_index(rows)
        entries = events['vo_TZZNQ_8_1']
        self.assertGreater(len({texts[e['text_id']] for e in entries if texts.get(e['text_id'])}), 1)

    def test_absent_audio_does_not_synthesize_candidate(self):
        record = {'missing': True, 'text_id': 'absent', 'origin': 'test', 'source_path': []}
        result = diagnose_missing([record], {'test'}, set(), lambda *_: [])[0]
        self.assertEqual(result['shared_audio_candidates'], [])
        self.assertIsNone(result['audio_source'])
        self.assertEqual(result['status'], 'unresolved_body_reference')


if __name__ == '__main__':
    unittest.main()

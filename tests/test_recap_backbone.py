import json
import unittest
from pathlib import Path
from unittest.mock import patch

from wuwa_story.recap_backbone import build_backbone, duplicate_text_flows
from wuwa_story.reading import reading_text


class BackboneTests(unittest.TestCase):
    def test_failed_segment_is_transactional_and_next_segment_survives(self):
        entries = [{'Flow': {'FlowListName': 'f', 'FlowId': 1, 'StateId': n}} for n in (1, 2, 1)]
        class Parser:
            def __init__(self, **kwargs):
                self.events = []; self.decisions = []; self.action_log = []
                self.talk_coverage = []; self.unverified_content = []; self.missing = []
            def actions(self, actions):
                self.events.append({'kind': 'dialogue', 'raw_text': '你好', 'display_name': '甲'})
                if actions == 'bad':
                    raise ValueError('blocked after partial write')
        with patch('wuwa_story.recap_backbone.embedded', return_value=[(1, entries)]), \
             patch('wuwa_story.recap_backbone.flow_actions', side_effect=lambda b: (b.decode(), [1])), \
             patch('wuwa_story.recap_backbone.Exporter', Parser):
            b = build_backbone(1, [{'BinData': b'book'}],
                               {'f_1_1': {'BinData': b'good'}, 'f_1_2': {'BinData': b'bad'}}, None)
        self.assertEqual([s['status'] for s in b['segments']], ['parsed', 'blocked', 'parsed'])
        self.assertEqual(b['segments'][1]['events'][0]['kind'], 'recap_gap')
        self.assertNotIn('你好', str(b['segments'][1]['events']))
        self.assertEqual(b['parsed_segments'], 2)  # repeated recap occurrence is not collapsed

    def test_duplicates_require_identical_text_speakers_and_keep_recap_occurrences(self):
        r = {'text_id': 'a', 'raw_text': '相同', 'text': '相同', 'kind': 'dialogue', 'who_id': 1}
        inventories = {'a': [r], 'b': [dict(r)], 'c': [dict(r, who_id=2)], 'd': [dict(r)]}
        states = {k: {'BinData': k.encode()} for k in inventories}
        with patch('wuwa_story.recap_backbone.flow_actions', side_effect=lambda b: ([b.decode()], [1])):
            pairs = duplicate_text_flows(inventories, {'a', 'd'}, states)
        self.assertEqual([p['state_key'] for p in pairs], ['b'])
        self.assertFalse(pairs[0]['actions_equal'])
        self.assertFalse(pairs[0]['runtime_equivalence_verified'])

    def test_real_task_keeps_choices_in_context_and_gaps_in_place(self):
        from wuwa_story.recap_backbone import export_task_backbone
        d = export_task_backbone(145000004)
        b = d['recap_backbone']
        self.assertEqual((len(b['segments']), b['parsed_segments'], b['blocked_segments']), (92, 90, 2))
        self.assertEqual(sum(len(s['events']) for s in b['segments'] if s['status']=='parsed'), 986)
        self.assertTrue(any(e['kind']=='choice' for s in b['segments'] for e in s['events']))
        txt = reading_text(d)
        self.assertIn('漂泊者【选择】', txt.split('【附录：')[0])
        self.assertEqual(txt.count('依照你的命令，我只能到这里了。'), 1)
        self.assertEqual(txt.count('暂未解析，后续正文继续'), 2)
        self.assertEqual(d['batch_coverage']['status'], 'recap_draft')
        self.assertFalse(d['batch_coverage']['reading_acceptance']['accepted'])


if __name__ == '__main__':
    unittest.main()

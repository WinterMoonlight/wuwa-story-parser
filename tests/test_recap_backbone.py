import json
import unittest
from pathlib import Path
from unittest.mock import patch

from wuwa_story.recap_backbone import build_backbone, duplicate_text_flows
from wuwa_story.reading import reading_text


class BackboneTests(unittest.TestCase):
    def test_choice_override_reaches_normal_route_and_recap_fallback(self):
        from wuwa_story.recap_backbone import export_task_backbone
        # A normal successfully exported route must honour the same override as
        # the isolated recap fallback; otherwise selected reply and prose differ.
        first = export_task_backbone(211750002)
        key = first['route']['choices'][0]['choice_key']
        other = export_task_backbone(211750002, {key: 1})
        self.assertIn('Event_WWPDJSBF_4_5', [e.get('text_id') for e in other['events']])
        self.assertNotIn('Event_WWPDJSBF_4_4', [e.get('text_id') for e in other['events']])
        self.assertEqual(first['events'][3:], other['events'][3:])
        recap = export_task_backbone(145000004)
        segment = next(s for s in recap['recap_backbone']['segments']
                       if s.get('route', {}).get('choices') and
                       len(s['route']['choices'][0]['options']) > 1)
        decision = segment['route']['choices'][0]
        changed = export_task_backbone(145000004, {decision['choice_key']: 1})
        new_segment = next(s for s in changed['recap_backbone']['segments']
                           if s['entry_index'] == segment['entry_index'])
        actual = next(c for c in new_segment['route']['choices'] if c['choice_key'] == decision['choice_key'])
        self.assertEqual(actual['selected_index'], 1)
        self.assertEqual(next(e['text_id'] for e in new_segment['events']
                              if e.get('choice_key') == decision['choice_key']), decision['options'][1]['text_id'])
        self.assertEqual(recap['recap_backbone']['blocked_segments'], changed['recap_backbone']['blocked_segments'])

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

    def test_courtyard_reads_library_success_dialogue_before_boss_transition(self):
        from wuwa_story.reading_cases.courtyard import BOSS_INTRO, CONFRONTATION, LIBRARY_FLOW
        from wuwa_story.mainline_reading import build_mainline_reading
        from wuwa_story.recap_backbone import export_task_backbone

        result = export_task_backbone(139000031)
        segments = result['recap_backbone']['segments']
        index = next(i for i, segment in enumerate(segments) if segment['state_key'] == LIBRARY_FLOW)
        self.assertEqual(segments[index + 1]['state_key'], BOSS_INTRO)
        inserted = segments[index]['current_task_continuation']
        self.assertEqual(inserted['state_key'], CONFRONTATION)
        self.assertEqual([e['text_id'] for e in inserted['events']],
                         [f'Huanglong_main_1_5_76_{i}' for i in (1, 12, 2, 3, 10, 4, 5, 6, 11, 7, 8, 9)])
        proof = inserted['placement']
        self.assertEqual(proof['investigation_node']['Id'], 81)
        self.assertEqual(proof['success_node']['FinishActions'][1]['Params']['DungeonId'], 1503)
        self.assertFalse(proof['runtime_verified'])
        view = build_mainline_reading(result)
        blocks = view['blocks']
        continuation = next(i for i, block in enumerate(blocks) if block['scope'] == 'current_task_continuation')
        self.assertEqual(blocks[continuation - 1]['source_pointer'], f'/recap_backbone/segments/{index}/events')
        self.assertEqual(blocks[continuation + 1]['source_pointer'], f'/recap_backbone/segments/{index + 1}/events')
        self.assertEqual(view['retained_text_events'], 389)
        self.assertEqual(view['omission_markers'], 7)

    def test_old_house_awakening_sits_between_fainting_and_exit(self):
        from wuwa_story.mainline_reading import build_mainline_reading
        from wuwa_story.reading_cases.old_house import AFTER_EXIT, AWAKENING, FAINT
        from wuwa_story.recap_backbone import export_task_backbone

        result = export_task_backbone(189000005)
        segments = result['recap_backbone']['segments']
        index = next(i for i, segment in enumerate(segments) if segment['state_key'] == FAINT)
        self.assertEqual(segments[index + 1]['state_key'], AFTER_EXIT)
        continuation = segments[index]['current_task_continuation']
        self.assertEqual(continuation['state_key'], AWAKENING)
        self.assertEqual([e['text_id'] for e in continuation['events']],
                         [f'Main_HuangLong_SYYLFML_290_{i}' for i in range(1, 8)])
        placement = continuation['placement']
        self.assertEqual(placement['entry_teleport']['Params']['DungeonId'], 2525)
        self.assertEqual(placement['flow_call_sites'][AWAKENING]['path'][1], 135)
        self.assertEqual((placement['exit_node_id'], placement['exit_tip']['entry_index']), (133, 8))
        self.assertFalse(placement['runtime_verified'])
        view = build_mainline_reading(result)
        blocks = view['blocks']
        inserted = next(i for i, block in enumerate(blocks) if block['scope'] == 'current_task_continuation')
        self.assertEqual(blocks[inserted - 1]['source_pointer'], f'/recap_backbone/segments/{index}/events')
        self.assertEqual(blocks[inserted + 1]['source_pointer'], f'/recap_backbone/segments/{index + 1}/events')
        self.assertEqual(view['retained_text_events'], 453)
        self.assertEqual(view['omission_markers'], 1)
        self.assertNotIn(AWAKENING, {r.get('origin') for r in result['batch_coverage']['records']})

    def test_camp_conversation_uses_entity_lifecycle_and_is_marked_optional(self):
        from wuwa_story.reading_cases.camp import ARRIVAL, CAMP_TALK, MESSENGER
        from wuwa_story.mainline_reading import build_mainline_reading
        from wuwa_story.recap_backbone import export_task_backbone

        result = export_task_backbone(140000004)
        segments = result['recap_backbone']['segments']
        index = next(i for i, segment in enumerate(segments) if segment['state_key'] == ARRIVAL)
        self.assertEqual(segments[index + 1]['state_key'], MESSENGER)
        continuation = segments[index]['current_task_continuation']
        self.assertEqual(continuation['state_key'], CAMP_TALK)
        self.assertTrue(continuation['optional'])
        self.assertEqual([e['text_id'] for e in continuation['events']],
                         [f'Huanglong_main_1_7_5_{i}' for i in (1, 7, 8, 2, 3, 4, 5, 6)])
        placement = continuation['placement']
        self.assertEqual(placement['entity_interaction']['entity_id'], 140800001)
        self.assertEqual(placement['awake']['source_path'], [30, 'FinishActions', 2])
        self.assertEqual(placement['destroy']['source_path'], [110, 'EnterActions', 1])
        self.assertFalse(placement['runtime_verified'])
        view = build_mainline_reading(result)
        self.assertEqual(view['retained_text_events'], 404)
        self.assertEqual(view['omission_markers'], 0)
        blocks = view['blocks']
        inserted = next(i for i, block in enumerate(blocks) if block['scope'] == 'current_task_continuation')
        self.assertEqual(blocks[inserted]['introduction'], '【检查营地 · 可选交谈】')
        self.assertEqual(blocks[inserted - 1]['source_pointer'], f'/recap_backbone/segments/{index}/events')
        self.assertEqual(blocks[inserted + 1]['source_pointer'], f'/recap_backbone/segments/{index + 1}/events')
        self.assertNotIn(CAMP_TALK, {r.get('origin') for r in result['batch_coverage']['records']})


if __name__ == '__main__':
    unittest.main()

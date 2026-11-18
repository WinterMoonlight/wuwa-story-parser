import unittest
from wuwa_story.recap_backbone import export_task_backbone


class RoundFourTests(unittest.TestCase):
    def test_avinuolin_adds_current_aftermath_without_replacing_legacy_gap(self):
        from wuwa_story.reading_cases.avinuolin import FAMILY, MISSING, RETURN
        from wuwa_story.mainline_reading import build_mainline_reading

        result = export_task_backbone(145000005)
        segments = result['recap_backbone']['segments']
        index = next(i for i, segment in enumerate(segments) if segment['state_key'] == MISSING)
        gap = segments[index]
        self.assertEqual(segments[index - 1]['state_key'], FAMILY + '11_15')
        self.assertEqual(segments[index + 1]['state_key'], FAMILY + '16_1')
        self.assertEqual(gap['error'], 'Missing flow state')
        self.assertEqual([event['kind'] for event in gap['events']], ['recap_gap'])
        continuation = gap['current_task_continuation']
        self.assertEqual(continuation['state_key'], RETURN)
        self.assertEqual(len(continuation['events']), 16)
        self.assertEqual(continuation['placement']['return_node_id'], 436)
        self.assertFalse(continuation['placement']['legacy_state_equivalence_verified'])
        self.assertFalse(continuation['placement']['runtime_sibling_order_verified'])
        view = build_mainline_reading(result)
        self.assertEqual(view['retained_text_events'], 1039)
        self.assertEqual(view['omission_markers'], 7)
        blocks = view['blocks']
        inserted = next(i for i, block in enumerate(blocks) if block['scope'] == 'current_task_continuation')
        self.assertEqual(blocks[inserted - 1]['parts'][0]['kind'], 'omission')
        self.assertEqual(blocks[inserted + 1]['source_pointer'], f'/recap_backbone/segments/{index + 1}/events')

    def test_unconditional_routes_keep_original_indices_and_reject_guard_override(self):
        cases=[(145000005,'剧情_2_2_阿维纽林主线_9_1',11,1,21),
               (311000001,'剧情_主线生态npc对话（上）_1_13',2,1,3),
               (886000001,'剧情_2_6_狄斯台地主线_下半_混沌之间_1_18',1,0,3),
               (936000002,'剧情_3_0_拉海洛主线_下半_2_15_1',2,0,4)]
        for q,key,tid,selected,count in cases:
            d=export_task_backbone(q)
            s=next(s for s in d['recap_backbone']['segments'] if s['state_key']==key)
            self.assertEqual(s['status'],'parsed',s.get('error'))
            self.assertEqual(len(s['events']),count)
            c=next(c for c in s['route']['choices'] if c['choice_key']==key+':'+str(tid))
            self.assertEqual(c['selected_index'],selected)
            excluded=c['condition_policy']['excluded_original_indices'][0]
            self.assertEqual(c['options'][excluded]['availability'],'unverified')
            self.assertIn('source_condition',c['options'][excluded])
            d=export_task_backbone(q,{key+':'+str(tid):excluded})
            s=next(s for s in d['recap_backbone']['segments'] if s['state_key']==key)
            self.assertEqual(s['status'],'blocked')
            self.assertIn('unknown availability',s['error'])
            self.assertEqual([e['kind'] for e in s['events']],['recap_gap'])

    def test_letter_original_call_position_and_no_recap_duplicate(self):
        d=export_task_backbone(192000006)
        s=next(s for s in d['recap_backbone']['segments'] if s['state_key']=='剧情_3_5_拉海洛今州_51_1')
        self.assertEqual(s['status'],'parsed',s.get('error'))
        self.assertEqual(len(s['events']),14)
        positions=[i for i,e in enumerate(s['events']) if e.get('letter_id')==750003]
        self.assertEqual(len(positions),1)
        i=positions[0]
        self.assertIn('是秧秧的信',s['events'][i-1]['text'])
        self.assertEqual(s['events'][i]['text_id'],'Main_HuangLong_SYYLFML_1_1')
        self.assertIn('秧秧啊',s['events'][i+1]['text'])
        self.assertNotIn('剧情_3_5_拉海洛今州_2_1',[x['state_key'] for x in d['recap_backbone']['segments']])

    def test_terminal_text_keeps_finish_state_unexecuted(self):
        key='剧情_2_0_黎那汐塔主线_第三幕下_狂欢节_60_1'
        d=export_task_backbone(114000029)
        s=next(s for s in d['recap_backbone']['segments'] if s['state_key']==key)
        self.assertEqual(s['status'],'parsed')
        self.assertEqual(len(s['events']),4)
        proof=next(p for p in s['unverified_content'] if p['kind']=='terminal_text_boundary')
        self.assertFalse(proof['state_controls_executed'])
        self.assertFalse(proof['runtime_completion_verified'])

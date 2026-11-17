import unittest
from wuwa_story.recap_backbone import export_task_backbone


class RoundFourTests(unittest.TestCase):
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

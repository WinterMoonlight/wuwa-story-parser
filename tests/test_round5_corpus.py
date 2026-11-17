import unittest
from unittest.mock import patch
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class RoundFiveTests(unittest.TestCase):
    def test_prefix_caption_cannot_be_promoted_to_confirmed_route(self):
        d=export_task_backbone(114000029)
        backbone=d['recap_backbone']
        s=next(s for s in backbone['segments'] if s.get('prefix_event_count'))
        s['events'][0]['media']={'captions':[{'text':'测试字幕','text_id':'prefix_caption_test'}]}
        with patch('wuwa_story.recap_backbone.build_backbone',return_value=backbone):
            result=export_task_backbone(114000029)
        record=next(r for r in result['batch_coverage']['records'] if r.get('text')=='测试字幕')
        self.assertEqual(record['category'],'unverified')
        self.assertEqual(record['order_scope'],'recap_prefix_only')
        self.assertFalse(record['order_verified'])

    def test_reached_prefix_keeps_gap_and_status(self):
        for q, suffix, count in [(114000029,'狂欢节_21_1',9),(114000029,'狂欢节_60_1',4),
                                 (880000044,'千夏活动主线_9_14',17)]:
            d=export_task_backbone(q)
            s=next(s for s in d['recap_backbone']['segments'] if s['state_key'].endswith(suffix))
            self.assertEqual(s['status'],'blocked')
            self.assertEqual(s['prefix_event_count'],count)
            self.assertEqual(len(s['events']),count+1)
            self.assertEqual(s['events'][-1]['kind'],'recap_gap')
            self.assertFalse(s['control_boundary']['boundary_executed'])
            self.assertFalse(s['control_boundary']['suffix_order_verified'])
            self.assertIn('本段仅展示已解析的开头',reading_text(d))
            prefix=[r for r in d['batch_coverage']['records'] if r.get('order_scope')=='recap_prefix_only']
            self.assertTrue(prefix)
            self.assertTrue(all(r['category']=='unverified' for r in prefix))

    def test_async_panel_is_not_a_serial_dialogue_event(self):
        d=export_task_backbone(165800000)
        s=next(s for s in d['recap_backbone']['segments'] if s['state_key']=='剧情_3_2_拉海洛主线_下半_4_1')
        self.assertEqual(s['status'],'parsed',s.get('error'))
        self.assertEqual(len(s['events']),13)
        a=s['unordered_attachments'][0]
        self.assertEqual([v['text'] for v in a['texts']],['星炬学院内','刚刚，通讯的另一边……'])
        self.assertFalse(a['interleaving_with_dialogue_verified'])
        ids={e.get('text_id') for e in s['events']}
        self.assertTrue(all(v['text_id'] not in ids for v in a['texts']))
        self.assertIn('本段异步界面材料',reading_text(d))
        self.assertEqual(d['batch_coverage']['source_counts']['recap_unordered_panel_texts'],2)

    def test_unordered_combination_does_not_leak_partial_events(self):
        d=export_task_backbone(915000001)
        for s in d['recap_backbone']['segments']:
            if s['state_key'].endswith(('_1_15_1','_1_17_1')):
                self.assertEqual(s['status'],'blocked')
                self.assertNotIn('prefix_event_count',s)
                self.assertEqual([e['kind'] for e in s['events']],['recap_gap'])

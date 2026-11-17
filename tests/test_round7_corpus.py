import unittest

from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class Round7CorpusTests(unittest.TestCase):
    def test_consensus_suffix_at_unique_recap_anchor(self):
        result = export_task_backbone(114000026)
        anchor = next(s for s in result['recap_backbone']['segments'] if s['state_key']=='剧情_2_0_黎那汐塔主线_序幕_1_1')
        extra='剧情_2_0_黎那汐塔主线_序幕_10_1'
        inserted=[e for e in anchor['events'] if e.get('state_key')==extra]
        self.assertEqual(len(inserted),13)
        self.assertEqual(sum(e['kind']=='choice' for e in inserted),1)
        self.assertEqual(anchor['events'][-13:],inserted)
        self.assertTrue(all(e['task_placement']['owner_node_ids']==[114,123,130] for e in inserted))
        self.assertFalse(result['recap_backbone']['task_order_verified'])

    def test_phone_emoji_survives_final_rendering(self):
        from wuwa_story.phone import inspect_message
        from wuwa_story.database import rows
        from wuwa_story.rendering import render_result
        phone=inspect_message(38005,rows)
        events=phone['events']
        original_ids=[e.get('talk_id') for e in events]
        result=render_result({'title':'手机消息','route':phone['route'],'events':events,'validation':{}})
        self.assertEqual([e.get('talk_id') for e in result['events']],original_ids)
        self.assertEqual(len(events),31)
        self.assertEqual(events[-1]['text'],'【表情：图片内容尚未核验】')
        self.assertIn('【表情：图片内容尚未核验】',reading_text(result))
        self.assertIn('raw_text',events[-1])

    def test_declared_trigger_text_is_candidate_not_mainline(self):
        result = export_task_backbone(690000001)
        records = [r for r in result['batch_coverage']['records']
                   if r.get('reading_context') == 'entity_trigger_candidate']
        self.assertEqual(len(records), 7)
        self.assertEqual(len({r['origin'] for r in records}), 3)
        self.assertTrue(all(r['category'] == 'candidate_branch'
                            and not r['order_verified'] and not r['mandatory_verified'] for r in records))
        body = {(e.get('state_key', s['state_key']), e.get('text_id'))
                for s in result['recap_backbone']['segments'] for e in s['events']}
        self.assertFalse(body & {(r['origin'], r['text_id']) for r in records})
        text = reading_text(result)
        for r in records:
            self.assertIn(r['text'], text)
            self.assertTrue(r['ownership_link_indices'])
        self.assertTrue(all(not link['runtime_trigger_verified'] for link in result['batch_coverage']['entity_trigger_links']))


if __name__ == '__main__':
    unittest.main()

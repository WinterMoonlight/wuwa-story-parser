import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class Round8CorpusTests(unittest.TestCase):
    def test_phone_tip_sections_preserve_source_order_without_duplicate_appendix(self):
        result=export_task_backbone(165800000)
        backbone=result['recap_backbone']
        inserted=backbone['phone_tip_insertions']
        self.assertEqual([(p['entry_index'],p['message_id'],len(p['events'])) for p in inserted],[(0,32000,14),(5,32001,9)])
        txt=reading_text(result)
        self.assertEqual(txt.count('【手机消息：按回顾任务提示位置排列】'),2)
        self.assertLess(txt.index('【手机消息：按回顾任务提示位置排列】'),txt.index('【回顾第1段】'))
        for p in inserted:
            original=result['external_content'][p['external_index']]['phone']
            self.assertEqual(p['events'],original['events'])
            self.assertFalse(original['read_time_verified'])
        records=result['batch_coverage']['records']
        hidden=[r for r in records if r.get('counted_elsewhere')]
        self.assertEqual(len(hidden),23)
        new=[r for r in records if r.get('order_scope')=='unique_recap_tip_phone_section_only']
        self.assertEqual(len(new),23)
        self.assertTrue(all(not r['order_verified'] for r in new))
        self.assertFalse(backbone['task_order_verified'])
        self.assertFalse(result['batch_coverage']['reading_acceptance']['accepted'])

    def test_phone_with_unknown_surrounding_actions_remains_separate(self):
        result=export_task_backbone(173000000)
        from wuwa_story.phone_tip_anchors import phone_tip_insertions
        self.assertFalse(phone_tip_insertions(result['source']['task_nodes'],result['recap_backbone'],result['external_content'],source=None))
        self.assertTrue(any(e.get('phone',{}).get('message_id')==36000 for e in result['external_content']))


if __name__=='__main__':
    unittest.main()

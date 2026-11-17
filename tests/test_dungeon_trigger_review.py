import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class DungeonTriggerReviewTests(unittest.TestCase):
    def test_repeated_flow_keeps_each_callsite_and_phase(self):
        result=export_task_backbone(139000027)
        reviews=result['batch_coverage']['dungeon_trigger_review']
        repeated=next(r for r in reviews if r['state_key'].endswith('_8_3'))
        self.assertEqual(repeated['callsite_count'],2)
        self.assertEqual({(o['node_id'],o['phase'])for o in repeated['occurrences']},
                         {(22,'FinishActions'),(27,'EnterActions')})
        self.assertFalse(repeated['single_playback_verified'])
        self.assertFalse(repeated['order_verified'])
        self.assertIn('同一对白有多处触发配置',reading_text(result))
        timed=next(o for o in repeated['occurrences']if o['node_id']==27)
        self.assertEqual(timed['condition']['Time'],1)
        self.assertEqual(timed['phase'],'EnterActions')
        condition=next(r for r in reviews if r['state_key'].endswith('_8_8'))
        self.assertEqual(condition['callsite_count'],0)
        self.assertEqual(condition['reference_count'],1)
        self.assertEqual(condition['occurrences'][0]['reference_kind'],'flow_completion_condition')


if __name__=='__main__':unittest.main()

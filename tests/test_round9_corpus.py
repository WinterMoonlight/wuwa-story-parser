import unittest
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class Round9CorpusTests(unittest.TestCase):
    def test_36000_at_tip_with_post_read_world_evidence(self):
        result=export_task_backbone(173000000)
        backbone=result['recap_backbone']
        insertion=next(p for p in backbone['phone_tip_insertions'] if p['message_id']==36000)
        self.assertEqual(insertion['entry_index'],0)
        self.assertEqual(len(insertion['events']),15)
        self.assertEqual(insertion['events'],result['external_content'][insertion['external_index']]['phone']['events'])
        proof=insertion['proof']
        self.assertFalse(proof['runtime_verified'])
        self.assertFalse(proof['post_read_world_effects_simulated'])
        evidence=proof['surrounding_action_evidence']
        self.assertEqual(len(evidence),7)
        states=[e['evidence'] for e in evidence if e['evidence']['source_action']['Name']=='ChangeEntityState']
        self.assertEqual(len(states),1)
        self.assertTrue(states[0]['entities'][0]['source_sha256'])
        self.assertFalse(states[0]['runtime_executed'])
        txt=reading_text(result)
        self.assertLess(txt.index('【手机消息：按回顾任务提示位置排列】'),txt.index('【回顾第1段】'))
        self.assertEqual(len([r for r in result['batch_coverage']['records']if r.get('counted_elsewhere')]),15)
        self.assertFalse(backbone['task_order_verified'])
        self.assertFalse(result['batch_coverage']['reading_acceptance']['accepted'])


if __name__=='__main__':unittest.main()

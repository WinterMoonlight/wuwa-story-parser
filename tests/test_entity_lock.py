import unittest
from unittest.mock import patch
from wuwa_story.reading_effects import entity_lock_shape
from wuwa_story.export_task import Exporter


class EntityLockTests(unittest.TestCase):
    def test_exact_shape_and_boundaries(self):
        a={'Name':'LockEntity','Params':{'EntityIds':[123]}}
        self.assertTrue(entity_lock_shape(a))
        self.assertTrue(entity_lock_shape(dict(a,Name='UnlockEntity')))
        for bad in [dict(a,Async=True),dict(a,Timeout=1),dict(a,OnFinish=[]),
                    dict(a,Params=None),dict(a,Params={'EntityIds':[True]}),
                    dict(a,Params={'EntityIds':[]}),dict(a,Params={'EntityIds':[-1]}),
                    dict(a,Params={'EntityIds':[123],'Actions':[]})]:
            self.assertFalse(entity_lock_shape(bad))
            p=Exporter(allow_incomplete=True);p.state_key='test'
            with self.assertRaises(ValueError):p.action(bad)

    def test_reading_order_and_strict_rejection(self):
        for name in ['LockEntity','UnlockEntity']:
            a={'Name':name,'Params':{'EntityIds':[123]}}
            p=Exporter(allow_incomplete=True);p.state_key='test'
            with patch('wuwa_story.export_task.texts',{'a':'前','b':'后'}):
                p.actions([{'Name':'ShowCenterText','Params':{'TidCenterText':'a'}},a,
                           {'Name':'ShowCenterText','Params':{'TidCenterText':'b'}}])
            self.assertEqual([e['raw_text'] for e in p.events],['前','后'])
            self.assertFalse(p.unverified_content[0]['runtime_executed'])
            p=Exporter();p.state_key='test'
            with self.assertRaises(ValueError):p.action(a)

    def test_real_recap_restored_in_place(self):
        from wuwa_story.recap_backbone import export_task_backbone
        for qid,key in [(125900000,'剧情_1_1_乘宵山主线_2_15'),(886000002,'剧情_3_7_主线火匣_44_1')]:
            d=export_task_backbone(qid)
            seg=next(s for s in d['recap_backbone']['segments'] if s['state_key']==key)
            self.assertEqual(seg['status'],'parsed')
            self.assertTrue(seg['events'])
            self.assertTrue(any(e['kind']=='entity_lock_state' for e in seg['unverified_content']))


if __name__=='__main__':unittest.main()

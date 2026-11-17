import copy
import unittest
from unittest.mock import patch
from wuwa_story.reading_effects import leisure_sit_shape
from wuwa_story.export_task import Exporter
from wuwa_story.recap_backbone import export_task_backbone


class RoundThreeTests(unittest.TestCase):
    def test_phone_open_boundaries_and_source_order(self):
        from wuwa_story.phone import inspect_open_phone
        from wuwa_story.database import rows
        a={'Name':'PhoneSystemInteract','Params':{'InteractType':{'Type':'FlowOpenPhoneMessage',
           'PhoneBoardType':{'Type':'MessageBoard','MessageBoardConfig':{'PhoneMessageId':33004}}}}}
        for extra in [{'Async':True},{'Timeout':1},{'Callbacks':[]}]:
            with self.assertRaises(ValueError):inspect_open_phone(dict(a,**extra),rows)
        for p in [None, {'InteractType':None}, {'InteractType':{'Type':'SendPhoneMessage'}}]:
            with self.assertRaises(ValueError):inspect_open_phone(dict(a,Params=p),rows)
        d=export_task_backbone(119000000)
        s=next(s for s in d['recap_backbone']['segments'] if s['state_key']=='剧情_3_3_拉海洛主线_下半_1_15')
        self.assertEqual(s['status'],'parsed',s.get('error'))
        self.assertEqual(len(s['events']),68)
        child=s['events'][14:27]
        self.assertTrue(all(e['state_key']=='剧情_3_3_拉海洛主线_下半_6_4' for e in child))
        self.assertTrue(all(e['phone_message_id']==33004 for e in child))
        self.assertTrue(all(e['parent_phone_action']['Name']=='PhoneSystemInteract' for e in child))
        self.assertFalse(s['missing_text_ids'])
        self.assertEqual(len([e for e in s['events'] if e['kind']=='choice']),8)
        self.assertEqual(len([e for e in s['events'] if e['kind']=='system_tip']),1)

    def test_sit_boundaries_and_order(self):
        a={'Name':'LeisureInteract','Params':{'Option':{'Type':'SitDown'},'SceneEntity':195700002}}
        self.assertTrue(leisure_sit_shape(a))
        for extra in [{'Async':True},{'Timeout':1},{'Callback':[]}]:
            self.assertFalse(leisure_sit_shape(dict(a,**extra)))
        for entity in [True,0,-1,'1']:
            b=copy.deepcopy(a);b['Params']['SceneEntity']=entity
            self.assertFalse(leisure_sit_shape(b))
        b=copy.deepcopy(a);b['Params']['Option']['Type']='GetUp'
        self.assertFalse(leisure_sit_shape(b))
        p=Exporter(allow_incomplete=True);p.state_key='test'
        with patch('wuwa_story.export_task.texts',{'a':'之前','b':'之后'}):
            p.actions([{'Name':'ShowCenterText','Params':{'TidCenterText':'a'}},a,
                       {'Name':'ShowCenterText','Params':{'TidCenterText':'b'}}])
        self.assertEqual([e['raw_text'] for e in p.events],['之前','之后'])
        self.assertFalse(p.unverified_content[0]['pose_completion_verified'])
        strict=Exporter();strict.state_key='test'
        with self.assertRaises(ValueError):strict.action(a)

    def test_real_sit_text(self):
        d=export_task_backbone(125000129)
        s=next(s for s in d['recap_backbone']['segments'] if s['state_key']=='剧情_3_4_拉海洛主线_10_1')
        self.assertEqual(s['status'],'parsed',s.get('error'))
        self.assertEqual(len(s['events']),3)
        self.assertEqual([e['text_id'] for e in s['events']],
                         [f'Main_LahaiRoi_WMXZTK_61_{i}' for i in (1,2,3)])
        self.assertTrue(all(e['source_item']['Type']=='CenterText' for e in s['events']))

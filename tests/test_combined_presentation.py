import copy
import unittest
from unittest.mock import patch
from wuwa_story.combined_presentation import combined_hide, combined_actor
from wuwa_story.export_task import Exporter


class CombinedTests(unittest.TestCase):
    def item(self, name='HideByRangeInFlow'):
        params = {'Center':{'X':1,'Y':2,'Z':3},'Radius':10,'EntityIds':[1],
                  'IsCleanSimpleNpc':False,'IsCleanPasserByNpc':True} if name=='HideByRangeInFlow' else {'ActorIndex':0,'Talker':2}
        return {'Type':'Talk','Id':1,'WhoId':1,'TidTalk':'a',
                'Options':[{'TidTalkOption':'o','Actions':[]}],
                'Actions':[{'Name':name,'Params':params}]}

    def test_hide_rejects_competing_options_and_unknown_payload(self):
        good=self.item();self.assertTrue(combined_hide(good))
        for mode in ['multiple','action','condition','async','callback','radius','id']:
            a=copy.deepcopy(good)
            if mode=='multiple':a['Options']*=2
            if mode=='action':a['Options'][0]['Actions']=[{'Name':'FinishTalk','Params':{}}]
            if mode=='condition':a['Options'][0]['PreCondition']={}
            if mode=='async':a['Actions'][0]['Async']=True
            if mode=='callback':a['Actions'][0]['OnFinish']=[]
            if mode=='radius':a['Actions'][0]['Params']['Radius']=float('nan')
            if mode=='id':a['Actions'][0]['Params']['EntityIds']=[True]
            self.assertFalse(combined_hide(a),mode)

    def test_actor_requires_explicit_identity_and_passive_option(self):
        a=self.item('ChangeActorTalker');records={1:{'name':'甲'}}
        self.assertTrue(combined_actor(a,[a],records))
        self.assertFalse(combined_actor(a,[a],{1:{'name':'？？？'}}))
        other={'Type':'Talk','Id':2};self.assertFalse(combined_actor(a,[a,other],records))
        a['Actions'][0]['Timeout']=1;self.assertFalse(combined_actor(a,[a],records))
        del a['Actions'][0]['Timeout'];a['Options'][0]['Actions']=[{'Name':'DestroyEntity','Params':{}}]
        self.assertFalse(combined_actor(a,[a],records))

    def test_text_order_and_strict_boundary(self):
        for name in ['HideByRangeInFlow','ChangeActorTalker']:
            item=self.item(name)
            items=[item,{'Type':'Talk','Id':2,'WhoId':2,'TidTalk':'b'}]
            with patch('wuwa_story.export_task.texts',{'a':'之前','o':'回应','b':'之后'}):
                p=Exporter(allow_incomplete=True,speaker_records={1:{'name':'甲'},2:{'name':'乙'}});p.state_key='test'
                p.actions([{'Name':'ShowTalk','Params':{'TalkItems':items}}])
                self.assertEqual([e['raw_text'] for e in p.events],['之前','回应','之后'])
                self.assertEqual(p.events[0]['display_name'],'甲')
                self.assertEqual(p.events[-1]['display_name'],'乙')
                audit=next(e for e in p.unverified_content if e['kind'].startswith('combined_'))
                self.assertFalse(audit['item_action_option_relative_timing_verified'])
                p=Exporter();p.state_key='test'
                with self.assertRaisesRegex(ValueError,'Combined'):p.talk(items)

    def test_real_recovered_segments_and_nested_option_order(self):
        from wuwa_story.recap_backbone import export_task_backbone
        samples=[(880000044,'剧情_2.8千夏活动主线_4_3',9),
                 (168800009,'剧情_3_2_拉海洛主线_上半_暗面4_4_1',15),
                 (886000002,'剧情_3_7_梦枢天罗_2_7',7),
                 (119000001,'剧情_3_8_予以明日的花束2_3_1',12)]
        for qid,key,count in samples:
            d=export_task_backbone(qid);s=next(s for s in d['recap_backbone']['segments'] if s['state_key']==key)
            self.assertEqual(s['status'],'parsed');self.assertEqual(len(s['events']),count)
            if qid==880000044:
                ids=[e.get('text_id') for e in s['events']]
                self.assertLess(ids.index('Shixifeidu_main_2_8_13001_9'),ids.index('Shixifeidu_main_2_8_13001_8'))

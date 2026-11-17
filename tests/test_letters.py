import copy
import unittest
from unittest.mock import patch
from wuwa_story.database import rows
from wuwa_story.letters import inspect_letter


def call():
    return {'Name':'OpenSystemBoard','Params':{'SystemType':'WriteLetter','BoardId':0,
            'WriteLetterConfig':{'LetterId':750003}}}


class LetterTests(unittest.TestCase):
    def test_real_letter_source_and_text(self):
        d=inspect_letter(call(),rows)
        self.assertEqual(d['state_key'],'剧情_3_5_拉海洛今州_2_1')
        self.assertEqual(d['title'],'秧秧的信')
        self.assertEqual([e['text_id'] for e in d['events']],['Main_HuangLong_SYYLFML_1_1'])
        self.assertEqual(d['events'][0]['display_name'],'秧秧的信')
        self.assertIn('也给阿布带了些应时的点心',d['events'][0]['text'])
        self.assertFalse(d['missing_text_ids'])
        self.assertFalse(d['route']['choices'])
        self.assertFalse(d['style_identity_inferred'])
        self.assertFalse(d['read_completion_verified'])

    def test_call_reference_and_schema_guards(self):
        for extra in [{'Async':True},{'Timeout':1},{'Callbacks':[]}]:
            with self.assertRaises(ValueError):inspect_letter(dict(call(),**extra),rows)
        for value in [True,0,-1,'750003']:
            a=call();a['Params']['WriteLetterConfig']['LetterId']=value
            with self.assertRaises(ValueError):inspect_letter(a,rows)
        a=call();a['Params']['BoardId']=True
        with self.assertRaises(ValueError):inspect_letter(a,rows)
        with self.assertRaises(ValueError):inspect_letter(call(),lambda *args:[])
        def bad(db,table):
            r=rows(db,table)
            if db=='db_WriteLetter.db':
                r=copy.deepcopy(r)
                for v in r:
                    if v['Id']==750003:v['BinData']=b'bad'
            return r
        with self.assertRaises(ValueError):inspect_letter(call(),bad)

    def test_nested_or_interactive_letter_is_not_inlined(self):
        for name in ['OpenSystemBoard','PlayFlow','FinishState']:
            with patch('wuwa_story.export_task.flow_actions',return_value=([{'Name':name}],[])):
                with self.assertRaises(ValueError):inspect_letter(call(),rows)
        a=[{'Name':'SetPlotMode','Params':{'Mode':'LevelC','IsSwitchMainRole':False}},
           {'Name':'ShowTalk','Params':{'TalkItems':[{'Type':'Talk','Id':1,'WhoId':1,'TidTalk':'x','Options':[]}]}}]
        with patch('wuwa_story.export_task.flow_actions',return_value=(a,[])):
            with self.assertRaises(ValueError):inspect_letter(call(),rows)
        with patch('wuwa_story.export_task.texts',{'Main_HuangLong_SYYLFML_1_1':'{unknown}'}):
            with self.assertRaises(ValueError):inspect_letter(call(),rows)

import copy
import unittest
from unittest.mock import patch
from wuwa_story.database import rows
from wuwa_story.confirm_boxes import inspect_confirm_box
from wuwa_story.write_only_recap import write_only_environment
from wuwa_story.recap_backbone import export_task_backbone


class RoundTwoTests(unittest.TestCase):
    def test_chaos_choice_keeps_dialogue_and_assignment_on_same_route(self):
        key = '剧情_2_6_狄斯台地主线_下半_混沌之间_2_15'
        prefix = list(range(1, 9)) + [8, 9] + list(range(11, 17)) + [16] + list(range(17, 25))
        for index, variable, tail, excluded, action_id in [
            (0, 'Value2', [25, 26], [27, 28, 29, 30], 5000151),
            (1, 'Fail2', [27, 28, 29, 30], [25, 26], 5000153),
        ]:
            with self.subTest(selected_index=index):
                result = export_task_backbone(886000001, choices={key + ':24': index})
                segment = next(s for s in result['recap_backbone']['segments']
                               if s['state_key'] == key)
                self.assertEqual(segment['status'], 'parsed', segment.get('error'))
                ids = [e['talk_id'] for e in segment['events']]
                self.assertEqual(ids, prefix + tail)
                self.assertTrue(set(excluded).isdisjoint(ids))
                decision = next(c for c in segment['route']['choices']
                                if c['choice_key'] == key + ':24')
                self.assertEqual(decision['selected_index'], index)
                record = next(r for r in segment['unverified_content']
                              if r['kind'] == 'isolated_write_only_variables')
                self.assertTrue(record['no_cross_segment_propagation'])
                self.assertFalse(record['runtime_executed'])
                self.assertFalse(record['downstream_effects_verified'])
                self.assertEqual(len(record['trace']), 1)
                trace = record['trace'][0]
                self.assertEqual(trace['variable']['Name'], variable)
                self.assertEqual(trace['source_action']['ActionId'], action_id)
                self.assertEqual(trace['scope_id'], record['scope_id'])
                self.assertFalse(trace['before_known'])
                self.assertIsNone(trace['before'])
                self.assertIs(trace['after'], True)
                self.assertEqual([(v['name'], v['value']) for v in record['final_values']],
                                 [(variable, True)])

    def test_isolated_write_guards(self):
        a = {'Name':'SetVar','Params':{'VarLeft':{'Type':'Boolean','Source':'Self','Name':'x'},
             'VarRight':{'Type':'Boolean','Source':'Constant','Value':True}}}
        e = write_only_environment([a], 'a'); e.assign(a)
        self.assertIsNone(write_only_environment([a], 'b').read(a['Params']['VarLeft']))
        for extra in [{'Name':'FinishState'}, {'Name':'PlayFlow'}, {'Condition':{}},
                      {'Var1':a['Params']['VarLeft']}]:
            self.assertIsNone(write_only_environment([a, extra], 'a'))
        bad = copy.deepcopy(a); bad['Params']['VarLeft']['Source']='Global'
        self.assertIsNone(write_only_environment([a,bad], 'a'))

    def test_confirm_source_and_guards(self):
        a={'Name':'OpenSystemBoard','Params':{'SystemType':'ConfirmBox','BoardId':181}}
        b=inspect_confirm_box(a,rows)
        self.assertEqual([v['text_id'] for v in b['texts']],
            ['ConfirmBox_180_Title','ConfirmBox_181_Content','ConfirmBox_1_ButtonText_1'])
        self.assertIn('长线任务',b['texts'][1]['raw_text'])
        self.assertFalse(b['button_click_verified'])
        for extra in [{'Async':True},{'Timeout':1},{'Callbacks':[]}]:
            with self.assertRaises(ValueError): inspect_confirm_box(dict(a,**extra),rows)
        with patch('wuwa_story.confirm_boxes.texts',{'ConfirmBox_180_Title':'{name}'}):
            with self.assertRaises(ValueError): inspect_confirm_box(a,rows)
        with self.assertRaises(ValueError): inspect_confirm_box(a,lambda *args:[])
        multi=copy.deepcopy(a); multi['Params']['BoardId']=1
        with self.assertRaises(ValueError): inspect_confirm_box(multi,rows)

    def test_real_write_only_and_panel_segments(self):
        cases={886000001:{'混沌之间_1_27':3,'混沌之间_2_15':27,'混沌之间_2_24':4},
               168800009:{'上半1_34_1':3},886000002:{'谛天监_3_1':11},
               114000020:{'第四章_42_2':3},114000026:{'序幕_2_1':16},
               114000029:{'狂欢节_3_1':6}}
        for qid, targets in cases.items():
            d=export_task_backbone(qid)
            for suffix,count in targets.items():
                s=next(s for s in d['recap_backbone']['segments'] if s['state_key'].endswith(suffix))
                self.assertEqual(s['status'],'parsed',(qid,s.get('error')))
                self.assertEqual(len(s['events']),count)
                if '混沌之间_2_15' == suffix:
                    self.assertTrue(s['route']['choices'])

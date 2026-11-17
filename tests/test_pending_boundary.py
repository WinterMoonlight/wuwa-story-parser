import copy
import unittest
from unittest.mock import patch
from wuwa_story.batch import Snapshot
from wuwa_story.database import texts
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.pending_boundary import conditional_menu_prefix, enrollment_boundary
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.reading import reading_text


class PendingBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = {r['StateKey']: r for r in Snapshot().rows('db_flowState.db', 'flowstate')}
        cls.key = '剧情_尤诺线npc生态_5_1'
        cls.actions = flow_actions(cls.states[cls.key]['BinData'])[0]
        cls.show = next(a for a in cls.actions if a['Name'] == 'ShowTalk')

    def test_unknown_menu_without_route_proof_preserves_prefix_and_original_source(self):
        with patch('wuwa_story.conditional_route.conditional_text_route', return_value=None):
            result = export_task_backbone(886000001)
        s = next(s for s in result['recap_backbone']['segments'] if s['state_key'] == self.key)
        self.assertEqual(s['status'], 'blocked')
        self.assertEqual(s['prefix_event_count'], 2)
        self.assertEqual(s['error'], 'Conditional menu availability is unknown')
        self.assertEqual([e.get('talk_id') for e in s['events'][:-1]], [1, 2])
        self.assertEqual(s['events'][1]['source_item'], self.show['Params']['TalkItems'][1])
        self.assertFalse(s['route']['choices'])
        self.assertFalse(s['control_boundary']['condition_values_evaluated'])
        self.assertIn('可用条件尚未确认', reading_text(result))
        self.assertEqual(s['source_actions'], self.actions)

    def test_prefix_guards(self):
        for change in ('async', 'unknown_guard', 'unconditional', 'action', 'sequence', 'missing'):
            show = copy.deepcopy(self.show)
            p = show['Params']
            if change == 'async': show['Async'] = True
            elif change == 'unknown_guard': p['TalkItems'][1]['Options'][0]['PreCondition'] = {'Type':'Unknown'}
            elif change == 'unconditional': p['TalkItems'][1]['Options'][0].pop('PreCondition')
            elif change == 'action': p['TalkItems'][0]['Actions'] = [{'Name':'FinishState','Params':{}}]
            elif change == 'sequence': p['TalkSequence'] = [[1,2]]
            else: p['TalkItems'][0]['TidTalk'] = 'missing-key'
            self.assertIsNone(conditional_menu_prefix(show, texts), change)

    def test_standard_parser_does_not_evaluate_unknown_menu(self):
        for review in (False, True):
            parser = Exporter(allow_incomplete=review)
            parser.state_key = self.key
            with self.assertRaises(ValueError):
                parser.actions(self.actions)

    def test_enrollment_is_split_with_no_false_completion(self):
        with patch('wuwa_story.pending_boundary.enrollment_return_route', return_value=None):
            result = export_task_backbone(915000001)
        s = next(s for s in result['recap_backbone']['segments'] if s['state_key'].endswith('_1_15_1'))
        self.assertEqual(s['status'], 'blocked')
        self.assertEqual(s['prefix_event_count'], 1)
        fragment = s['local_fragments'][0]
        self.assertEqual(len(fragment['events']), 25)
        self.assertFalse(fragment['runtime_return_verified'])
        self.assertFalse(fragment['whole_segment_complete'])
        records = [r for r in result['batch_coverage']['records'] if r.get('order_scope') == 'configuration_after_unresolved_ui']
        self.assertEqual(len(records), 25)
        self.assertTrue(all(r['category']=='unverified' and not r['order_verified'] for r in records))
        self.assertIn('界面调用后的配置对白', reading_text(result))
        original = next(a for a in s['source_actions'] if a['Name']=='ShowTalk')['Params']['TalkItems'][0]
        self.assertTrue(original['Actions'])
        self.assertEqual(s['events'][0]['source_item'], original)

    def test_enrollment_shape_is_narrow(self):
        result = export_task_backbone(915000001)
        s = next(s for s in result['recap_backbone']['segments'] if s['state_key'].endswith('_1_15_1'))
        item = next(a for a in s['source_actions'] if a['Name']=='ShowTalk')['Params']['TalkItems'][0]
        self.assertIsNotNone(enrollment_boundary(item))
        for change in ('async', 'callback', 'option_action', 'condition'):
            bad = copy.deepcopy(item)
            if change=='async':bad['Actions'][0]['Async']=True
            elif change=='callback':bad['Actions'][0]['OnFinish']=[]
            elif change=='option_action':bad['Options'][0]['Actions']=[{'Name':'SetVar','Params':{}}]
            else:bad['Options'][0]['PreCondition']={}
            self.assertIsNone(enrollment_boundary(bad), change)

    def test_later_showtalk_does_not_replace_earlier_source_items(self):
        parser=Exporter(allow_incomplete=True,capture_control_prefix=True)
        parser.state_key='test'
        first=copy.deepcopy(self.show['Params']['TalkItems'][0])
        first['Id']=2
        parser.actions([{'Name':'ShowTalk','Params':{'TalkItems':[first]}}])
        from wuwa_story.pending_boundary import PendingDialogueBoundary
        with self.assertRaises(PendingDialogueBoundary):
            parser.actions([self.show])
        self.assertEqual(parser.events[0]['source_item'],first)

    def test_enrollment_fragment_rejects_conditions_or_bad_jumps(self):
        from wuwa_story.pending_boundary import PendingDialogueBoundary,enrollment_fragment
        source=Snapshot()
        key='剧情_3_0_主线_拉海洛主线_上半_1_15_1'
        actions=flow_actions(self.states[key]['BinData'])[0]
        show=next(a for a in actions if a['Name']=='ShowTalk')
        first=show['Params']['TalkItems'][0]
        boundary=PendingDialogueBoundary('enrollment',first['Actions'][0],key,first)
        for mode in ('condition','jump','sequence','second_ui'):
            bad=copy.deepcopy(actions);p=next(a['Params'] for a in bad if a['Name']=='ShowTalk')
            if mode=='condition':p['TalkItems'][1]['Condition']={}
            elif mode=='jump':p['TalkItems'][-1]['Actions']=[{'Name':'JumpTalk','Params':{'TalkId':-999}}]
            elif mode=='sequence':p['TalkSequence']=[[1]]
            else:p['TalkItems'][1]['Actions']=copy.deepcopy(first['Actions'])
            self.assertIsNone(enrollment_fragment(bad,boundary,source,None,None,1),mode)

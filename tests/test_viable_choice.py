import copy
import unittest

from wuwa_story.batch import Snapshot
from wuwa_story.export_task import Exporter, flow_actions
from wuwa_story.prefix_boundary import UnresolvedControlBoundary
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.viable_choice import retry_unconditional_choice


class ViableChoiceTests(unittest.TestCase):
    key='剧情_2.8千夏活动主线_9_14'

    def test_default_uses_complete_local_alternative_and_keeps_original_failure(self):
        result=export_task_backbone(880000044)
        s=next(s for s in result['recap_backbone']['segments'] if s['state_key']==self.key)
        self.assertEqual(s['status'],'parsed')
        self.assertEqual(len(s['events']),18)
        self.assertEqual(s['route']['choices'][-1]['selected_index'],1)
        self.assertIn('晚点再说',s['events'][-2]['text'])
        audit=next(a for a in s['unverified_content'] if a['kind']=='implicit_choice_retry')
        self.assertEqual(audit['original_selected_index'],0)
        self.assertEqual(audit['selected_index'],1)
        self.assertEqual(audit['original_error'],'Unsupported action: SetVar')
        self.assertEqual(len(audit['original_prefix_events']),17)
        self.assertFalse(audit['original_boundary']['boundary_executed'])
        self.assertFalse(audit['runtime_route_verified'])

    def test_explicit_default_still_blocked_and_explicit_alternative_is_honored(self):
        for choice,status,count in ((0,'blocked',18),(1,'parsed',18)):
            result=export_task_backbone(880000044,{self.key+':14':choice})
            s=next(s for s in result['recap_backbone']['segments'] if s['state_key']==self.key)
            self.assertEqual(s['status'],status)
            self.assertEqual(len(s['events']),count)
            self.assertFalse(any(a.get('kind')=='implicit_choice_retry' for a in s['unverified_content']))

    def test_no_retry_for_conditional_or_failing_alternatives(self):
        source=Snapshot()
        row=next(r for r in source.rows('db_flowState.db','flowstate') if r['StateKey']==self.key)
        actions=flow_actions(row['BinData'])[0]
        p=Exporter(source=source,allow_incomplete=True,capture_control_prefix=True)
        p.state_key=self.key
        with self.assertRaises(UnresolvedControlBoundary) as caught:p.actions(actions)
        for change in ('conditional','unknown_action','missing_target','explicit','not_direct','async'):
            bad=copy.deepcopy(actions);choices={}
            item=next(a for a in bad if a['Name']=='ShowTalk')['Params']['TalkItems'][-2]
            if change=='conditional':item['Options'][1]['PreCondition']={}
            elif change=='unknown_action':item['Options'][1]['Actions']=[{'Name':'Unknown','Params':{}}]
            elif change=='missing_target':item['Options'][1]['Actions'][0]['Params']['TalkId']=-1
            elif change=='explicit':choices={self.key+':14':0}
            elif change=='not_direct':item['Options'][0]['Actions']=[]
            else:next(a for a in bad if a['Name']=='ShowTalk')['Async']=True
            self.assertIsNone(retry_unconditional_choice(bad,p,caught.exception,source,None,choices),change)

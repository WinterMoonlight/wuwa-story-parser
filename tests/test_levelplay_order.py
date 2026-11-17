import unittest
from unittest.mock import patch
from types import SimpleNamespace
from wuwa_story.levelplay_order import sync_flow, local_sequences


def call(s, **extra):
    return dict(Name='PlayFlow',Params={'FlowListName':'f','FlowId':1,'StateId':s},**extra)


class LevelPlayOrderTests(unittest.TestCase):
    def run_case(self, actions, links=None, candidate_keys=None, fail=False):
        audits=[{'levelplay_id':10,'nodes':[{'Id':2,'FinishActions':actions}], 'task_conditions':[]}]
        links=links if links is not None else [{'levelplay_id':10,'state_key':'f_1_1'},{'levelplay_id':10,'state_key':'f_1_2'}]
        keys={'f_1_1','f_1_2'} if candidate_keys is None else candidate_keys
        parser=SimpleNamespace(events=[],unverified_content=[],decisions=[],actions=lambda a:False)
        with patch('wuwa_story.levelplay_order.flow_actions',return_value=([],[1])),patch('wuwa_story.levelplay_order.Exporter',return_value=parser):
            if fail:parser.actions=lambda a:(_ for _ in ()).throw(ValueError('unknown'))
            return local_sequences(audits,links,{k:{'BinData':b'x'} for k in keys},None,keys)

    def test_adjacent_sync_is_local_not_global(self):
        r=self.run_case([call(1),call(2)])[0]
        self.assertEqual(r['status'],'local_order_only')
        self.assertTrue(r['relative_invocation_order_verified'])
        self.assertFalse(r['placement_verified'])

    def test_async_and_unknown_intervening_action_break_sequence(self):
        self.assertEqual(self.run_case([call(1),call(2,Async=True)]),[])
        self.assertEqual(self.run_case([call(1),{'Name':'Unknown'},call(2)]),[])

    def test_timeout_and_bad_params_are_not_synchronous_proof(self):
        self.assertFalse(sync_flow(call(1,Timeout=2)))
        self.assertFalse(sync_flow({'Name':'PlayFlow','Params':None}))
        self.assertFalse(sync_flow(None))

    def test_repeated_occurrence_is_not_collapsed(self):
        links=[{'levelplay_id':10,'state_key':k} for k in ['f_1_1','f_1_1','f_1_2']]
        r=self.run_case([call(1),call(2)],links=links)[0]
        self.assertEqual(r['reason'],'repeated_or_unresolved_call_occurrence')

    def test_existing_body_not_pulled_into_appendix(self):
        r=self.run_case([call(1),call(2)],candidate_keys={'f_1_1'})[0]
        self.assertEqual(r['reason'],'not_all_calls_in_candidate_scope')

    def test_parse_failure_preserves_inventory_instead_of_partial_route(self):
        r=self.run_case([call(1),call(2)],fail=True)[0]
        self.assertEqual(r['status'],'blocked')
        self.assertEqual(r['segments'],[])

    def test_real_night_local_fragment_and_no_recap_insertion(self):
        from wuwa_story.recap_backbone import export_task_backbone
        from wuwa_story.reading import reading_text
        d=export_task_backbone(119000000)
        good=[r for r in d['batch_coverage']['levelplay_local_sequences'] if r['status']=='local_order_only']
        self.assertEqual(len(good),1)
        self.assertEqual(good[0]['action_indices'],[0,1])
        self.assertEqual([k.rsplit('_',1)[1] for k in good[0]['state_keys']],['1','14'])
        self.assertEqual(len(good[0]['segments'][0]['events']),8)
        self.assertEqual(d['batch_coverage']['source_counts']['levelplay_local_caption_texts'],20)
        self.assertEqual(d['recap_backbone']['parsed_segments'],38)
        self.assertEqual(d['recap_backbone']['blocked_segments'],0)
        txt=reading_text(d)
        self.assertIn('玩法局部有序片段',txt)
        self.assertIn('与主干的衔接位置尚未确定',txt)
        for event in good[0]['segments'][0]['events']:
            self.assertIn(event['text'],txt)


if __name__=='__main__':unittest.main()

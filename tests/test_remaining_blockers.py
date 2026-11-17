import unittest
from wuwa_story.remaining_blockers import collect_blockers, build_report, collect_unresolved_choices


class RemainingBlockersTests(unittest.TestCase):
    def test_original_choice_failure_is_retained_outside_selected_route_count(self):
        source={'quest_id':1,'title':'test','recap_backbone':{'segments':[{
            'status':'parsed','entry_index':0,'state_key':'a_1_1','unverified_content':[{
                'kind':'implicit_choice_retry','original_error':'Unsupported action: SetVar',
                'original_selected_index':0,'selected_index':1}]}]}}
        self.assertEqual(collect_blockers(source,['a.json']),[])
        self.assertEqual(collect_unresolved_choices(source,['a.json'])[0]['status'],'original_choice_still_unsupported')
    def test_exact_dedup_keeps_occurrences_and_prefixes_blocked(self):
        segments=[{'entry_index':i,'state_key':'same','status':'blocked','error':'Missing flow state'} for i in (1,2)]
        segments += [{'entry_index':3,'state_key':'prefix','status':'blocked','error':'Unsupported action: FinishState','prefix_event_count':4},
                     {'entry_index':4,'state_key':'done','status':'parsed'}]
        a=collect_blockers({'quest_id':1,'title':'a','recap_backbone':{'segments':segments}},['a.json','a.txt'])
        b=collect_blockers({'quest_id':2,'title':'b','recap_backbone':{'segments':segments[:1]}},['b.json','b.txt'])
        r=build_report(a+b)
        self.assertEqual(r['summary']['occurrences'],4)
        self.assertEqual(r['summary']['unique_exact_blockers'],2)
        self.assertEqual(r['summary']['tasks'],2)
        self.assertEqual(r['summary']['prefix_segments_still_blocked'],1)
        self.assertEqual(r['summary']['prefix_events_still_blocked'],4)
        self.assertTrue(all(c['status']=='blocked' for c in r['cases']))

    def test_unknown_errors_remain_explicit_and_scope_is_limited(self):
        d={'quest_id':1,'title':'x','recap_backbone':{'segments':[{'entry_index':0,'state_key':'x','status':'blocked','error':'new error'}]}}
        r=build_report(collect_blockers(d,['x.json','x.txt']))
        self.assertEqual(r['cases'][0]['category'],'unclassified')
        self.assertIn('not all task',r['scope'])
        self.assertEqual(build_report([])['summary']['occurrences'],0)

    def test_neighbors_and_call_sites_preserve_evidence_only(self):
        result = {'quest_id': 1, 'title': 'test', 'source': {
            'quest_definition': {'FinishActions': [{'Name': 'PlayFlow', 'Params': {
                'FlowListName': 'a', 'FlowId': 1, 'StateId': 2}}]}},
            'recap_backbone': {'segments': [
                {'entry_index': 0, 'state_key': 'a_1_1', 'status': 'parsed'},
                {'entry_index': 2, 'state_key': 'a_1_2', 'status': 'blocked', 'error': 'Missing flow state'},
                {'entry_index': 3, 'state_key': 'a_1_3', 'status': 'parsed'}]}}
        case = collect_blockers(result, ['x.json', 'x.txt'])[0]
        self.assertEqual(case['previous_recap_flow']['entry_index'], 0)
        self.assertEqual(case['next_recap_flow']['state_key'], 'a_1_3')
        self.assertEqual(case['task_call_sites'][0]['path'], ['quest', 'FinishActions', 0, 'Params'])
        self.assertFalse(case['recap_neighbors_establish_runtime_order'])

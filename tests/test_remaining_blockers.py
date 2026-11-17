import unittest
from wuwa_story.remaining_blockers import collect_blockers, build_report


class RemainingBlockersTests(unittest.TestCase):
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

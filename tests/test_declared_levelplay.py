import unittest
from types import SimpleNamespace
from unittest.mock import patch
from wuwa_story.declared_levelplay import declared_levelplays


class DeclaredLevelPlayTests(unittest.TestCase):
    def run_case(self, definition=None, nodes=None, declaration='l_8_10'):
        definition = definition if definition is not None else {'Id':10,'LevelId':8}
        nodes = nodes if nodes is not None else [
            {'Id':1,'Type':'Sequence','ParentNodeId':0},
            {'Id':2,'Type':'Action','ParentNodeId':1,'Actions':[{
                'Name':'PlayFlow','Async':True,'Params':{'FlowListName':'f','FlowId':3,'StateId':1}}]}]
        blobs={b'd':definition}
        node_rows=[]
        for i,n in enumerate(nodes):
            b=str(i).encode();blobs[b]=n
            node_rows.append({'Key':f"10_{n['Id']}",'BinData':b})
        source=SimpleNamespace(rows=lambda f,t:[{'LevelPlayId':10,'BinData':b'd'}] if t=='levelplaydata' else node_rows)
        with patch('wuwa_story.declared_levelplay.embedded',side_effect=lambda b:[(1,blobs[b])]):
            return declared_levelplays({'Children':[declaration]},[],[],source)

    def test_async_call_is_inventory_not_order(self):
        links,gaps,audits=self.run_case()
        self.assertFalse(gaps)
        self.assertEqual(links[0]['state_key'],'f_3_1')
        self.assertTrue(links[0]['invocation_async'])
        self.assertFalse(links[0]['order_verified'])
        self.assertFalse(audits[0]['placement_verified'])

    def test_wrong_map_rejects_same_id(self):
        links,gaps,_=self.run_case(declaration='l_9_10')
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'],'definition_id_or_map_mismatch')

    def test_reference_alone_does_not_establish_ownership(self):
        self.assertEqual(declared_levelplays({'Reference':['l_8_10']},[],[],None),([],[],[]))

    def test_duplicate_node_does_not_pick_first(self):
        links,gaps,_=self.run_case(nodes=[{'Id':1},{'Id':1}])
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'],'missing_or_duplicate_nodes')

    def test_cycle_does_not_supply_an_order(self):
        node={'Id':2,'ParentNodeId':2,'Actions':[{'Name':'PlayFlow','Params':{'FlowListName':'f','FlowId':3,'StateId':1}}]}
        links,gaps,_=self.run_case(nodes=[node])
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'],'invalid_ancestry')

    def test_recovery_actions_not_flattened_into_normal_calls(self):
        node={'Id':1,'ParentNodeId':0,'SaveConfig':{'EnterActions':[{'Name':'PlayFlow','Params':{'FlowListName':'f','FlowId':3,'StateId':1}}]}}
        links,_,audits=self.run_case(nodes=[node])
        self.assertFalse(links)
        self.assertIn('SaveConfig',audits[0]['nodes'][0])

    def test_completion_flow_is_kept_with_condition_evidence(self):
        condition = {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'f', 'FlowId': 9, 'StateId': 2}}
        node = {'Id': 10, 'ParentNodeId': 0, 'Type': 'ChildQuest', 'Condition': condition}
        links, gaps, _ = self.run_case(nodes=[node])
        self.assertFalse(gaps)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['state_key'], 'f_9_2')
        self.assertEqual(links[0]['source_condition'], condition)
        self.assertEqual(links[0]['phase'], 'Condition')
        self.assertNotIn('source_action', links[0])
        self.assertFalse(links[0]['runtime_trigger_verified'])
        self.assertFalse(links[0]['order_verified'])

    def test_invalid_completion_flow_is_reported(self):
        node = {'Id': 10, 'ParentNodeId': 0, 'Type': 'ChildQuest',
                'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'f', 'FlowId': True}}}
        links, gaps, _ = self.run_case(nodes=[node])
        self.assertFalse(links)
        self.assertEqual(gaps[0]['phase'], 'Condition')
        self.assertEqual(gaps[0]['reason'], 'malformed_flow_reference')

    def test_echoes_pollution_dialogue_is_recovered_as_candidate(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(145000004)
        coverage = result['batch_coverage']
        key = '剧情_1_3_世界_黑海岸_去除污染_9_2'
        links = [link for link in coverage['declared_levelplay_links'] if link['state_key'] == key]
        self.assertEqual(len(links), 1)
        self.assertEqual((links[0]['levelplay_id'], links[0]['node_id']), (134000035, 10))
        records = [record for record in coverage['records'] if record.get('origin') == key]
        self.assertEqual(len(records), 4)
        self.assertTrue(all(r['category'] == 'candidate_branch' and not r['order_verified'] for r in records))
        segments = result['recap_backbone']['segments']
        self.assertEqual([s['error'] for s in segments[27:29]], ['Missing flow state'] * 2)

    def test_real_glory_four_lines_keep_recap_and_asset_gaps(self):
        from wuwa_story.recap_backbone import export_task_backbone
        d=export_task_backbone(125000125)
        c=d['batch_coverage']
        extra=[r for r in c['records'] if r.get('reading_context')=='declared_levelplay_candidate']
        self.assertEqual([r['text_id'] for r in extra],['MAIN_RYAM_8_1','MAIN_RYAM_8_2','MAIN_RYAM_73_1','MAIN_RYAM_74_1'])
        self.assertTrue(all(not r['order_verified'] and r['category']=='candidate_branch' for r in extra))
        self.assertEqual(d['recap_backbone']['parsed_segments'],33)
        self.assertEqual(d['recap_backbone']['blocked_segments'],1)
        self.assertEqual(sum(len(s['events']) for s in d['recap_backbone']['segments'] if s['status']=='parsed'),351)
        audit=next(a for a in c['declared_levelplay_audit'] if a['levelplay_id']==146850003)
        self.assertEqual(audit['task_conditions'][0]['recap_tip_positions'],[21])
        self.assertFalse(any(l['levelplay_id']==125000006 for l in c['declared_levelplay_links']))
        self.assertFalse(any(l['state_key'].endswith('_3_6') for l in c['declared_levelplay_links']))


if __name__=='__main__':unittest.main()

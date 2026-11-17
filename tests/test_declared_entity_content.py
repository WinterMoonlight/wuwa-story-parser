import unittest
from unittest.mock import patch
from types import SimpleNamespace

from wuwa_story.declared_entity_content import declared_entity_content


class DeclaredEntityTests(unittest.TestCase):
    def source(self, rows):
        return SimpleNamespace(rows=lambda *args: rows)

    def row(self, map_id=8, entity_id=20):
        return {'MapId': map_id, 'EntityId': entity_id, 'Id': 3, 'BinData': b'config'}

    def config(self):
        return {'BubbleComponent': {'Flows': [{'Flow': {'FlowIndex': {
            'FlowListName': 'shared', 'FlowId': 2, 'StateId': 3}}, 'Condition': {'Unknown': True}}]},
            'UnrelatedComponent': {'FlowListName': 'shared', 'FlowId': 99, 'StateId': 9}}

    def test_exact_map_owner_only_and_unknown_condition_not_executed(self):
        source = self.source([self.row(), self.row(9)])
        with patch('wuwa_story.declared_entity_content.embedded', return_value=[(1,self.config()), (2,self.config())]):
            links, gaps = declared_entity_content({'Children': ['e_8_20']}, source)
        self.assertEqual(gaps, [])
        self.assertEqual([x['state_key'] for x in links], ['shared_2_3'])
        self.assertEqual(links[0]['map_id'], 8)
        self.assertFalse(links[0]['order_verified'])
        self.assertFalse(links[0]['mandatory_verified'])
        self.assertIn('Condition', links[0]['source_component']['Flows'][0])

    def test_same_entity_id_other_map_is_not_owner(self):
        links,gaps=declared_entity_content({'Children':['e_8_20']},self.source([self.row(9)]))
        self.assertFalse(links)
        self.assertEqual(gaps[0]['rows'],0)

    def test_duplicate_rows_do_not_pick_first(self):
        links,gaps=declared_entity_content({'Children':['e_8_20']},self.source([self.row(),self.row()]))
        self.assertFalse(links)
        self.assertEqual(gaps[0]['rows'],2)

    def test_disagreeing_embedded_fields_rejected(self):
        with patch('wuwa_story.declared_entity_content.embedded',return_value=[(1,self.config()),(2,{})]):
            links,gaps=declared_entity_content({'Children':['e_8_20']},self.source([self.row()]))
        self.assertFalse(links)
        self.assertEqual(gaps[0]['reason'],'ambiguous_entity_config')

    def test_reference_only_is_not_child_ownership(self):
        self.assertEqual(declared_entity_content({'Reference':['e_8_20']},None),([],[]))

    def test_malformed_flow_id_not_coerced(self):
        cfg={'InteractComponent':{'FlowListName':'shared','FlowId':True,'StateId':3}}
        with patch('wuwa_story.declared_entity_content.embedded',return_value=[(1,cfg)]):
            links,_=declared_entity_content({'Children':['e_8_20']},self.source([self.row()]))
        self.assertFalse(links)

    def test_real_quest_candidates_stay_out_of_ordered_body(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(125000125)
        coverage = result['batch_coverage']
        candidates = [r for r in coverage['records'] if r.get('reading_context') == 'declared_entity_candidate']
        self.assertEqual(len(candidates), 74)
        self.assertEqual(len({r['origin'] for r in candidates}), 24)
        self.assertTrue(all(r['category'] == 'candidate_branch' and not r['order_verified'] for r in candidates))
        self.assertEqual(result['recap_backbone']['parsed_segments'],33)
        self.assertEqual(result['recap_backbone']['blocked_segments'],1)
        self.assertTrue(coverage['order']['dependencies']['recap_dependency_conflicts'])
        body = {e['text_id'] for s in result['recap_backbone']['segments'] for e in s['events'] if e.get('text_id')}
        self.assertFalse(body & {r['text_id'] for r in candidates})

    def test_real_alternate_choice_skips_other_responses(self):
        from wuwa_story.recap_backbone import export_task_backbone
        key='剧情_2_4_七丘主线_上1_4_2'
        result=export_task_backbone(125000125,{key+':7':1})
        segment=next(s for s in result['recap_backbone']['segments'] if s['state_key']==key)
        ids=[e['talk_id'] for e in segment['events'] if e['kind']=='dialogue' and 7<=e.get('talk_id',0)<=11]
        self.assertEqual(ids,[7,9,11])


if __name__=='__main__':
    unittest.main()

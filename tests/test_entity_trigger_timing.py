from copy import deepcopy
from types import SimpleNamespace
import unittest

from wuwa_story.entity_trigger_timing import entity_trigger_timing
from wuwa_story.reading import reading_text


class EntityTriggerTimingTests(unittest.TestCase):
    def fixture(self):
        quest = {'DungeonId': 80}
        nodes = [
            {'Id': 1, 'Type': 'Sequence', 'Desc': '根节点'},
            {'Id': 2, 'ParentNodeId': 1, 'Type': 'Sequence', 'Desc': '宅邸', 'DungeonId': 90},
            {'Id': 3, 'ParentNodeId': 2, 'Type': 'ChildQuest',
             'Condition': {'Type': 'PlayFlow', 'Flow': {'FlowListName': 'main', 'FlowId': 1, 'StateId': 2}},
             'FinishActions': [{'Name': 'AwakeEntity', 'Params': {'EntityIds': [20]}}]},
            {'Id': 4, 'ParentNodeId': 2, 'Type': 'ChildQuest', 'TidTip': 'leave',
             'FinishActions': [{'Name': 'DestroyEntity', 'Params': {'EntityIds': [20]}}]},
            {'Id': 5, 'ParentNodeId': 1, 'Type': 'ChildQuest',
             'EnterActions': [{'Name': 'AwakeEntity', 'Params': {'EntityIds': [20]}}]},
        ]
        links = [{'state_key': 'side_1_1', 'map_id': 9, 'entity_id': 20, 'row_id': 7,
                  'source_sha256': 'hash', 'component': 'TriggerComponent',
                  'source_component': {'Condition': {'SelfState': 'normal'}},
                  'source_action': {'Name': 'PlayFlow', 'Async': True}, 'invocation_async': True,
                  'trigger_range': {'Shape': {'SphereRadius': 100}}}]
        backbone = {'order_source': {'entries': [
            {'Flow': {'FlowListName': 'main', 'FlowId': 1, 'StateId': 2}}, {'TidTip': 'leave'}]}}
        rows = [{'Id': 80, 'MapConfigId': 8}, {'Id': 90, 'MapConfigId': 9}]
        source = SimpleNamespace(rows=lambda *args: rows)
        return quest, nodes, links, backbone, source

    def test_map_alias_and_reused_entity_number(self):
        args = self.fixture()
        review = entity_trigger_timing(*args)[0]
        self.assertEqual(review['common_task_region']['name'], '宅邸')
        self.assertEqual([c['node_id'] for c in review['matching_map_lifecycle']], [3, 4])
        self.assertEqual([c['node_id'] for c in review['other_map_lifecycle']], [5])
        self.assertEqual(review['matching_map_lifecycle'][0]['condition_flow_positions'], [0])
        self.assertEqual(review['matching_map_lifecycle'][1]['tip_positions'], [1])
        self.assertIn('same_entity_number_reused_in_other_map', review['reasons'])
        self.assertIn('asynchronous_flow_completion_order_unverified', review['reasons'])
        self.assertFalse(review['placement_verified'])
        self.assertFalse(review['runtime_verified'])

    def test_ambiguous_map_does_not_supply_region(self):
        args = list(self.fixture())
        args[-1] = SimpleNamespace(rows=lambda *a: [
            {'Id': 80, 'MapConfigId': 8}, {'Id': 90, 'MapConfigId': 9}, {'Id': 90, 'MapConfigId': 10}])
        review = entity_trigger_timing(*args)[0]
        self.assertIsNone(review['common_task_region'])
        self.assertEqual(len(review['unknown_map_lifecycle']), 2)

    def test_broken_ancestry_cannot_supply_stage(self):
        args = self.fixture()
        args[1][3]['ParentNodeId'] = 999
        review = entity_trigger_timing(*args)[0]
        self.assertIsNone(review['common_task_region'])
        self.assertEqual(review['unknown_map_lifecycle'][0]['ancestry_error'], 'invalid_ancestry')

    def test_no_actions_from_embedded_child_or_reference(self):
        args = self.fixture()
        args[1][1]['Reference'] = {'EnterActions': [
            {'Name': 'AwakeEntity', 'Params': {'EntityIds': [20]}}]}
        args[1][1]['Children'] = [{'Id': 99, 'FinishActions': [
            {'Name': 'AwakeEntity', 'Params': {'EntityIds': [20]}}]}]
        review = entity_trigger_timing(*args)[0]
        self.assertEqual(len(review['matching_map_lifecycle']), 2)

    def test_synchronous_invocation_still_needs_spatial_order(self):
        args = self.fixture()
        args[2][0]['invocation_async'] = False
        review = entity_trigger_timing(*args)[0]
        self.assertNotIn('asynchronous_flow_completion_order_unverified', review['reasons'])
        self.assertEqual(review['placement_status'], 'unresolved')
        self.assertEqual(review['recap_occurrences'], [])

    def test_inputs_unchanged_and_empty_links_skip_database(self):
        args = self.fixture()
        saved = deepcopy(args[:4])
        entity_trigger_timing(*args)
        self.assertEqual(args[:4], saved)
        self.assertEqual(entity_trigger_timing({}, [], [], None, None), [])

    def test_real_avinuolin_all_four_remain_in_appendix(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(145000005)
        reviews = result['batch_coverage']['entity_trigger_timing']
        stages = {r['state_key']: (r['map_id'], r['common_task_region']['name']) for r in reviews}
        prefix = '剧情_2_2_阿维纽林主线_'
        self.assertEqual(stages, {prefix + '6_5': (903, '第一副塔'), prefix + '15_2': (903, '第3日'),
                                  prefix + '14_1': (904, '贵族宅邸'), prefix + '14_2': (904, '贵族宅邸')})
        self.assertTrue(all(not r['placement_verified'] for r in reviews))
        records = [r for r in result['batch_coverage']['records'] if r.get('origin') in stages]
        self.assertEqual(len(records), 17)
        self.assertTrue(all(r.get('reading_context') == 'entity_trigger_candidate' for r in records))
        self.assertTrue(all(not r.get('order_verified') for r in records))
        text = reading_text(result)
        for stage in ('贵族宅邸', '第一副塔', '第3日'):
            self.assertIn('【场景触发对白·' + stage + '：具体播放位置待确认】', text)


if __name__ == '__main__':
    unittest.main()

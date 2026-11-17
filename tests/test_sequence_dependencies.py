from copy import deepcopy
import unittest
from unittest.mock import patch

from wuwa_story.sequence_dependencies import (
    controller_dependencies, finish_requirements, flow_progression_review, synchronous_predecessors,
)


class SequenceDependencyTests(unittest.TestCase):
    def test_phase_relations_preserve_async_and_do_not_cross_nodes(self):
        call = {'Name': 'PlayFlow', 'Params': {'FlowListName': 'f', 'FlowId': 1, 'StateId': 1}, 'Async': True}
        nodes = [{'Id': 35, 'Condition': {'Type': 'ReachArea'}, 'EnterActions': [call],
                  'FinishActions': [{**call, 'Params': {**call['Params'], 'StateId': 2}}]},
                 {'Id': 163, 'FinishActions': [{**call, 'Params': {**call['Params'], 'StateId': 3}}]}]
        review = flow_progression_review(nodes, [{'state_keys': ['f_1_1', 'f_1_2', 'f_1_3']}])
        self.assertEqual(len(review['phase_relations']), 1)
        relation = review['phase_relations'][0]
        self.assertEqual((relation['from_call']['state_key'], relation['to_call']['state_key']), ('f_1_1', 'f_1_2'))
        self.assertTrue(relation['requires_same_activation'])
        self.assertFalse(relation['flow_completion_before_followup_verified'])
        self.assertFalse(relation['whole_task_order_verified'])

    def test_lifecycle_pair_records_phases_without_inventing_node_order(self):
        flow = {'FlowListName': 'f', 'FlowId': 1, 'StateId': 1}
        nodes = [{'Id': 80, 'Condition': {'Type': 'PlayFlow', 'Flow': flow},
                  'FinishActions': [{'Name': 'EnableLevelPlay', 'Params': {
                      'Configs': [{'LevelPlayId': 10, 'Enable': True}]}}]},
                 {'Id': 82, 'Condition': {'Type': 'ReachArea'},
                  'EnterActions': [{'Name': 'PlayFlow', 'Params': {**flow, 'StateId': 3}, 'Async': True},
                                   {'Name': 'ChangeEntityState', 'Params': {'EntityId': 20, 'State': 'active'}}],
                  'FinishActions': [{'Name': 'EnableLevelPlay', 'Params': {
                      'Configs': [{'LevelPlayId': 10, 'Enable': False}]}}]}]
        original = deepcopy(nodes)
        review = flow_progression_review(nodes, [{'state_keys': ['f_1_1', 'f_1_3']}])
        pair = review['levelplay_lifecycle'][0]
        self.assertEqual([w['enable'] for w in pair['writes']], [True, False])
        self.assertEqual(pair['writes'][0]['completed_condition_flows'], ['f_1_1'])
        self.assertEqual(pair['writes'][1]['completed_condition_flows'], [])
        self.assertFalse(pair['enable_disable_pair_establishes_order'])
        asynchronous = next(c for c in review['flow_calls'] if c['state_key'] == 'f_1_3')
        self.assertFalse(asynchronous['waits_for_flow_completion'])
        self.assertFalse(review['asynchronous_call_implies_completion'])
        self.assertEqual(nodes, original)

    def test_disabled_calls_and_other_phase_completion_are_not_used(self):
        flow = {'FlowListName': 'f', 'FlowId': 1, 'StateId': 1}
        nodes = [{'Id': 2, 'Condition': {'Type': 'PlayFlow', 'Flow': flow},
                  'EnterActions': [{'Name': 'EnableLevelPlay', 'Params': {
                      'Configs': [{'LevelPlayId': 10, 'Enable': True}]}}],
                  'FinishActions': [{'Name': 'PlayFlow', 'Params': flow, 'Disabled': True},
                                    {'Name': 'EnableLevelPlay', 'Disabled': True, 'Params': {
                                        'Configs': [{'LevelPlayId': 20, 'Enable': True}]}}]}]
        review = flow_progression_review(nodes, [{'state_keys': ['f_1_1']}])
        self.assertEqual(len(review['flow_calls']), 1)
        self.assertEqual([p['levelplay_id'] for p in review['levelplay_lifecycle']], [10])
        self.assertEqual(review['world_effects'][0]['completed_condition_flows'], [])

    def test_gate_and_definition_are_evidence_without_runtime_evaluation(self):
        condition = {'Type': 'CheckConditionGroup', 'Condition': {'Type': 0, 'Conditions': [
            {'Type': 'CheckLevelPlayState', 'LevelId': 10, 'Compare': 'Eq', 'State': 2}]}}
        nodes = [{'Id': 4, 'ParentNodeId': 3, 'Condition': condition,
                  'FinishActions': [{'Name': 'EnableLevelPlay', 'Params': {
                      'Configs': [{'LevelPlayId': 10, 'Enable': False}]}}]}]
        audit = {'levelplay_id': 10, 'definition': {'LevelPlayActive': {'ActiveType': 1}},
                 'definition_sha256': 'digest'}
        review = flow_progression_review(nodes, [], [audit])
        entry = review['levelplay_lifecycle'][0]
        self.assertEqual(entry['completion_gates'][0]['parent_node_id'], 3)
        self.assertFalse(entry['completion_gates'][0]['runtime_satisfied'])
        self.assertEqual(entry['source_definitions'][0]['sha256'], 'digest')
        self.assertFalse(review['whole_task_order_verified'])

    def test_shared_state_writers_do_not_become_exclusive_prerequisites(self):
        from types import SimpleNamespace
        candidate = {'source_row_key': '7_3', 'source_action': {'Name': 'ChangeEntityState'}}
        source = SimpleNamespace(_progression_task_writers={('entity', 20): [candidate]})
        nodes = [{'Id': 82, 'EnterActions': [{'Name': 'ChangeEntityState',
                  'Params': {'EntityId': 20, 'State': 'active'}}]}]
        result = flow_progression_review(nodes, [], source=source)
        self.assertEqual(result['shared_state_writers'][0]['candidate_task_writers'], [candidate])
        result['shared_state_writers'][0]['candidate_task_writers'][0]['source_row_key'] = 'changed'
        self.assertEqual(candidate['source_row_key'], '7_3')
        self.assertFalse(result['whole_task_order_verified'])

    def test_real_wind_three_flows_keep_unknown_inter_node_order(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(125000124)
        review = result['sequence_dependency_review']['flow_progression']
        calls = {(c['node_id'], c['phase']): c for c in review['flow_calls']}
        self.assertEqual(set(calls), {(80, 'Condition'), (82, 'EnterActions'), (84, 'Condition')})
        self.assertTrue(calls[82, 'EnterActions']['invocation_async'])
        pair = next(p for p in review['levelplay_lifecycle'] if p['levelplay_id'] == 131900003)
        self.assertEqual([(w['node_id'], w['enable']) for w in pair['writes']], [(80, True), (82, False)])
        self.assertEqual(pair['completion_gates'][0]['node_id'], 88)
        self.assertFalse(pair['enable_disable_pair_establishes_order'])
        entity = next(e for e in review['shared_state_writers'] if e['target_type'] == 'entity' and e['target_id'] == 140900034)
        self.assertTrue(any(e['source_row_key'] == '125000123_79' for e in entity['candidate_task_writers']))

    def test_only_positive_conjunctive_completion_requirements(self):
        gate = {'Type': 'CheckChildQuestFinished', 'QuestId': 1, 'ChildQuestId': 9, 'Compare': 'Eq'}
        self.assertEqual(finish_requirements({'Type': 'CheckConditionGroup', 'Condition': {
            'Type': 0, 'Conditions': [gate]}}), [gate])
        self.assertEqual(finish_requirements({'Type': 1, 'Conditions': [gate]}), [])
        self.assertEqual(finish_requirements({**gate, 'Compare': 'Ne'}), [])

    def test_only_synchronous_calls_precede_unlock_completion(self):
        call = {'Name': 'PlayFlow', 'Params': {'FlowListName': 'sample', 'FlowId': 1, 'StateId': 2}}
        result = synchronous_predecessors([call, {**call, 'Async': True}, {**call, 'Disabled': True}], 3)
        self.assertEqual([item['action_index'] for item in result], [0])

    def fixture(self):
        quest = {'Id': 1, 'Reference': ['e_8_100', 'e_8_200']}
        nodes = [{'Id': 49, 'FinishActions': [
            {'Name': 'PlayFlow', 'Params': {'FlowListName': 'sample', 'FlowId': 1, 'StateId': 7}},
            {'Name': 'UnlockEntity', 'Params': {'EntityIds': [100]}}]},
            {'Id': 16, 'Condition': {'Type': 'CheckEntityState', 'Conditions': [
                {'EntityId': 200, 'State': 'active'}]}}]
        configs = {100: ({'EntityStateComponent': {'LockConfig': {'IsInitLock': True}},
                         'TimelineTrackControlComponent': {'ControlGroups': [{'ControlConfigs': [
                             {'Type': 'Entity', 'EntityId': 200, 'ControlPoints': [{'State': 'active'}]}]}]}}, 'a'),
                   200: ({'EntityStateComponent': {'State': 'inactive'}}, 'b')}
        return quest, nodes, configs

    def collect(self, quest, nodes, configs):
        with patch('wuwa_story.sequence_dependencies.entity_index', return_value={}), patch(
                'wuwa_story.sequence_dependencies.entity_config', side_effect=lambda index, map_id, entity_id: configs.get(entity_id)):
            return controller_dependencies(quest, nodes, None)

    def test_controller_path_is_traced_without_promoting_global_order(self):
        quest, nodes, configs = self.fixture()
        before = deepcopy(nodes)
        relation = self.collect(quest, nodes, configs)[0]
        self.assertEqual((relation['from_node'], relation['to_node']), (49, 16))
        self.assertEqual(relation['preceding_sync_flows'][0]['state_key'], 'sample_1_7')
        self.assertFalse(relation['target_node_order_verified'])
        self.assertFalse(relation['all_state_writers_verified'])
        self.assertEqual(nodes, before)

    def test_initial_state_and_lock_are_required(self):
        for change in ('unlocked', 'already_active', 'missing_state'):
            quest, nodes, configs = self.fixture()
            if change == 'unlocked':
                configs[100][0]['EntityStateComponent']['LockConfig']['IsInitLock'] = False
            elif change == 'already_active':
                configs[200][0]['EntityStateComponent']['State'] = 'active'
            else:
                configs[200][0]['EntityStateComponent'] = {}
            self.assertEqual(self.collect(quest, nodes, configs), [], change)

    def test_multiple_task_unlockers_remain_visible(self):
        quest, nodes, configs = self.fixture()
        nodes.append({**deepcopy(nodes[0]), 'Id': 51})
        relations = self.collect(quest, nodes, configs)
        self.assertEqual(len(relations), 2)
        self.assertTrue(all(not relation['unique_task_unlocker'] for relation in relations))

    def test_real_mianlong_sequence_and_cross_branch_evidence(self):
        from wuwa_story.recap_backbone import export_task_backbone
        result = export_task_backbone(146000002)
        evidence = result['sequence_dependency_review']
        self.assertEqual(len(evidence['sequence_groups']), 12)
        self.assertEqual(len(evidence['node_storage']), 57)
        self.assertTrue(all(item['layout'] == 'key_and_json_only' for item in evidence['node_storage']))
        self.assertTrue(any((item['from_node'], item['to_node']) == (49, 58)
                            for item in evidence['completion_requirements']))
        relation = next(item for item in evidence['controller_dependencies'] if item['controller_id'] == 146900070)
        self.assertEqual((relation['from_node'], relation['to_node']), (49, 16))
        self.assertEqual([item['state_key'].rsplit('_', 1)[-1] for item in relation['preceding_sync_flows']], ['16', '7'])
        water = next(item for item in evidence['controller_dependencies'] if item['to_node'] == 9)
        self.assertEqual(water['recorded_controller_ids'], [146900063, 146900064])
        self.assertFalse(evidence['whole_task_order_verified'])


if __name__ == '__main__':
    unittest.main()

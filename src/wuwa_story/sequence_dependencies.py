"""Trace explicit task gates and controller prerequisites without ordering siblings."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import re

from .counter_order import equality_gate, local_counter
from .database import embedded, rows
from .export_task import flow_key, walk
from .node_order_evidence import storage_evidence
from .dependency_positions import _sync_flow


def finish_requirements(condition):
    if not isinstance(condition, dict):
        return []
    if condition.get('Type') == 'CheckConditionGroup':
        return finish_requirements(condition.get('Condition'))
    if type(condition.get('Type')) is int and condition['Type'] == 0:
        return [item for child in condition.get('Conditions', []) for item in finish_requirements(child)]
    if (condition.get('Type') == 'CheckChildQuestFinished' and condition.get('Compare') == 'Eq'
            and type(condition.get('QuestId')) is int and type(condition.get('ChildQuestId')) is int):
        return [condition]
    return []


def entity_index(source):
    index = getattr(source, '_declared_entity_content_index', None)
    if index is None:
        index = defaultdict(list)
        read_rows = source.rows if source is not None else rows
        for row in read_rows('db_level_entity.db', 'levelentityconfig'):
            index[row['MapId'], row['EntityId']].append(row)
        if source is not None:
            source._declared_entity_content_index = index
    return index


def entity_config(index, map_id, entity_id):
    matches = index.get((map_id, entity_id), [])
    if len(matches) != 1:
        return None
    row = matches[0]
    configs = [value for _, value in embedded(row['BinData']) if isinstance(value, dict)]
    if not configs or any(value != configs[0] for value in configs):
        return None
    return configs[0], hashlib.sha256(row['BinData']).hexdigest()


def synchronous_predecessors(actions, index):
    calls = []
    for position, action in enumerate(actions[:index]):
        params = action.get('Params', {})
        if (action.get('Name') == 'PlayFlow' and action.get('Async', False) is False
                and not action.get('Disabled', False) and isinstance(params, dict)
                and set(params) == {'FlowListName', 'FlowId', 'StateId'}
                and isinstance(params['FlowListName'], str)
                and type(params['FlowId']) is int and type(params['StateId']) is int):
            calls.append({'action_index': position, 'state_key': flow_key(params),
                          'source_action': deepcopy(action)})
    return calls


def controller_dependencies(quest, nodes, source):
    references = set()
    for ref in quest.get('Reference', []) + quest.get('Children', []):
        match = re.fullmatch(r'e_(\d+)_(\d+)', str(ref))
        if match:
            references.add(tuple(map(int, match.groups())))
    if not references:
        return []
    checks = defaultdict(list)
    unlocks = defaultdict(list)
    for node in nodes:
        condition = node.get('Condition', {})
        if condition.get('Type') == 'CheckEntityState':
            for check in condition.get('Conditions', []):
                if type(check.get('EntityId')) is int and isinstance(check.get('State'), str):
                    checks[check['EntityId'], check['State']].append((node, check))
        for phase in ('Actions', 'EnterActions', 'FinishActions'):
            actions = node.get(phase, [])
            for position, action in enumerate(actions):
                if action.get('Name') == 'UnlockEntity' and not action.get('Disabled', False):
                    for entity_id in action.get('Params', {}).get('EntityIds', []):
                        unlocks[entity_id].append((node, phase, position, action, actions))
    index = entity_index(source)
    controls_by_target = defaultdict(set)
    for map_id, controller_id in references:
        loaded = entity_config(index, map_id, controller_id)
        if loaded:
            for group in loaded[0].get('TimelineTrackControlComponent', {}).get('ControlGroups', []):
                for control in group.get('ControlConfigs', []):
                    if control.get('Type') == 'Entity':
                        for point in control.get('ControlPoints', []):
                            controls_by_target[map_id, control.get('EntityId'), point.get('State')].add(controller_id)
    relations = []
    for map_id, controller_id in sorted(references):
        if controller_id not in unlocks:
            continue
        loaded = entity_config(index, map_id, controller_id)
        if loaded is None:
            continue
        config, controller_hash = loaded
        if config.get('EntityStateComponent', {}).get('LockConfig', {}).get('IsInitLock') is not True:
            continue
        for group_index, group in enumerate(config.get('TimelineTrackControlComponent', {}).get('ControlGroups', [])):
            for control_index, control in enumerate(group.get('ControlConfigs', [])):
                if control.get('Type') != 'Entity' or type(control.get('EntityId')) is not int:
                    continue
                target_id = control['EntityId']
                loaded_target = entity_config(index, map_id, target_id)
                if loaded_target is None:
                    continue
                target_config, target_hash = loaded_target
                initial_state = target_config.get('EntityStateComponent', {}).get('State')
                if not isinstance(initial_state, str):
                    continue
                for point_index, point in enumerate(control.get('ControlPoints', [])):
                    state = point.get('State')
                    if not isinstance(state, str) or state == initial_state:
                        continue
                    for target, check in checks.get((target_id, state), []):
                        for owner, phase, position, action, actions in unlocks[controller_id]:
                            relations.append({'kind': 'timeline_controller_unlock',
                                'from_node': owner['Id'], 'to_node': target['Id'], 'map_id': map_id,
                                'controller_id': controller_id, 'target_entity_id': target_id,
                                'required_state': state, 'target_initial_state': initial_state,
                                'controller_initially_locked': True, 'phase': phase, 'action_index': position,
                                'source_action': deepcopy(action), 'target_condition': deepcopy(check),
                                'preceding_sync_flows': synchronous_predecessors(actions, position),
                                'control_path': ['TimelineTrackControlComponent', 'ControlGroups', group_index,
                                                 'ControlConfigs', control_index, 'ControlPoints', point_index],
                                'source_control': deepcopy(control),
                                'control_group_condition': deepcopy(group.get('Condition')),
                                'controller_sha256': controller_hash, 'target_sha256': target_hash,
                                'unique_task_unlocker': len(unlocks[controller_id]) == 1,
                                'recorded_controller_ids': sorted(controls_by_target[map_id, target_id, state]),
                                'flow_before_unlock_verified': True, 'target_node_order_verified': False,
                                'scope': 'configured initial state and this recorded controller path',
                                'all_state_writers_verified': False, 'runtime_verified': False,
                                'whole_task_order_verified': False})
    return relations


def _state_targets(action):
    params = action.get('Params', {})
    if not isinstance(params, dict) or action.get('Disabled', False):
        return []
    if action.get('Name') == 'ChangeEntityState' and type(params.get('EntityId')) is int:
        return [('entity', params['EntityId'])]
    if action.get('Name') in {'AwakeEntity', 'DestroyEntity'} and isinstance(params.get('EntityIds'), list):
        return [('entity', value) for value in params['EntityIds'] if type(value) is int]
    if action.get('Name') == 'EnableLevelPlay' and isinstance(params.get('Configs'), list):
        return [('levelplay', config['LevelPlayId']) for config in params['Configs']
                if isinstance(config, dict) and type(config.get('LevelPlayId')) is int]
    return []


def _task_state_writers(source):
    cache = getattr(source, '_progression_task_writers', None)
    if cache is not None:
        return cache
    cache = defaultdict(list)
    for row in source.rows('db_QuestNodeData.db', 'questnodedata'):
        values = [value for _, value in embedded(row['BinData']) if isinstance(value, dict)]
        if not values or any(value != values[0] for value in values):
            continue
        node = values[0]
        for phase in ('EnterActions', 'Actions', 'FinishActions'):
            for index, action in enumerate(node.get(phase, [])):
                for target in _state_targets(action):
                    cache[target].append({'source_row_key': row['Key'], 'node_id': node.get('Id'),
                                          'phase': phase, 'action_index': index,
                                          'source_action': deepcopy(action)})
    source._progression_task_writers = cache
    return cache


def flow_progression_review(nodes, groups, levelplay_audits=(), source=None):
    """Record call phases and world effects without ordering separate activations."""
    selected = {key for group in groups for key in group['state_keys']}
    calls, effects, gates = [], [], []
    for node in nodes:
        condition = node.get('Condition', {})
        condition_key = (_sync_flow({'Name': 'PlayFlow', 'Params': condition.get('Flow')})
                         if condition.get('Type') == 'PlayFlow' else None)
        if condition_key in selected:
            calls.append({'state_key': condition_key, 'node_id': node['Id'], 'phase': 'Condition',
                          'source_condition': deepcopy(condition), 'completion_condition': True})
        for check in walk(condition):
            if check.get('Type') == 'CheckLevelPlayState':
                gates.append({'node_id': node['Id'], 'source_condition': deepcopy(check),
                              'parent_node_id': node.get('ParentNodeId'), 'runtime_satisfied': False})
        for phase in ('EnterActions', 'Actions', 'FinishActions'):
            actions = node.get(phase, [])
            for index, action in enumerate(actions):
                if action.get('Disabled', False):
                    continue
                name, params = action.get('Name'), action.get('Params', {})
                key = _sync_flow({k: v for k, v in action.items() if k != 'Async'})
                if key in selected and type(action.get('Async', False)) is bool:
                    calls.append({'state_key': key, 'node_id': node['Id'], 'phase': phase,
                                  'action_index': index, 'invocation_async': action.get('Async', False),
                                  'waits_for_flow_completion': not action.get('Async', False),
                                  'source_action': deepcopy(action)})
                if name not in {'EnableLevelPlay', 'AwakeEntity', 'DestroyEntity', 'ChangeEntityState'}:
                    continue
                if not isinstance(params, dict):
                    continue
                preceding = synchronous_predecessors(actions, index)
                prerequisite = [condition_key] if phase == 'FinishActions' and condition_key else []
                effects.append({'node_id': node['Id'], 'phase': phase, 'action_index': index,
                                'source_action': deepcopy(action),
                                'completed_condition_flows': prerequisite,
                                'preceding_synchronous_calls': preceding,
                                'effect_executed': False})
    lifecycle = []
    play_ids = {config['LevelPlayId'] for effect in effects
                if effect['source_action']['Name'] == 'EnableLevelPlay'
                for config in effect['source_action']['Params'].get('Configs', [])
                if isinstance(config, dict) and type(config.get('LevelPlayId')) is int}
    for play_id in sorted(play_ids):
        writes = []
        for effect in effects:
            if effect['source_action']['Name'] != 'EnableLevelPlay':
                continue
            for config in effect['source_action']['Params'].get('Configs', []):
                if config.get('LevelPlayId') == play_id and type(config.get('Enable')) is bool:
                    writes.append({**deepcopy(effect), 'enable': config['Enable']})
        definitions = [audit for audit in levelplay_audits if audit['levelplay_id'] == play_id]
        lifecycle.append({'levelplay_id': play_id, 'writes': writes,
                          'completion_gates': [g for g in gates if g['source_condition'].get('LevelId') == play_id],
                          'source_definitions': [{'definition': deepcopy(a['definition']),
                                                  'sha256': a['definition_sha256']} for a in definitions],
                          'enable_disable_pair_establishes_order': False,
                          'reason': 'separate activations and initial state need an execution dependency'})
    targets = {target for effect in effects for target in _state_targets(effect['source_action'])}
    writers = _task_state_writers(source) if source is not None and targets else {}
    shared_writers = [{'target_type': kind, 'target_id': target_id,
                       'candidate_task_writers': deepcopy(writers.get((kind, target_id), [])),
                       'scope': 'direct actions in all QuestNodeData rows; maps and actual execution unverified'}
                      for kind, target_id in sorted(targets)] if source is not None else []
    phase_relations = []
    for node in nodes:
        entries = [call for call in calls if call['node_id'] == node['Id'] and call['phase'] == 'EnterActions']
        finishes = [call for call in calls if call['node_id'] == node['Id'] and call['phase'] == 'FinishActions']
        for entry in entries:
            for finish in finishes:
                phase_relations.append({'node_id': node['Id'], 'from_call': deepcopy(entry),
                    'to_call': deepcopy(finish), 'condition': deepcopy(node.get('Condition')),
                    'order_scope': 'same_activation_entry_before_finish_invocation',
                    'requires_same_activation': True, 'invocation_order_verified': True,
                    'flow_completion_before_followup_verified': not entry['invocation_async'],
                    'whole_task_order_verified': False, 'runtime_verified': False})
    return {'flow_calls': calls, 'phase_relations': phase_relations,
            'world_effects': effects, 'levelplay_lifecycle': lifecycle,
            'shared_state_writers': shared_writers,
            'node_conditions': [{'node_id': n['Id'], 'condition': deepcopy(n.get('Condition')),
                                 'parent_node_id': n.get('ParentNodeId')} for n in nodes],
            'selected_state_keys': sorted(selected), 'whole_task_order_verified': False,
            'asynchronous_call_implies_completion': False,
            'scope': 'direct node calls, local phase prerequisites and lifecycle configuration'}


def review_sequence_dependencies(quest, nodes, source, groups=(), levelplay_audits=()):
    by_id = {node['Id']: node for node in nodes}
    sequences = []
    requirements = []
    writes, gates = [], []
    for node in nodes:
        if node.get('Type') == 'Sequence':
            children = [child['Id'] for child in nodes if child.get('ParentNodeId') == node['Id']]
            sequences.append({'node_id': node['Id'], 'child_ids_as_stored': children,
                              'sibling_order_verified': len(children) <= 1,
                              'reason': 'single_child' if len(children) <= 1 else 'no_explicit_child_execution_list'})
        for condition in finish_requirements(node.get('Condition')):
            if condition['QuestId'] == quest['Id'] and condition['ChildQuestId'] in by_id:
                requirements.append({'from_node': condition['ChildQuestId'], 'to_node': node['Id'],
                    'source_condition': deepcopy(condition), 'order_scope': 'completion_before_condition_satisfaction',
                    'condition_dependency_verified': True, 'runtime_verified': False})
        for condition in walk(node.get('Condition', {})):
            gate = equality_gate(condition)
            if gate:
                gates.append({'node_id': node['Id'], 'name': gate[0], 'value': gate[1],
                              'source_condition': deepcopy(condition)})
        for action in walk(node):
            params = action.get('Params', {})
            if action.get('Name') == 'CalculateVar' and isinstance(params, dict):
                name = local_counter(params.get('Result'))
                if name:
                    writes.append({'node_id': node['Id'], 'name': name, 'source_action': deepcopy(action)})
    cache = getattr(source, '_sequence_node_storage', None)
    if cache is None:
        read_rows = source.rows if source is not None else rows
        cache = {row['Key']: row for row in read_rows('db_QuestNodeData.db', 'questnodedata')} if nodes else {}
        if source is not None:
            source._sequence_node_storage = cache
    storage = []
    for node in nodes:
        key = f"{quest['Id']}_{node['Id']}"
        row = cache.get(key)
        storage.append(storage_evidence(row) if row else {'key': key, 'storage_schema_verified': False})
    return {'version': 1, 'sequence_groups': sequences, 'completion_requirements': requirements,
            'flow_progression': flow_progression_review(nodes, groups, levelplay_audits, source),
            'node_storage': storage,
            'controller_dependencies': controller_dependencies(quest, nodes, source),
            'variable_scope': f"quest:{quest['Id']}", 'variable_writes': writes, 'variable_gates': gates,
            'variable_initial_values_evaluated': False, 'selected_variable_branch_verified': False,
            'whole_task_order_verified': False, 'runtime_verified': False}

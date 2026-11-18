"""Local dialogue order from one task node's completed flow and finish call."""
from copy import deepcopy
from hashlib import sha256
import struct

from .coverage import validate_world_effect
from .export_task import Exporter, flow_actions, flow_key
from .levelplay_order import sync_flow
from .rendering import render_result
from .task_flows import classify_task_flows
from .terminal_text import synchronous
from .dependency_positions import adjacent_sync_dependencies


def _local_ancestors(node, by_id):
    ancestors = []
    seen = {node['Id']}
    current = node
    while current.get('ParentNodeId') in by_id:
        current = by_id[current['ParentNodeId']]
        if (current['Id'] in seen or current.get('Type') not in {'Sequence', 'ParallelSelect'}
                or any(current.get(k) for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots'))):
            return None
        if current['Type'] == 'ParallelSelect' and (type(current.get('Count')) is not int or current['Count'] < 0):
            return None
        seen.add(current['Id'])
        ancestors.append(current['Id'])
    return ancestors if ancestors and current.get('ParentNodeId') == 0 else None


def _dependency_runs(edges):
    """Combine overlapping adjacency edges into one contiguous call sequence."""
    runs = []
    current = []
    for edge in edges:
        if current and (edge['node_id'] != current[-1]['node_id']
                        or edge['from_finish_action_index'] != current[-1]['finish_action_index']):
            runs.append(current)
            current = []
        current.append(edge)
    if current:
        runs.append(current)
    return runs


def _flow_segment(key, states, source, choices, *, record_constant_writes=False):
    try:
        raw, fields = flow_actions(states[key]['BinData'])
        recorder = None
        if record_constant_writes:
            from .constant_writes import constant_write_recorder
            recorder = constant_write_recorder(raw, key)
        parser = Exporter(source=source, choices=choices, allow_incomplete=True, configured_text_order=True,
                          variable_environment=recorder)
        parser.state_key = key
        if parser.actions(raw):
            return None
    except (ValueError, KeyError, TypeError, IndexError, struct.error):
        return None
    if recorder:
        parser.unverified_content.append({'kind': 'isolated_constant_write_audit',
                                          'trace': recorder.trace, 'runtime_executed': False})
    rendered = render_result({'title': '', 'events': parser.events, 'route': {'choices': parser.decisions}})
    return {'state_key': key, 'events': rendered['events'], 'route': rendered['route'],
            'source_actions': raw, 'action_fields': fields, 'sha256': sha256(states[key]['BinData']).hexdigest(),
            'unverified_content': parser.unverified_content, 'missing_text_ids': sorted(set(parser.missing))}


def adjacent_task_sequences(quest, nodes, states, source, choices=None):
    """Retain local call order in tasks without a recap or a parsed task route."""
    by_id = {node['Id']: node for node in nodes}
    if len(by_id) != len(nodes):
        return []
    try:
        occurrences = classify_task_flows(quest, nodes)
    except ValueError:
        return []
    groups = []
    for run in _dependency_runs(adjacent_sync_dependencies(nodes)):
        edge = run[0]
        node = by_id[edge['node_id']]
        ancestors = _local_ancestors(node, by_id)
        if ancestors is None or node.get('FailedCondition') or node.get('ExitCondition'):
            continue
        actions = node['FinishActions']
        start, end = edge['from_finish_action_index'], run[-1]['finish_action_index'] + 1
        keys = [edge['from_state']] + [link['to_state'] for link in run]
        if len(set(keys)) != len(keys) or any(k not in states or len(occurrences.get(k, [])) != 1 for k in keys):
            continue
        segments = [_flow_segment(key, states, source, choices) for key in keys]
        if any(segment is None for segment in segments):
            continue
        if not any(e['kind'] in {'dialogue', 'choice', 'narration'}
                   for segment in segments for e in segment['events']):
            continue
        # Media-only segments retain their call position while their contents are deferred.
        if any(not segment['events'] for segment in segments):
            continue
        groups.append({'node_id': node['Id'], 'state_keys': keys, 'segments': segments,
            'order_scope': 'adjacent_synchronous_finish_calls', 'local_order_verified': True,
            'mainline_placement_verified': False, 'runtime_executed': False,
            'proof': {**deepcopy(edge), 'condition': deepcopy(node.get('Condition')),
                      'to_state': keys[-1], 'finish_action_index': end - 1,
                      'ancestor_ids': ancestors, 'bridge_actions': [],
                      'source_actions': deepcopy(actions[start:end]),
                      'action_indices': list(range(start, end)),
                      'run_dependencies': deepcopy(run),
                      'parallel_ancestors': [deepcopy(by_id[i]) for i in ancestors
                                             if by_id[i]['Type'] == 'ParallelSelect'],
                      'cross_branch_order_verified': False,
                      'preceding_actions': deepcopy(actions[:start]),
                      'following_actions': deepcopy(actions[end:]),
                      'scope': 'relative order of this contiguous call sequence if node completion reaches it'}})
    return groups


def independent_task_sequences(quest, nodes, states, source, existing_groups=(), choices=None):
    """Recover unique direct calls independently; multiple calls do not imply a route."""
    by_id = {node['Id']: node for node in nodes}
    if len(by_id) != len(nodes):
        return []
    used = {key for group in existing_groups for key in group['state_keys']}
    occurrences = classify_task_flows(quest, nodes)
    groups = []
    for node in nodes:
        ancestors = _local_ancestors(node, by_id)
        if (ancestors is None or node.get('Type') not in {'ChildQuest', 'Action'}
                or node.get('FailedCondition') or node.get('ExitCondition')):
            continue
        calls = [(phase, index, action) for phase in ('Actions', 'EnterActions', 'FinishActions')
                 for index, action in enumerate(node.get(phase, []))
                 if action.get('Name') == 'PlayFlow' and not action.get('Disabled', False)]
        for phase, index, call in calls:
            reference = call.get('Params', {})
            if (not isinstance(reference, dict) or set(reference) != {'FlowListName', 'FlowId', 'StateId'}
                    or not isinstance(reference['FlowListName'], str)
                    or type(reference['FlowId']) is not int or type(reference['StateId']) is not int
                    or type(call.get('Async', False)) is not bool):
                continue
            key = flow_key(reference)
            if key in used or key not in states or len(occurrences.get(key, [])) != 1:
                continue
            segment = _flow_segment(key, states, source, choices)
            if segment is None or not segment['events']:
                continue
            proof = {'source_occurrence': deepcopy(occurrences[key][0]),
                     'phase': phase, 'action_index': index, 'source_action': deepcopy(call),
                     'condition': deepcopy(node.get('Condition')), 'ancestor_ids': ancestors,
                     'bridge_actions': [], 'inter_group_order_verified': False,
                     'invocation_async': call.get('Async', False),
                     'scope': 'flow internal order if this direct call is reached'}
            if len(calls) > 1:
                proof['multiple_direct_calls'] = True
            groups.append({'node_id': node['Id'], 'state_keys': [key], 'segments': [segment],
                'order_scope': 'single_flow_without_task_order', 'local_order_verified': True,
                'mainline_placement_verified': False, 'runtime_executed': False, 'proof': proof})
            used.add(key)
    return groups


def bridge_actions_valid(actions):
    """Only inspected scene effects may lie between the two explicit calls."""
    for action in actions:
        if not isinstance(action, dict):
            return False
        name = action.get('Name')
        params = action.get('Params', {})
        if not synchronous(action, name) or not isinstance(params, dict):
            return False
        if name == 'UnlockTeleportTrigger':
            try:
                validate_world_effect(name, params)
            except ValueError:
                return False
            if type(params['TeleportId']) is not int or params['TeleportId'] <= 0:
                return False
        elif name == 'ChangeEntityState':
            if (set(params) != {'Type', 'EntityId', 'State'} or params['Type'] != 'Directly'
                    or type(params['EntityId']) is not int or params['EntityId'] <= 0
                    or not isinstance(params['State'], str) or not params['State']):
                return False
        else:
            return False
    return True


def _information_bridge(actions, source):
    """Decode explicit synchronous InformationView calls without assuming UI close timing."""
    content = []
    for index, action in enumerate(actions):
        if bridge_actions_valid([action]):
            continue
        params = action.get('Params', {})
        if (not synchronous(action, 'OpenSystemBoard') or not isinstance(params, dict)
                or set(params) != {'SystemType', 'BoardId'} or params['SystemType'] != 'InformationView'
                or type(params['BoardId']) is not int or params['BoardId'] <= 0):
            return None
        parser = Exporter(source=source, allow_incomplete=True, configured_text_order=True)
        parser.state_key = None  # A task action is not a synthetic flow-state record.
        try:
            if parser.actions([action]) or parser.missing:
                return None
        except (ValueError, KeyError, TypeError, IndexError, struct.error):
            return None
        if len(parser.events) != 1 or parser.events[0].get('kind') != 'information_board':
            return None
        events = render_result({'title': '', 'events': parser.events, 'route': {'choices': []}})['events']
        content.append({'before_segment_index': 1, 'phase': 'FinishActions', 'action_index': index,
                        'source_action': deepcopy(action), 'events': events,
                        'display_duration_verified': False, 'panel_close_timing_verified': False})
    return content or None


def local_task_sequences(quest, nodes, backbone, states, source, choices=None, *, allow_parallel_async=False,
                         allow_information_bridge=False):
    recap = {s['state_key'] for s in backbone['segments']}
    by_id = {node['Id']: node for node in nodes}
    if len(by_id) != len(nodes):
        return []
    try:
        occurrences = classify_task_flows(quest, nodes)
    except ValueError:
        return []
    groups = []
    for node in nodes:
        if (node.get('Type') != 'ChildQuest' or node.get('FailedCondition') or node.get('ExitCondition')
                or node.get('Disabled') or node.get('Slots')):
            continue
        condition = node.get('Condition', {})
        if not isinstance(condition, dict) or set(condition) != {'Type', 'Flow'} or condition['Type'] != 'PlayFlow':
            continue
        ref = condition['Flow']
        if not isinstance(ref, dict) or not sync_flow({'Name': 'PlayFlow', 'Params': ref}):
            continue
        ancestors = _local_ancestors(node, by_id)
        if ancestors is None or (not allow_parallel_async and any(by_id[i]['Type'] != 'Sequence' for i in ancestors)):
            continue
        actions = node.get('FinishActions', [])
        if not isinstance(actions, list) or not all(isinstance(action, dict) for action in actions):
            continue
        calls = [(i, action) for i, action in enumerate(actions) if action.get('Name') == 'PlayFlow']
        if len(calls) != 1:
            continue
        index, call = calls[0]
        synchronous_call = {k: v for k, v in call.items() if k != 'Async'}
        is_async = call.get('Async', False) is True
        if (type(call.get('Async', False)) is not bool or not sync_flow(synchronous_call)
                or (is_async and not allow_parallel_async)):
            continue
        intermediate = None
        if not bridge_actions_valid(actions[:index]):
            intermediate = _information_bridge(actions[:index], source) if allow_information_bridge else None
            if intermediate is None:
                continue
        keys = [flow_key(ref), flow_key(call['Params'])]
        if (keys[0] == keys[1] or any(k in recap or k not in states or len(occurrences.get(k, [])) != 1 for k in keys)):
            continue
        segments = [_flow_segment(key, states, source, choices) for key in keys]
        if any(segment is None or not any(e['kind'] in {'dialogue', 'choice', 'narration'}
                                         for e in segment['events']) for segment in segments):
            continue
        proof = {'condition': deepcopy(condition), 'finish_action_index': index,
                 'source_action': deepcopy(call), 'bridge_actions': deepcopy(actions[:index]),
                 'ancestor_ids': ancestors, 'condition_flow_completed_assumption': True,
                 'intermediate_callback_content_verified': False}
        if allow_parallel_async:
            proof.update(invocation_async=is_async, following_actions=deepcopy(actions[index + 1:]),
                         parallel_ancestors=[deepcopy(by_id[i]) for i in ancestors if by_id[i]['Type'] == 'ParallelSelect'],
                         cross_branch_order_verified=False, followup_completion_order_verified=False,
                         basis='condition flow completion precedes this node finish-action invocation')
        group = {'node_id': node['Id'], 'state_keys': keys, 'segments': segments,
            'order_scope': 'condition_completion_to_async_call' if is_async else 'same_node_condition_to_finish',
            'local_order_verified': True, 'mainline_placement_verified': False, 'runtime_executed': False,
            'proof': proof}
        if intermediate:
            group.update(order_scope='condition_completion_via_information_board', intermediate_content=intermediate)
            proof.update(panel_close_timing_verified=False,
                         basis='condition completion, information board invocation, followup invocation in one node')
        groups.append(group)
    return groups


def connect_condition_followups(quest, nodes, states, source, groups, choices=None):
    """Merge already collected flows where a task completion proves their order."""
    candidates = local_task_sequences(quest, nodes, {'segments': []}, states, source, choices,
                                      allow_parallel_async=True, allow_information_bridge=True)
    result = list(groups)
    for candidate in candidates:
        keys = set(candidate['state_keys'])
        matching = [i for i, group in enumerate(result) if keys.intersection(group['state_keys'])]
        if any(not set(result[i]['state_keys']) <= keys for i in matching):
            continue
        if any(result[i]['state_keys'] == candidate['state_keys'] for i in matching):
            continue
        previous = {segment['state_key']: segment for i in matching for segment in result[i]['segments']}
        candidate['segments'] = [previous.get(segment['state_key'], segment) for segment in candidate['segments']]
        position = min(matching, default=len(result))
        result = [group for i, group in enumerate(result) if i not in matching]
        result.insert(position, candidate)
    return result

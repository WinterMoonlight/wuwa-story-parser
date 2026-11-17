"""Conditional call order from increasing counters in one gameplay owner."""
from collections import Counter, defaultdict
from copy import deepcopy

from .export_task import flow_key, walk
from .task_local_order import _flow_segment


def local_counter(value):
    if (isinstance(value, dict) and set(value) == {'Type', 'Source', 'Name'}
            and value['Type'] == 'Int' and value['Source'] == 'Self'
            and isinstance(value['Name'], str) and value['Name']):
        return value['Name']
    return None


def int_constant(value):
    if (isinstance(value, dict) and set(value) == {'Type', 'Source', 'Value'}
            and value['Type'] == 'Int' and value['Source'] == 'Constant'
            and type(value['Value']) is int):
        return value['Value']
    return None


def equality_gate(condition):
    if not isinstance(condition, dict) or condition.get('Type') != 'CompareVar':
        return None
    if 'Conditions' in condition:
        if (set(condition) != {'Type', 'Count', 'Conditions'} or type(condition['Count']) is not int
                or condition['Count'] != 0 or not isinstance(condition['Conditions'], list)
                or len(condition['Conditions']) != 1):
            return None
        condition = condition['Conditions'][0]
    if (not isinstance(condition, dict)
            or set(condition) - {'Type', 'Var1', 'Var2', 'Compare'} or condition.get('Compare') != 'Eq'):
        return None
    for reference, constant in ((condition.get('Var1'), condition.get('Var2')),
                                (condition.get('Var2'), condition.get('Var1'))):
        name, value = local_counter(reference), int_constant(constant)
        if name is not None and value is not None:
            return name, value
    return None


def counter_writes(nodes, name):
    """Accept a closed set of direct positive increments; preserve unknown starts."""
    writes = []
    for node in nodes:
        for value in walk(node):
            action_name = value.get('Name')
            params = value.get('Params', {})
            if not isinstance(params, dict):
                if action_name in {'CalculateVar', 'SetVar'}:
                    return None
                continue
            references_counter = any(local_counter(item) == name for item in walk(params))
            if references_counter and action_name not in {'SetVar', 'CalculateVar', None}:
                return None
            if action_name == 'SetVar' and local_counter(params.get('VarLeft')) == name:
                return None
            if action_name != 'CalculateVar' or local_counter(params.get('Result')) != name:
                continue
            if (value.get('Disabled', False) or value.get('Async', False)
                    or set(params) != {'Var1', 'Var2', 'Op', 'Result'} or params['Op'] != 'Add'):
                return None
            operands = [(params['Var1'], params['Var2']), (params['Var2'], params['Var1'])]
            increments = [int_constant(right) for left, right in operands if local_counter(left) == name]
            if len(increments) != 1 or increments[0] is None or increments[0] <= 0:
                return None
            # Nested callbacks have unknown execution scopes. Only direct finish actions qualify.
            if value not in node.get('FinishActions', []):
                return None
            writes.append({'node_id': node['Id'], 'increment': increments[0],
                           'source_action': deepcopy(value)})
    return writes or None


def counter_sequences(audits, links, states, source, candidate_keys, choices=None):
    groups = []
    counts = Counter((link['levelplay_id'], link['state_key']) for link in links)
    for audit in audits:
        nodes = audit['nodes']
        by_id = {node['Id']: node for node in nodes}
        gates = defaultdict(list)
        for node in nodes:
            gate = equality_gate(node.get('Condition'))
            parent = by_id.get(node.get('ParentNodeId'), {})
            if (not gate or node.get('Type') != 'ChildQuest' or parent.get('Type') != 'ParallelSelect'
                    or type(parent.get('Count')) is not int or parent['Count'] != 0
                    or any(node.get(key) for key in ('EnterActions', 'ExitCondition', 'FailedCondition', 'FixProcessor'))):
                continue
            actions = node.get('FinishActions', [])
            calls = [(index, action) for index, action in enumerate(actions)
                     if action.get('Name') == 'PlayFlow' and not action.get('Disabled', False)]
            if len(calls) != 1 or calls[0][0] != 0:
                continue
            index, call = calls[0]
            reference = call.get('Params', {})
            if (not isinstance(reference, dict) or set(reference) != {'FlowListName', 'FlowId', 'StateId'}
                    or not isinstance(reference['FlowListName'], str)
                    or type(reference['FlowId']) is not int or type(reference['StateId']) is not int):
                continue
            key = flow_key(reference)
            if key in candidate_keys and key in states and counts[audit['levelplay_id'], key] == 1:
                gates[node['ParentNodeId'], gate[0]].append(
                    {'threshold': gate[1], 'state_key': key, 'node_id': node['Id'],
                     'condition': deepcopy(node['Condition']), 'source_action': deepcopy(call),
                     'finish_action_index': index})
        for (parent_id, name), entries in gates.items():
            if len(entries) < 2 or len({entry['threshold'] for entry in entries}) != len(entries):
                continue
            writes = counter_writes(nodes, name)
            if not writes:
                continue
            entries.sort(key=lambda entry: entry['threshold'])
            segments = [_flow_segment(entry['state_key'], states, source, choices) for entry in entries]
            if any(segment is None or not segment['events'] for segment in segments):
                continue
            groups.append({'levelplay_id': audit['levelplay_id'], 'node_id': parent_id,
                'status': 'local_order_only', 'order_scope': 'increasing_counter_invocations',
                'state_keys': [entry['state_key'] for entry in entries], 'segments': segments,
                'placement_verified': False, 'runtime_verified': False,
                'relative_invocation_order_verified': True, 'dialogue_completion_order_verified': False,
                'proof': {'variable': {'Type': 'Int', 'Source': 'Self', 'Name': name},
                          'scope_id': f"levelplay:{audit['levelplay_id']}",
                          'thresholds': entries, 'positive_writes': writes,
                          'initial_value_assumed': False, 'all_thresholds_reached_verified': False,
                          'assumptions': ['same gameplay lifecycle', 'observed local counter writes only'],
                          'scope': 'if these equality gates are reached, call order follows increasing values; asynchronous completions remain unordered'}})
    return groups

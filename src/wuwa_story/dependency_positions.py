"""Occurrence-aware evidence for local flow dependencies, not a runtime scheduler."""
from collections import defaultdict


def _sync_flow(action):
    if not isinstance(action, dict):
        return None
    if set(action) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'}:
        return None
    if action.get('Name') != 'PlayFlow' or action.get('Async', False) is not False:
        return None
    params = action.get('Params')
    if not isinstance(params, dict) or set(params) != {'FlowListName', 'FlowId', 'StateId'}:
        return None
    if not isinstance(params['FlowListName'], str) or not params['FlowListName'].strip():
        return None
    if any(type(params[k]) is not int or params[k] <= 0 for k in ('FlowId', 'StateId')):
        return None
    return f"{params['FlowListName']}_{params['FlowId']}_{params['StateId']}"


def adjacent_sync_dependencies(nodes):
    """Only direct adjacent synchronous calls in one ChildQuest finish array.

    The edge applies if execution reaches these calls during the same activation.
    It proves neither that the node executes nor that the two references identify
    unique occurrences in a recap. No sibling or indirect callback order is added.
    """
    edges = []
    for node in nodes:
        if not isinstance(node, dict) or node.get('Type') != 'ChildQuest':
            continue
        actions = node.get('FinishActions', [])
        if not isinstance(actions, list):
            continue
        for index, (first, second) in enumerate(zip(actions, actions[1:])):
            source, target = _sync_flow(first), _sync_flow(second)
            if source is None or target is None:
                continue
            edges.append({
                'from_state': source, 'from_event': 'synchronous_finish_flow_completed',
                'to_state': target, 'to_event': 'next_finish_flow_invoked',
                'node_id': node.get('Id'),
                'from_finish_action_index': index, 'finish_action_index': index + 1,
                'source_actions': [first, second],
                'scope': 'same node activation, if execution reaches both adjacent calls',
                'basis': 'adjacent synchronous PlayFlow calls in FinishActions',
                'runtime_executed': False, 'global_order_verified': False,
            })
    return edges


def dependency_positions(edges, ordered):
    """Compare only unique recap occurrences; repeated references stay unresolved."""
    positions = defaultdict(list)
    for index, key in enumerate(ordered):
        positions[key].append(index)
    result = {'conflicts': [], 'unresolved': [], 'consistent': []}
    for edge in edges:
        before = positions.get(edge['from_state'], [])
        after = positions.get(edge['to_state'], [])
        item = dict(edge, from_positions=list(before), to_positions=list(after))
        if not before or not after:
            item['reason'] = 'dependency_endpoint_absent_from_recap'
            result['unresolved'].append(item)
        elif len(before) != 1 or len(after) != 1:
            item['reason'] = 'repeated_recap_occurrences_need_callsite_mapping'
            result['unresolved'].append(item)
        elif edge['from_state'] == edge['to_state']:
            item['reason'] = 'same_reference_does_not_identify_two_distinct_calls'
            result['unresolved'].append(item)
        elif before[0] > after[0]:
            item['reason'] = 'unique_recap_occurrences_reverse_local_dependency'
            result['conflicts'].append(item)
        else:
            item['reason'] = 'unique_recap_occurrences_follow_local_dependency'
            result['consistent'].append(item)
    return result

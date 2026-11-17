"""Correct unique recap occurrences using explicit completion-to-call dependencies."""
from copy import deepcopy
import heapq

from .dependency_positions import _sync_flow, dependency_positions
from .levelplay_completion import ancestry
from .task_flows import classify_task_flows


def repair_dependency_order(quest, nodes, backbone, dependencies):
    conflicts = dependencies['recap_dependency_conflicts']
    if not conflicts:
        return []
    segments = backbone['segments']
    positions = {}
    for i, segment in enumerate(segments):
        positions.setdefault(segment['state_key'], []).append(i)
    try:
        occurrences = classify_task_flows(quest, nodes)
    except ValueError:
        return []
    proofs = []
    for edge in conflicts:
        chain, error = ancestry(edge['node_id'], nodes)
        if error or not chain or chain[0].get('Type') != 'ChildQuest':
            continue
        node = chain[0]
        if (not chain[1:] or any(n.get('Type') != 'Sequence' for n in chain[1:])
                or any(n.get(k) for n in chain for k in ('FailedCondition', 'ExitCondition', 'Slots'))
                or any(n.get('Condition') for n in chain[1:])):
            continue
        condition = node.get('Condition', {})
        if set(condition) != {'Type', 'Flow'} or condition['Type'] != 'PlayFlow':
            continue
        source = _sync_flow({'Name': 'PlayFlow', 'Params': condition['Flow']})
        actions = node.get('FinishActions', [])
        index = edge['finish_action_index']
        if not isinstance(actions, list) or index != len(actions) - 1 or index < 0:
            continue
        action = actions[index]
        if not isinstance(action, dict) or type(action.get('Async', False)) is not bool:
            continue
        target = _sync_flow({k: v for k, v in action.items() if k != 'Async'})
        if (source != edge['from_state'] or target != edge['to_state'] or source == target
                or any(len(positions.get(key, [])) != 1 or len(occurrences.get(key, [])) != 1
                       for key in (source, target))):
            continue
        valid_prefix = True
        for prefix in actions[:index]:
            params = prefix.get('Params', {}) if isinstance(prefix, dict) else {}
            if (not isinstance(prefix, dict) or prefix.get('Name') != 'AwakeEntity'
                    or prefix.get('Async', False) is not False
                    or set(prefix) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'}
                    or not isinstance(params, dict) or set(params) != {'EntityIds'}
                    or not isinstance(params['EntityIds'], list) or not params['EntityIds']
                    or any(type(i) is not int or i <= 0 for i in params['EntityIds'])):
                valid_prefix = False
                break
        if not valid_prefix:
            continue
        left, right = positions[source][0], positions[target][0]
        if any(segments[i]['status'] != 'parsed' or segments[i].get('prefix_event_count') for i in (left, right)):
            continue
        entry_range = sorted((segments[left]['entry_index'], segments[right]['entry_index']))
        if any(entry_range[0] <= p['entry_index'] <= entry_range[1]
               for p in backbone.get('phone_tip_insertions', [])):
            continue
        proofs.append({**deepcopy(edge), 'source_condition': deepcopy(condition),
                       'source_finish_actions': deepcopy(actions), 'ancestor_ids': [n['Id'] for n in chain[1:]],
                       'invocation_async': action.get('Async', False),
                       'basis': 'unique condition flow completes before same-node finish flow invocation',
                       'completion_order_verified': False, 'runtime_executed': False})
    if not proofs:
        return []
    successors = {i: set() for i in range(len(segments))}
    incoming = [0] * len(segments)
    for proof in proofs:
        left, right = positions[proof['from_state']][0], positions[proof['to_state']][0]
        if right not in successors[left]:
            successors[left].add(right)
            incoming[right] += 1
    ready = [i for i, count in enumerate(incoming) if not count]
    heapq.heapify(ready)
    order = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for following in successors[current]:
            incoming[following] -= 1
            if incoming[following] == 0:
                heapq.heappush(ready, following)
    if len(order) != len(segments):
        return []
    keys = [segments[i]['state_key'] for i in order]
    old_conflicts = {(e['from_state'], e['to_state']) for e in conflicts}
    remaining = dependency_positions(dependencies['edges'], keys)['conflicts']
    if any((e['from_state'], e['to_state']) not in old_conflicts for e in remaining):
        return []
    for proof in proofs:
        proof['corrected_from_position'] = keys.index(proof['from_state'])
        proof['corrected_to_position'] = keys.index(proof['to_state'])
    backbone['dependency_order_corrections'] = {
        'proofs': proofs, 'original_segment_keys': [s['state_key'] for s in segments],
        'ordered_segment_keys': keys, 'tie_break': 'original recap position',
        'scope': 'completed condition flow precedes subsequent invocation; other timing remains unverified'}
    backbone['segments'] = [segments[i] for i in order]
    return proofs

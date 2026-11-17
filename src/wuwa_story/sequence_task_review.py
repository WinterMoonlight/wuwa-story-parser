"""Read individual flows in flat Sequence tasks while retaining missing sibling order."""
from copy import deepcopy

from .levelplay_completion import ancestry
from .task_flows import classify_task_flows
from .task_local_order import _flow_segment


def review_sequence_task(quest, nodes, states, source, existing_groups=(), choices=None):
    if not nodes or any(n.get('Type') not in {'Sequence', 'ChildQuest', 'QuestSucceed'} for n in nodes):
        return [], None
    roots = [n for n in nodes if n.get('ParentNodeId') == 0]
    if len(roots) != 1 or roots[0]['Type'] != 'Sequence':
        return [], None
    chains = {n['Id']: ancestry(n['Id'], nodes) for n in nodes}
    if any(error for _, error in chains.values()):
        return [], None
    if any(n.get(k) for n in nodes for k in ('Slots', 'FailedCondition', 'ExitCondition')):
        return [], None
    if any(n.get('Condition') for n in nodes if n['Type'] == 'Sequence'):
        return [], None
    if any(n.get('Condition', {}).get('Type') not in {'PlayFlow', 'DoInteract', 'FinishDungeon'}
           for n in nodes if n['Type'] == 'ChildQuest'):
        return [], None
    occurrences = classify_task_flows(quest, nodes)
    used = {key for group in existing_groups for key in group['state_keys']}
    by_id = {n['Id']: n for n in nodes}
    groups, failures = [], []
    for key, calls in occurrences.items():
        if key in used or len(calls) != 1 or calls[0]['kind'] not in {'task_condition', 'task_action'}:
            continue
        call = calls[0]
        if len(call['path']) < 2 or call['path'][0] != 'nodes':
            continue
        node = by_id[call['path'][1]]
        if node['Type'] != 'ChildQuest':
            continue
        segment = _flow_segment(key, states, source, choices) if key in states else None
        if segment is None or not segment['events']:
            failures.append({'state_key': key, 'node_id': node['Id'], 'reason': 'flow_not_fully_parsed'})
            continue
        groups.append({'node_id': node['Id'], 'state_keys': [key], 'segments': [segment],
            'order_scope': 'single_flow_without_task_order', 'local_order_verified': True,
            'mainline_placement_verified': False, 'runtime_executed': False,
            'proof': {'condition': deepcopy(node.get('Condition')), 'source_occurrence': deepcopy(call),
                      'ancestor_ids': [n['Id'] for n in chains[node['Id']][0][1:]],
                      'bridge_actions': [], 'inter_group_order_verified': False,
                      'scope': 'flow internal order only; group display follows source enumeration'}})
    if not groups:
        return [], None
    sequence_groups = []
    for node in nodes:
        if node['Type'] != 'Sequence':
            continue
        children = [n['Id'] for n in nodes if n.get('ParentNodeId') == node['Id']]
        sequence_groups.append({'node_id': node['Id'], 'child_node_ids': children,
                                'child_order_verified': len(children) <= 1,
                                'reason': 'no_explicit_child_execution_order' if len(children) > 1 else 'single_child'})
    dungeon_edges, visibility_edges = [], []
    for node in nodes:
        for index, action in enumerate(node.get('FinishActions', [])):
            params = action.get('Params', {})
            if action.get('Name') == 'TeleportDungeon' and type(params.get('DungeonId')) is int:
                for target in nodes:
                    condition = target.get('Condition', {})
                    detail = condition.get('Condition', {})
                    if (condition.get('Type') == 'FinishDungeon' and detail.get('Type') == 'DungeonId'
                            and detail.get('DungeonId') == params['DungeonId']
                            and type(detail.get('Count')) is int and detail['Count'] == 1):
                        dungeon_edges.append({'from_node': node['Id'], 'to_node': target['Id'],
                            'finish_action_index': index, 'source_action': deepcopy(action),
                            'completion_condition': deepcopy(condition),
                            'scope': 'enter this dungeon and wait for its completion', 'runtime_verified': False})
            if action.get('Name') == 'SetEntityVisible' and params.get('Visible') is True:
                entities = set(params.get('EntityIds', []))
                for target in nodes:
                    condition = target.get('Condition', {})
                    if condition.get('Type') != 'DoInteract':
                        continue
                    for option in condition.get('AddOptions', []):
                        if option.get('EntityId') in entities:
                            visibility_edges.append({'from_node': node['Id'], 'to_node': target['Id'],
                                'entity_id': option['EntityId'], 'source_action': deepcopy(action),
                                'order_verified': False,
                                'reason': 'initial_visibility_and_other_activation_paths_unverified'})
    return groups, {'sequence_groups': sequence_groups, 'dungeon_completion_relations': dungeon_edges,
                    'visibility_candidates': visibility_edges, 'flow_failures': failures,
                    'whole_task_order_verified': False,
                    'display_order_is_execution_order': False,
                    'scope': 'source conditions and actions; no sibling order inferred from IDs or row order'}

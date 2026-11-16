"""Recap-only flows owned by explicitly declared and awakened quest entities."""
import hashlib
import re
from .database import embedded
from .export_task import flow_key


def linked_entity_flows(quest, nodes, missing, read_rows):
    declared = set()
    for child in quest.get('Children', []):
        match = re.fullmatch(r'e_(\d+)_(\d+)', child)
        if match:
            declared.add(tuple(map(int, match.groups())))
    roots = [n['Id'] for n in nodes if n.get('ParentNodeId') == 0 and n.get('Type') == 'Sequence']
    if len(roots) != 1:
        return []
    by_id = {n['Id']: n for n in nodes}
    def ancestry(node):
        chain, seen = [], set()
        parent = node.get('ParentNodeId')
        while parent not in roots:
            if parent in seen or parent not in by_id:
                return None
            seen.add(parent); item = by_id[parent]
            if item.get('Type') not in {'Sequence', 'ParallelSelect'} or item.get('FailedCondition') or item.get('ExitCondition'):
                return None
            if item['Type'] == 'ParallelSelect' and item.get('Count') != 1:
                return None
            chain.append(item); parent = item.get('ParentNodeId')
        return chain
    awake = {}
    for node in nodes:
        if ancestry(node) is None or node.get('Type') != 'ChildQuest' or node.get('FailedCondition') or node.get('ExitCondition'):
            continue
        for phase in ('EnterActions',):
            for index, action in enumerate(node.get(phase, [])):
                if action.get('Name') == 'AwakeEntity' and set(action.get('Params', {})) == {'EntityIds'}:
                    for entity in action['Params']['EntityIds']:
                        awake.setdefault(entity, []).append({'node_id': node['Id'], 'phase': phase,
                                                             'action_index': index, 'source_action': action, 'ancestor_chain': ancestry(node)})
    if not missing or not declared:
        return []
    grouped = {}
    for row in read_rows('db_level_entity.db', 'levelentityconfig'):
        pair = (row['MapId'], row['EntityId'])
        if pair in declared and pair[1] in awake:
            grouped.setdefault(pair, []).append(row)
    links = []
    for pair, matches in grouped.items():
        if len(matches) != 1:
            continue
        row = matches[0]
        values = [(i, v) for i, v in embedded(row['BinData']) if isinstance(v, dict)]
        if not values or any(v != values[0][1] for _, v in values):
            continue
        config = values[0][1]
        interact = config.get('InteractComponent', {})
        if (set(interact) - {'Options', 'TurnAroundType'} or not isinstance(interact.get('Options'), list) or len(interact['Options']) != 1
                or interact.get('TurnAroundType', 'PlayerTurnToInteractor') != 'PlayerTurnToInteractor'):
            continue
        option = interact['Options'][0]
        kind = option.get('Type', {})
        if set(option) - {'Type', 'OptionLockTypeList'} or option.get('OptionLockTypeList', []) not in ([], ['OnMotor']) or set(kind) != {'Type', 'Flow'} or kind['Type'] != 'Flow':
            continue
        flow = kind['Flow']
        if set(flow) != {'FlowListName', 'FlowId', 'StateId'}:
            continue
        key = flow_key(flow)
        if key not in missing:
            continue
        links.append({'state_key': key, 'map_id': pair[0], 'entity_id': pair[1],
                      'declaration': f'e_{pair[0]}_{pair[1]}', 'awake_calls': awake[pair[1]],
                      'source_row_id': row['Id'], 'source_config': config,
                      'equivalent_json_fields': [i for i, _ in values],
                      'sha256': hashlib.sha256(row['BinData']).hexdigest(),
                      'order_source': 'quest_recap', 'mandatory_verified': False,
                      'runtime_trigger_verified': False})
    # Ambiguous entity owners are not resolved by whichever row happened to be first.
    keys = [link['state_key'] for link in links]
    return links if len(keys) == len(set(keys)) else []

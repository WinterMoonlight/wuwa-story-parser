"""Inventory exact entity trigger calls; ownership is not execution or order."""
from collections import defaultdict
import hashlib
import re

from .database import embedded
from .export_task import flow_key


def action_arrays(component, value):
    """Only inspected action-bearing paths, never arbitrary embedded Flow data."""
    if not isinstance(value, dict):
        return
    if component == 'TriggerComponent':
        yield ('Actions',), value.get('Actions', [])
        exit_config = value.get('ExitConfig', {})
        if isinstance(exit_config, dict):
            yield ('ExitConfig', 'Actions'), exit_config.get('Actions', [])
    elif component == 'ClientTriggerComponent':
        for phase in ('OnTriggerEnter', 'OnTriggerExit'):
            config = value.get(phase, {})
            if isinstance(config, dict):
                yield (phase, 'Actions'), config.get('Actions', [])
    elif component == 'EntityStateComponent':
        behaviors = value.get('StateChangeBehaviors', [])
        if isinstance(behaviors, list):
            for i, behavior in enumerate(behaviors):
                if isinstance(behavior, dict):
                    yield ('StateChangeBehaviors', i, 'Action'), behavior.get('Action', [])


def entity_trigger_content(quest, source):
    declared = set()
    for child in quest.get('Children', []):
        match = re.fullmatch(r'e_(\d+)_(\d+)', str(child))
        if match:
            declared.add(tuple(map(int, match.groups())))
    if not declared:
        return [], []
    index = getattr(source, '_declared_entity_content_index', None)
    if index is None:
        index = defaultdict(list)
        for row in source.rows('db_level_entity.db', 'levelentityconfig'):
            index[row['MapId'], row['EntityId']].append(row)
        source._declared_entity_content_index = index
    links, gaps = [], []
    for pair in sorted(declared):
        declaration = f'e_{pair[0]}_{pair[1]}'
        matches = index.get(pair, [])
        if len(matches) != 1:
            gaps.append({'declaration': declaration, 'reason': 'missing_or_ambiguous_entity_row', 'rows': len(matches)})
            continue
        row = matches[0]
        configs = [(i, v) for i, v in embedded(row['BinData']) if isinstance(v, dict)]
        if not configs or any(v != configs[0][1] for _, v in configs):
            gaps.append({'declaration': declaration, 'reason': 'ambiguous_entity_config'})
            continue
        config = configs[0][1]
        for component in ('TriggerComponent', 'ClientTriggerComponent', 'EntityStateComponent'):
            value = config.get(component, {})
            for path, actions in action_arrays(component, value):
                if not isinstance(actions, list):
                    continue
                for i, action in enumerate(actions):
                    if not isinstance(action, dict) or action.get('Name') != 'PlayFlow':
                        continue
                    flow = action.get('Params')
                    source_path = [component, *path, i]
                    if (not isinstance(flow, dict) or not isinstance(flow.get('FlowListName'), str)
                            or not flow['FlowListName'] or type(flow.get('FlowId')) is not int
                            or type(flow.get('StateId')) is not int):
                        gaps.append({'declaration': declaration, 'source_path': source_path,
                                     'reason': 'malformed_flow_reference'})
                        continue
                    links.append({'state_key': flow_key(flow), 'declaration': declaration,
                        'map_id': pair[0], 'entity_id': pair[1], 'row_id': row['Id'],
                        'component': component, 'source_component': value, 'source_path': source_path,
                        'trigger_range': config.get('RangeComponent'),
                        'source_action': action, 'equivalent_json_fields': [i for i, _ in configs],
                        'source_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                        'ownership_basis': 'QuestData.Children exact map/entity pair; explicit PlayFlow action',
                        'invocation_async': action.get('Async', False),
                        'runtime_trigger_verified': False, 'order_verified': False, 'mandatory_verified': False})
    return links, gaps

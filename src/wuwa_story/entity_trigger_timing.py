"""Map-scoped lifecycle evidence for spatial dialogue, without guessing playback."""
from collections import defaultdict

from .export_task import flow_key
from .levelplay_completion import ancestry


def _lifecycle_actions(value, path=()):
    if isinstance(value, dict):
        if value.get('Name') in {'AwakeEntity', 'DestroyEntity', 'ChangeEntityState'}:
            params = value.get('Params', {})
            if isinstance(params, dict):
                ids = params.get('EntityIds', [params.get('EntityId')])
                if isinstance(ids, list):
                    yield path, value, [i for i in ids if type(i) is int]
        for key, child in value.items():
            yield from _lifecycle_actions(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _lifecycle_actions(child, path + (index,))


def entity_trigger_timing(quest, nodes, links, backbone, source):
    if not links:
        return []
    maps = defaultdict(list)
    for row in source.rows('db_instance_dungeon.db', 'instancedungeon'):
        maps[row['Id']].append(row['MapConfigId'])
    entries = (backbone or {}).get('order_source', {}).get('entries', [])
    flow_positions = defaultdict(list)
    tip_positions = defaultdict(list)
    for index, entry in enumerate(entries):
        ref = entry.get('Flow', {})
        if ref.get('FlowListName'):
            flow_positions[flow_key(ref)].append(index)
        if entry.get('TidTip'):
            tip_positions[entry['TidTip']].append(index)
    lifecycle = defaultdict(list)
    for node in nodes:
        chain, error = ancestry(node['Id'], nodes)
        owner = next((n for n in chain if type(n.get('DungeonId')) is int), quest)
        dungeon = owner.get('DungeonId')
        candidates = maps.get(dungeon, [])
        map_id = candidates[0] if not error and len(candidates) == 1 else None
        condition = node.get('Condition', {})
        ref = condition.get('Flow', {}) if condition.get('Type') == 'PlayFlow' else {}
        positions = flow_positions.get(flow_key(ref), []) if ref.get('FlowListName') else []
        actions = {phase: node[phase] for phase in ('EnterActions', 'FinishActions') if phase in node}
        for path, action, ids in _lifecycle_actions(actions):
            call = {'node_id': node['Id'], 'source_path': list(path), 'source_action': action,
                    'node_condition': condition, 'map_id': map_id, 'dungeon_id': dungeon,
                    'ancestry_error': error, 'ancestor_ids': [n['Id'] for n in chain],
                    'condition_flow_positions': list(positions),
                    'tip_positions': list(tip_positions.get(node.get('TidTip'), [])),
                    'runtime_executed': False}
            for entity_id in ids:
                lifecycle[entity_id].append((call, chain))
    result = []
    for link in links:
        calls = lifecycle.get(link['entity_id'], [])
        matching = [(call, chain) for call, chain in calls if call['map_id'] == link['map_id']]
        other = [call for call, _ in calls if call['map_id'] not in (None, link['map_id'])]
        unknown = [call for call, _ in calls if call['map_id'] is None]
        common = []
        if matching and not unknown:
            ids = set.intersection(*({n['Id'] for n in chain} for _, chain in matching))
            common = [n for n in matching[0][1] if n['Id'] in ids and n.get('Type') == 'Sequence' and n.get('Desc')]
        region = ({'node_id': common[0]['Id'], 'name': common[0]['Desc'],
                   'scope': 'shared map-scoped task ancestor; not a playback interval'} if common else None)
        reasons = ['spatial_trigger_has_no_unique_recap_call_position', 'initial_activation_state_unverified']
        if link.get('invocation_async'):
            reasons.append('asynchronous_flow_completion_order_unverified')
        if other:
            reasons.append('same_entity_number_reused_in_other_map')
        if unknown:
            reasons.append('lifecycle_call_map_unresolved')
        result.append({'state_key': link['state_key'], 'map_id': link['map_id'],
                       'entity_id': link['entity_id'], 'source_row_id': link['row_id'],
                       'source_sha256': link['source_sha256'], 'trigger_range': link.get('trigger_range'),
                       'trigger_component': link['component'], 'source_component': link['source_component'],
                       'source_action': link['source_action'], 'common_task_region': region,
                       'lifecycle_scope': 'task node EnterActions and FinishActions; nested actions retained as configuration evidence',
                       'matching_map_lifecycle': [call for call, _ in matching],
                       'other_map_lifecycle': other, 'unknown_map_lifecycle': unknown,
                       'recap_occurrences': list(flow_positions.get(link['state_key'], [])),
                       'placement_status': 'unresolved', 'placement_verified': False,
                       'runtime_verified': False, 'reasons': reasons})
    return result

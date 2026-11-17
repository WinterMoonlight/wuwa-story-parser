"""Associate explicit dungeon transitions with uniquely mapped gameplay text."""
from collections import defaultdict
import hashlib

from .declared_levelplay import declared_levelplays, one_config
from .export_task import flow_key


def dungeon_candidates(task_nodes, source):
    calls = defaultdict(list)
    for node in task_nodes:
        for phase in ('EnterActions', 'FinishActions', 'Actions'):
            for index, action in enumerate(node.get(phase, [])):
                if action.get('Name') != 'TeleportDungeon':
                    continue
                params = action.get('Params', {})
                dungeon_id = params.get('DungeonId')
                if type(dungeon_id) is not int or dungeon_id <= 0:
                    continue
                calls[dungeon_id].append({'node_id': node['Id'], 'phase': phase,
                                          'action_index': index, 'source_action': action})
    if not calls:
        return [], [], []
    dungeons = defaultdict(list)
    for row in source.rows('db_instance_dungeon.db', 'instancedungeon'):
        dungeons[row['Id']].append(row)
    definitions = defaultdict(list)
    for row in source.rows('db_LevelPlayData.db', 'levelplaydata'):
        try:
            definition = one_config(row)
        except ValueError:
            continue
        if definition.get('Type') == 'Dungeon':
            definitions[definition.get('LevelId')].append((row, definition))
    links, gaps, audits = [], [], []
    for dungeon_id, call_sites in sorted(calls.items()):
        matches = dungeons[dungeon_id]
        if len(matches) != 1:
            gaps.append({'dungeon_id': dungeon_id, 'reason': 'missing_or_ambiguous_dungeon'})
            continue
        row = matches[0]
        map_id = row['MapConfigId']
        plays = definitions[map_id]
        if len(plays) != 1:
            gaps.append({'dungeon_id': dungeon_id, 'map_id': map_id,
                         'reason': 'missing_or_ambiguous_dungeon_gameplay'})
            continue
        play_row, definition = plays[0]
        play_id = play_row['LevelPlayId']
        candidate_links, candidate_gaps, candidate_audits = declared_levelplays(
            {'Children': [f'l_{map_id}_{play_id}']}, task_nodes, [], source)
        proof = {'dungeon_id': dungeon_id, 'map_id': map_id, 'levelplay_id': play_id,
                 'dungeon_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                 'call_sites': call_sites,
                 'basis': 'TeleportDungeon.DungeonId to instance MapConfigId to unique Dungeon LevelId',
                 'runtime_trigger_verified': False, 'order_verified': False}
        for link in candidate_links:
            link.update(ownership_basis=proof['basis'], dungeon_link=proof)
        for audit in candidate_audits:
            audit['dungeon_link'] = proof
            # A condition's flow is an explicit completion reference, distinct
            # from an action invocation. Preserve that distinction in evidence.
            for node in audit['nodes']:
                condition = node.get('Condition', {})
                flow = condition.get('Flow', {})
                if (condition.get('Type') != 'PlayFlow'
                        or set(flow) != {'FlowListName', 'FlowId', 'StateId'}
                        or not isinstance(flow['FlowListName'], str)
                        or not flow['FlowListName']
                        or type(flow['FlowId']) is not int or type(flow['StateId']) is not int):
                    continue
                candidate_links.append({'state_key': flow_key(flow), 'levelplay_id': play_id,
                    'map_id': map_id, 'node_id': node['Id'], 'phase': 'Condition',
                    'source_condition': condition, 'source_row_key': f"{play_id}_{node['Id']}",
                    'source_sha256': audit['node_sha256'][f"{play_id}_{node['Id']}"],
                    'ownership_basis': proof['basis'], 'dungeon_link': proof,
                    'reference_kind': 'flow_completion_condition',
                    'runtime_trigger_verified': False, 'order_verified': False})
        links.extend(candidate_links)
        gaps.extend(dict(gap, dungeon_id=dungeon_id) for gap in candidate_gaps)
        audits.extend(candidate_audits)
    return links, gaps, audits

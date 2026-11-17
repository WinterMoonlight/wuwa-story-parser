"""Exact quest-child gameplay ownership, with call sites but no guessed sibling order."""
from collections import defaultdict
import hashlib
import re
from .database import embedded
from .export_task import flow_key, walk


def one_config(row):
    values = [v for _, v in embedded(row['BinData']) if isinstance(v, dict)]
    if not values or any(v != values[0] for v in values):
        raise ValueError('ambiguous_json_fields')
    return values[0]


def declared_levelplays(quest, task_nodes, entries, source):
    declared = set()
    for child in quest.get('Children', []):
        match = re.fullmatch(r'l_(\d+)_(\d+)', str(child))
        if match:
            declared.add(tuple(map(int, match.groups())))
    if not declared:
        return [], [], []
    cache = getattr(source, '_declared_levelplay_index', None)
    if cache is None:
        definitions, nodes = defaultdict(list), defaultdict(list)
        for row in source.rows('db_LevelPlayData.db', 'levelplaydata'):
            definitions[row['LevelPlayId']].append(row)
        for row in source.rows('db_LevelPlayNodeData.db', 'levelplaynodedata'):
            match = re.fullmatch(r'(\d+)_(\d+)', row['Key'])
            if match:
                nodes[int(match[1])].append(row)
        cache = definitions, nodes
        source._declared_levelplay_index = cache
    definitions, node_rows = cache
    links, gaps, audits = [], [], []
    for map_id, play_id in sorted(declared):
        declaration = f'l_{map_id}_{play_id}'
        try:
            if len(definitions[play_id]) != 1:
                raise ValueError('missing_or_ambiguous_definition')
            row = definitions[play_id][0]
            definition = one_config(row)
            if definition.get('Id') != play_id or definition.get('LevelId') != map_id:
                raise ValueError('definition_id_or_map_mismatch')
            decoded = [(r, one_config(r)) for r in node_rows[play_id]]
            by_id = {n['Id']: n for _, n in decoded}
            if not decoded or len(by_id) != len(decoded):
                raise ValueError('missing_or_duplicate_nodes')
            if any(str(n['Id']) != r['Key'].split('_')[1] for r, n in decoded):
                raise ValueError('node_key_id_mismatch')
        except (ValueError, KeyError, TypeError) as exc:
            gaps.append({'declaration': declaration, 'reason': str(exc)})
            continue
        activations = []
        for node in task_nodes:
            condition = node.get('Condition', {})
            if condition.get('Type') == 'CheckLevelPlay' and play_id in condition.get('LevelPlayIds', []):
                activations.append({'node_id': node['Id'], 'source_node': node,
                                    'recap_tip_positions': [i for i, e in enumerate(entries)
                                        if node.get('TidTip') and e.get('TidTip') == node['TidTip']],
                                    'scope': 'task_region_only_not_dialogue_anchor'})
        audit = {'declaration': declaration, 'levelplay_id': play_id, 'map_id': map_id,
                 'definition': definition, 'definition_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                 'nodes': [n for _, n in decoded],
                 'node_sha256': {r['Key']: hashlib.sha256(r['BinData']).hexdigest() for r, _ in decoded},
                 'task_conditions': activations, 'placement_verified': False,
                 'order_limitations': ['ParentNodeId alone does not order siblings',
                     'Asynchronous invocation does not establish dialogue completion',
                     'Parallel failure, repeat and recovery paths are not executed']}
        audits.append(audit)
        for r, node in decoded:
            ancestors, seen = [], {node['Id']}
            parent = node.get('ParentNodeId', 0)
            valid = True
            while parent:
                if parent in seen or parent not in by_id:
                    valid = False
                    break
                seen.add(parent); ancestor = by_id[parent]
                ancestors.append(ancestor); parent = ancestor.get('ParentNodeId', 0)
            if not valid:
                gaps.append({'declaration': declaration, 'node_id': node['Id'], 'reason': 'invalid_ancestry'})
                continue
            condition = node.get('Condition', {})
            if condition.get('Type') == 'PlayFlow':
                flow = condition.get('Flow')
                if (isinstance(flow, dict) and isinstance(flow.get('FlowListName'), str)
                        and flow['FlowListName'] and type(flow.get('FlowId')) is int
                        and type(flow.get('StateId')) is int):
                    links.append({'state_key': flow_key(flow), 'declaration': declaration,
                                  'levelplay_id': play_id, 'map_id': map_id, 'node_id': node['Id'],
                                  'phase': 'Condition', 'source_path': ['Condition', 'Flow'],
                                  'source_condition': condition,
                                  'reference_kind': 'flow_completion_condition',
                                  'ancestor_ids': [a['Id'] for a in ancestors],
                                  'ancestor_types': [a.get('Type') for a in ancestors],
                                  'failure_ancestor': any(a.get('Type') == 'QuestFailed' for a in [node]+ancestors),
                                  'source_row_key': r['Key'], 'source_sha256': hashlib.sha256(r['BinData']).hexdigest(),
                                  'ownership_basis': 'QuestData.Children exact map/levelplay pair',
                                  'order_verified': False, 'runtime_trigger_verified': False})
                else:
                    gaps.append({'declaration': declaration, 'node_id': node['Id'],
                                 'phase': 'Condition', 'reason': 'malformed_flow_reference'})
            for phase in ('Actions', 'EnterActions', 'FinishActions'):
                for index, action in enumerate(node.get(phase, [])):
                    flow = action.get('Params', {})
                    if action.get('Name') != 'PlayFlow' or not isinstance(flow, dict):
                        continue
                    if not (isinstance(flow.get('FlowListName'), str) and flow['FlowListName']
                            and type(flow.get('FlowId')) is int and type(flow.get('StateId')) is int):
                        gaps.append({'declaration': declaration, 'node_id': node['Id'],
                                     'phase': phase, 'action_index': index, 'reason': 'malformed_flow_reference'})
                        continue
                    links.append({'state_key': flow_key(flow), 'declaration': declaration,
                                  'levelplay_id': play_id, 'node_id': node['Id'], 'phase': phase,
                                  'action_index': index, 'source_action': action,
                                  'ancestor_ids': [a['Id'] for a in ancestors],
                                  'ancestor_types': [a.get('Type') for a in ancestors],
                                  'failure_ancestor': any(a.get('Type') == 'QuestFailed' for a in [node]+ancestors),
                                  'source_row_key': r['Key'], 'source_sha256': hashlib.sha256(r['BinData']).hexdigest(),
                                  'invocation_async': action.get('Async', False),
                                  'ownership_basis': 'QuestData.Children exact map/levelplay pair',
                                  'order_verified': False, 'runtime_trigger_verified': False})
    return links, gaps, audits

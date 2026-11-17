"""Inventory explicit quest-child interactions; never infer route order from ownership."""
from collections import defaultdict
import hashlib
import re

from .database import embedded
from .export_task import walk, flow_key


def declared_entity_content(quest, source):
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
        matches = index.get(pair, [])
        if len(matches) != 1:
            gaps.append({'declaration': f'e_{pair[0]}_{pair[1]}',
                         'reason': 'missing_or_ambiguous_entity_row', 'rows': len(matches)})
            continue
        row = matches[0]
        configs = [(i, v) for i, v in embedded(row['BinData']) if isinstance(v, dict)]
        if not configs or any(v != configs[0][1] for _, v in configs):
            gaps.append({'declaration': f'e_{pair[0]}_{pair[1]}', 'reason': 'ambiguous_entity_config'})
            continue
        config = configs[0][1]
        for component in ('BubbleComponent', 'InteractComponent'):
            value = config.get(component, {})
            keys = set()
            for flow in walk(value):
                if (isinstance(flow.get('FlowListName'), str) and flow['FlowListName']
                        and type(flow.get('FlowId')) is int and type(flow.get('StateId')) is int):
                    keys.add(flow_key(flow))
            for key in sorted(keys):
                links.append({'state_key': key, 'declaration': f'e_{pair[0]}_{pair[1]}',
                              'map_id': pair[0], 'entity_id': pair[1], 'row_id': row['Id'],
                              'component': component, 'source_component': value,
                              'equivalent_json_fields': [i for i, _ in configs],
                              'source_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                              'ownership_basis': 'QuestData.Children exact map/entity pair',
                              'runtime_trigger_verified': False, 'order_verified': False,
                              'mandatory_verified': False})
    return links, gaps

"""Resolve recap references through exact tip ownership and dungeon map evidence."""
import hashlib
from collections import defaultdict
from .database import embedded


def linked_levelplays(nodes, entries, read_rows):
    from .export_task import walk, flow_key
    tips = {e.get('TidTip') for e in entries if e.get('TidTip')}
    dungeon_ids = {o['Condition']['DungeonId'] for o in walk(nodes)
                   if o.get('Type') == 'FinishDungeon' and
                   o.get('Condition', {}).get('Type') == 'DungeonId'}
    if not tips or not dungeon_ids:
        return []
    dungeons = [r for r in read_rows('db_instance_dungeon.db', 'instancedungeon') if r['Id'] in dungeon_ids]
    maps = {r['MapConfigId'] for r in dungeons}
    groups = defaultdict(list)
    for row in read_rows('db_LevelPlayNodeData.db', 'levelplaynodedata'):
        values = [v for _, v in embedded(row['BinData']) if isinstance(v, dict)]
        if len(values) == 1:
            groups[int(row['Key'].split('_')[0])].append((row, values[0]))
    links = []
    for row in read_rows('db_LevelPlayData.db', 'levelplaydata'):
        values = [v for _, v in embedded(row['BinData']) if isinstance(v, dict)]
        if len(values) != 1:
            continue
        definition = values[0]
        group = groups[row['LevelPlayId']]
        matched = sorted(tips & {n.get('TidTip') for _, n in group})
        if not matched or definition.get('Type') != 'Dungeon' or definition.get('LevelId') not in maps:
            continue
        associated = [n for _, n in group]
        refs = sorted({flow_key(o) for o in walk([definition, associated])
                       if o.get('FlowListName') and 'FlowId' in o and 'StateId' in o})
        links.append({'levelplay_id': row['LevelPlayId'], 'matched_tip_ids': matched,
                      'dungeon_ids': [r['Id'] for r in dungeons if r['MapConfigId'] == definition['LevelId']],
                      'map_id': definition['LevelId'], 'flow_references': refs,
                      'definition': definition, 'nodes': associated,
                      'definition_sha256': hashlib.sha256(row['BinData']).hexdigest(),
                      'node_sha256': {r['Key']: hashlib.sha256(r['BinData']).hexdigest() for r, _ in group},
                      'runtime_executed': False})
    return links


def reconcile(references, ordered, links):
    linked = {key for link in links for key in link['flow_references']}
    return bool(ordered) and len(ordered) == len(set(ordered)) and bool(links) and references | linked == set(ordered)

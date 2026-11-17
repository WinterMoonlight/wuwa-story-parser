"""Inspect exported node storage and relationships without treating row order as execution."""
import hashlib
import struct
from .database import field, string
from .levelplay_completion import ancestry


def storage_evidence(row):
    blob = row['BinData']
    result = {'key': row['Key'], 'sha256': hashlib.sha256(blob).hexdigest(),
              'storage_schema_verified': False, 'execution_order_verified': False}
    try:
        root = struct.unpack_from('<I', blob)[0]
        vtable = root - struct.unpack_from('<i', blob, root)[0]
        size = struct.unpack_from('<H', blob, vtable)[0]
        if size < 4 or size % 2:
            raise ValueError('invalid_vtable')
        count = (size - 4) // 2
        present = [i for i in range(count) if field(blob, i) is not None]
        result.update(field_count=count, present_fields=present)
        if present == [0, 1] and string(blob, 0) == row['Key']:
            import json
            value = json.loads(string(blob, 1))
            if not isinstance(value, dict):
                raise ValueError('node_json_not_object')
            result.update(storage_schema_verified=True, layout='key_and_json_only',
                          json_keys=sorted(value))
        else:
            result['reason'] = 'additional_or_unknown_fields'
    except (ValueError, IndexError, UnicodeError, struct.error) as exc:
        result['reason'] = str(exc)
    return result


def pair_evidence(nodes, start, end):
    left, le = ancestry(start, nodes)
    right, re = ancestry(end, nodes)
    result = {'from_node': start, 'to_node': end, 'execution_order_verified': False,
              'from_ancestry': [n['Id'] for n in left], 'to_ancestry': [n['Id'] for n in right]}
    if le or re:
        result['reason'] = le or re
        return result
    shared = next((n for n in left if n['Id'] in {r['Id'] for r in right}), None)
    result['common_ancestor'] = {'node_id': shared['Id'], 'type': shared['Type']} if shared else None
    result['reason'] = 'ancestry_without_execution_edge'
    return result


def node_order_audit(audit, fragment, task_nodes, entries, quest_id, source):
    cache = getattr(source, '_node_order_storage', None)
    if cache is None:
        cache = {}
        for db, table in [('db_QuestNodeData.db', 'questnodedata'),
                          ('db_LevelPlayNodeData.db', 'levelplaynodedata')]:
            cache[db] = {r['Key']: r for r in source.rows(db, table)}
        source._node_order_storage = cache
    play_nodes = audit['nodes']
    success = sorted(n['Id'] for n in play_nodes if n.get('Type') == 'QuestSucceed')
    gameplay = [pair_evidence(play_nodes, fragment['node_id'], end) for end in success]
    # Exact condition-flow matches only. These are possible recap correspondences, not successor edges.
    from .export_task import flow_key
    positions = {}
    for i, e in enumerate(entries):
        flow = e.get('Flow', {})
        if flow.get('FlowListName'):
            positions.setdefault(flow_key(flow), []).append(i)
    matches = []
    for n in task_nodes:
        c = n.get('Condition', {})
        if c.get('Type') != 'PlayFlow' or not c.get('Flow', {}).get('FlowListName'):
            continue
        key = flow_key(c['Flow'])
        if key not in positions:
            continue
        for gate in audit['task_conditions']:
            relation = pair_evidence(task_nodes, gate['node_id'], n['Id'])
            relation.update(state_key=key, recap_entry_indices=positions[key])
            matches.append(relation)
    storage = []
    for db, prefix, nodes in [('db_QuestNodeData.db', quest_id, task_nodes),
                              ('db_LevelPlayNodeData.db', audit['levelplay_id'], play_nodes)]:
        for n in sorted(nodes, key=lambda n: n['Id']):
            key = f'{prefix}_{n["Id"]}'
            row = cache[db].get(key)
            storage.append(dict(storage_evidence(row), database=db) if row else
                           {'key': key, 'database': db, 'reason': 'missing_node_row', 'storage_schema_verified': False})
    return {'gameplay_to_success': gameplay, 'task_gate_to_recap_conditions': matches,
            'node_storage': storage, 'execution_order_verified': False,
            'scope': 'exported node records and exact condition-flow correspondences only; not engine runtime',
            'sort_policy': 'IDs sorted for audit display only, never execution'}

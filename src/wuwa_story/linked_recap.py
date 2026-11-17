"""Recover a task's remaining flows from a uniquely linked recap-only record."""
from copy import deepcopy
from hashlib import sha256

from .database import embedded
from .dependency_positions import _sync_flow
from .dependencies import dependency_report
from .unplaced import completion_only_flows


def _recap_only_tree(nodes):
    """Allow no executable tree, or the inspected constant-success placeholder tree."""
    if not nodes:
        return True
    if len(nodes) != 3 or len({n.get('Id') for n in nodes}) != 3:
        return False
    roots = [n for n in nodes if n.get('Type') == 'Sequence' and n.get('ParentNodeId') == 0]
    steps = [n for n in nodes if n.get('Type') == 'ChildQuest']
    ends = [n for n in nodes if n.get('Type') == 'QuestSucceed']
    if len(roots) != 1 or len(steps) != 1 or len(ends) != 1:
        return False
    if any(n.get('ParentNodeId') != roots[0]['Id'] for n in steps + ends):
        return False
    allowed = {'Type', 'Id', 'Desc', 'ParentNodeId', 'Condition', 'TidTip', 'HideTip',
               'HideUiExceptTaskList', 'FinishActions'}
    if any(set(n) - allowed or n.get('FinishActions') for n in nodes):
        return False
    if any(n.get('Condition') for n in roots + ends):
        return False
    condition = steps[0].get('Condition', {})
    if set(condition) != {'Type', 'Condition'} or condition['Type'] != 'CheckConditionGroup':
        return False
    group = condition['Condition']
    if (not isinstance(group, dict) or set(group) != {'Type', 'Conditions'}
            or type(group['Type']) is not int or group['Type'] != 0
            or not isinstance(group['Conditions'], list) or len(group['Conditions']) != 1):
        return False
    compare = group['Conditions'][0]
    if (not isinstance(compare, dict) or set(compare) != {'Type', 'Var1', 'Compare', 'Var2'}
            or compare['Type'] != 'CompareVar' or compare['Compare'] != 'Eq'):
        return False
    value = compare['Var1']
    return (isinstance(value, dict) and set(value) == {'Type', 'Source', 'Value'}
            and value['Type'] == 'Int' and value['Source'] == 'Constant'
            and type(value['Value']) is int and value == compare['Var2'])


def _candidate_anchor(quest, candidate, entries, nodes, remaining):
    """Match explicit ownership and a source-task tip; never compare IDs as order."""
    if (candidate.get('Type') != 11 or candidate.get('Id') == quest['Id']
            or candidate.get('ProvideType') != {'Conditions': [{'Type': 'PreQuest', 'PreQuest': quest['Id']}]}
            or candidate.get('ChapterId') != quest.get('ChapterId')
            or candidate.get('DungeonId') != quest.get('DungeonId')
            or candidate.get('ActiveActions') or candidate.get('Children')
            or candidate.get('Reference') != [f"q_{quest['Id']}"]
            or set(candidate.get('WeakReference', [])) - {f"q_{quest['Id']}"}
            or not isinstance(entries, list) or len(entries) < 2):
        return None
    header = entries[0]
    if (not isinstance(header, dict) or header.get('Flow') != {'FlowListName': '', 'FlowId': 0, 'StateId': 0}
            or not header.get('TidTip') or header.get('IsHideUi', False)):
        return None
    keys = []
    for entry in entries[1:]:
        if not isinstance(entry, dict) or entry.get('TidTip') or entry.get('IsHideUi', False):
            return None
        key = _sync_flow({'Name': 'PlayFlow', 'Params': entry.get('Flow')})
        if key is None:
            return None
        keys.append(key)
    if len(set(keys)) != len(keys) or set(keys) != set(remaining):
        return None
    roots = [n['Id'] for n in nodes if n.get('Type') == 'Sequence' and n.get('ParentNodeId') == 0]
    anchors = [n for n in nodes if n.get('TidTip') == header['TidTip']]
    if (len(roots) != 1 or len(anchors) != 1 or anchors[0].get('Type') != 'ChildQuest'
            or anchors[0].get('ParentNodeId') != roots[0]
            or anchors[0].get('Condition', {}).get('Type') != 'ReachArea'
            or any(anchors[0].get(k) for k in ('Disabled', 'FailedCondition', 'ExitCondition'))):
        return None
    owned = completion_only_flows(quest, nodes, set(keys))
    if len(owned) != len(keys):
        return None
    return {'state_keys': keys, 'anchor_node_id': anchors[0]['Id'],
            'source_tip': header['TidTip'], 'source_header': deepcopy(header),
            'owned_flows': deepcopy(owned)}


def recover_linked_recap(quest, nodes, result, states, source, choices=None):
    remaining = {p['state_key'] for p in result.get('source', {}).get(
        'recap_reference_resolution', {}).get('unplaced_task_flows', [])}
    if not remaining or not result.get('events'):
        return {'sections': [], 'candidates': []}
    quest_rows = source.rows('db_QuestData.db', 'questdata')
    node_rows = source.rows('db_QuestNodeData.db', 'questnodedata')
    books = source.rows('db_PlotHandBook.db', 'plothandbookconfig')
    candidates = []
    for row in quest_rows:
        definitions = [v for _, v in embedded(row['BinData']) if isinstance(v, dict)]
        if not definitions or any(v != definitions[0] for v in definitions):
            continue
        candidate = definitions[0]
        if (candidate.get('ProvideType') != {'Conditions': [{'Type': 'PreQuest', 'PreQuest': quest['Id']}]}
                or candidate.get('Type') != 11):
            continue
        qid = candidate['Id']
        matches = [r for r in books if r['QuestId'] == qid]
        candidate_nodes = []
        for node_row in node_rows:
            if node_row['Key'].split('_', 1)[0] != str(qid):
                continue
            values = [v for _, v in embedded(node_row['BinData']) if isinstance(v, dict)]
            if not values or any(v != values[0] for v in values):
                candidate_nodes.append({})
            else:
                candidate_nodes.append(values[0])
        if len(matches) != 1 or not _recap_only_tree(candidate_nodes):
            continue
        arrays = [v for _, v in embedded(matches[0]['BinData']) if isinstance(v, list)]
        if len(arrays) != 1:
            continue
        anchor = _candidate_anchor(quest, candidate, arrays[0], nodes, remaining)
        if anchor:
            candidates.append((candidate, row, matches[0], anchor, candidate_nodes))
    review = {'sections': [], 'candidates': [item[0]['Id'] for item in candidates]}
    if len(candidates) != 1:
        review['reason'] = 'no_unique_recap_only_record_covering_remaining_owned_flows'
        return review
    candidate, quest_row, book_row, anchor, candidate_nodes = candidates[0]
    qid = candidate['Id']
    if sum(r['QuestId'] == qid for r in quest_rows) != 1:
        review['reason'] = 'ambiguous_linked_quest_definition'
        return review
    primary_order = [s['state_key'] for s in result['source'].get('scenes', [])]
    if not primary_order or remaining.intersection(primary_order):
        review['reason'] = 'missing_or_overlapping_primary_recap'
        return review
    dependencies = dependency_report(quest, nodes, primary_order + anchor['state_keys'])
    if dependencies['recap_dependency_conflicts'] or dependencies['recap_dependency_unresolved']:
        review['reason'] = 'linked_recap_conflicts_with_or_does_not_cover_task_call_dependencies'
        return review
    from .recap_backbone import build_backbone
    backbone = build_backbone(qid, [book_row], states, source, choices=choices)
    if (not backbone or backbone['blocked_segments'] or any(s.get('missing_text_ids')
            or s.get('status') != 'parsed' or not s['events'] for s in backbone['segments'])):
        review['reason'] = 'linked_recap_not_fully_parsed'
        return review
    section = {'source_quest_id': qid, 'insert_after_primary_events': len(result['events']),
        'order_scope': 'linked_recap_sections', 'section_order_verified': True,
        'runtime_verified': False, 'mandatory_interactions_verified': False,
        'proof': {**anchor, 'candidate_definition': deepcopy(candidate),
            'candidate_placeholder_nodes': deepcopy(candidate_nodes),
            'quest_row_sha256': sha256(quest_row['BinData']).hexdigest(),
            'handbook_row_sha256': sha256(book_row['BinData']).hexdigest(),
            'source_entries': deepcopy(next(v for _, v in embedded(book_row['BinData']) if isinstance(v, list))),
            'primary_order_source': deepcopy(result['source'].get('order_source')),
            'task_dependency_check': dependencies,
            'basis': 'recap-only successor record, exact parent-task tip and complete owned-flow match',
            'runtime_node_order_verified': False},
        'segments': backbone['segments']}
    review['sections'] = [section]
    review['reason'] = 'unique_linked_recap_section'
    return review

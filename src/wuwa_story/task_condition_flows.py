"""Extract direct completion flows and verified serialized gender branches."""
from copy import deepcopy
import struct

from .dependency_positions import _sync_flow
from .task_flows import classify_task_flows
from .task_local_order import _flow_segment, _local_ancestors


def _gender(condition):
    if (not isinstance(condition, dict) or set(condition) != {'Type', 'Conditions'}
            or type(condition['Type']) is not int or condition['Type'] != 0
            or not isinstance(condition['Conditions'], list) or len(condition['Conditions']) != 1):
        return None
    atom = condition['Conditions'][0]
    if (not isinstance(atom, dict) or set(atom) != {'Type', 'Gender'}
            or atom['Type'] != 'CheckPlayerGender' or atom['Gender'] not in ('女', '男')):
        return None
    return atom['Gender']


def _branch_copies(node, parent_id, by_id, path):
    """Verify each inline node against its separately stored node definition."""
    if not isinstance(node, dict) or type(node.get('Id')) is not int:
        return None
    stored = by_id.get(node['Id'])
    if stored is None or stored.get('ParentNodeId') != parent_id:
        return None
    if 'ParentNodeId' in node and node['ParentNodeId'] != parent_id:
        return None
    inline_value = {k: v for k, v in node.items() if k not in {'Children', 'ParentNodeId'}}
    stored_value = {k: v for k, v in stored.items() if k not in {'Children', 'ParentNodeId'}}
    if inline_value != stored_value:
        return None
    children = node.get('Children', [])
    if not isinstance(children, list) or any(not isinstance(child, dict) or type(child.get('Id')) is not int for child in children):
        return None
    if {n['Id'] for n in by_id.values() if n.get('ParentNodeId') == node['Id']} != {child['Id'] for child in children}:
        return None
    copies = [{'node_id': node['Id'], 'inline_path': path}]
    for index, child in enumerate(children):
        descendants = _branch_copies(child, node['Id'], by_id, path + ['Children', index])
        if descendants is None:
            return None
        copies.extend(descendants)
    ids = [copy['node_id'] for copy in copies]
    return copies if len(ids) == len(set(ids)) else None


def _female_projection(nodes):
    by_id = {n['Id']: n for n in nodes}
    selected, rejected = [], []
    projected = deepcopy(by_id)
    for node in nodes:
        if node.get('Type') != 'ConditionSelector':
            continue
        slots = node.get('Slots')
        branches = []
        if (isinstance(slots, list) and len(slots) == 2 and not node.get('Disabled')
                and not any(node.get(k) for k in ('Condition', 'ExitCondition', 'FailedCondition',
                                                'Actions', 'EnterActions', 'FinishActions'))):
            for index, slot in enumerate(slots):
                if not isinstance(slot, dict) or set(slot) != {'Condition', 'Node'}:
                    break
                gender = _gender(slot['Condition'])
                copies = _branch_copies(slot['Node'], node['Id'], by_id,
                                        ['nodes', node['Id'], 'Slots', index, 'Node'])
                if gender is None or copies is None:
                    break
                branches.append({'slot_index': index, 'gender': gender, 'copies': copies})
        all_ids = [c['node_id'] for b in branches for c in b['copies']]
        roots = {s['Node'].get('Id') for s in slots if isinstance(s, dict) and isinstance(s.get('Node'), dict)} if isinstance(slots, list) else set()
        stored_roots = {n['Id'] for n in nodes if n.get('ParentNodeId') == node['Id']}
        if (len(branches) != 2 or {b['gender'] for b in branches} != {'女', '男'}
                or roots != stored_roots
                or len(all_ids) != len(set(all_ids))):
            rejected.append({'selector_id': node['Id'], 'reason': 'unverified_gender_branch_or_inline_copy'})
            continue
        female = next(b for b in branches if b['gender'] == '女')
        male = next(b for b in branches if b['gender'] == '男')
        projected[node['Id']] = {k: deepcopy(v) for k, v in node.items() if k != 'Slots'}
        projected[node['Id']]['Type'] = 'Sequence'
        for copy in male['copies']:
            projected.pop(copy['node_id'], None)
        selected.append({'selector_id': node['Id'], 'selected_gender': 'female',
                         'selected_slot': female['slot_index'], 'verified_inline_copies': female['copies'],
                         'excluded_node_ids': [c['node_id'] for c in male['copies']],
                         'source_selector': deepcopy(node), 'sibling_order_inferred': False})
    return list(projected.values()), selected, rejected


def condition_task_sequences(quest, nodes, states, source, existing_groups=(), choices=None):
    """Keep selected condition-flow text ordered internally, with global order open."""
    if len({n['Id'] for n in nodes}) != len(nodes):
        return [], None
    projected, selections, rejected = _female_projection(nodes)
    by_id = {n['Id']: n for n in projected}
    try:
        occurrences = classify_task_flows(quest, projected)
    except ValueError:
        return [], None
    used = {key for group in existing_groups for key in group['state_keys']}
    groups, failures = [], []
    for node in projected:
        if node.get('Type') != 'ChildQuest' or any(node.get(k) for k in ('FailedCondition', 'ExitCondition', 'Slots', 'Disabled')):
            continue
        ancestors = _local_ancestors(node, by_id)
        condition = node.get('Condition', {})
        if ancestors is None or not isinstance(condition, dict) or set(condition) != {'Type', 'Flow'}:
            continue
        if condition['Type'] != 'PlayFlow':
            continue
        key = _sync_flow({'Name': 'PlayFlow', 'Params': condition['Flow']})
        if key is None or key in used or len(occurrences.get(key, [])) != 1:
            continue
        try:
            segment = _flow_segment(key, states, source, choices) if key in states else None
        except struct.error:
            segment = None
        if segment is None or not segment['events']:
            failures.append({'node_id': node['Id'], 'state_key': key, 'reason': 'flow_not_parsed'})
            continue
        gender_proofs = [s for s in selections if node['Id'] in {c['node_id'] for c in s['verified_inline_copies']}]
        groups.append({'node_id': node['Id'], 'state_keys': [key], 'segments': [segment],
                       'order_scope': 'single_flow_without_task_order', 'local_order_verified': True,
                       'mainline_placement_verified': False, 'runtime_executed': False,
                       'proof': {'phase': 'Condition', 'condition': deepcopy(condition),
                                 'source_occurrence': deepcopy(occurrences[key][0]),
                                 'ancestor_ids': ancestors, 'gender_selections': deepcopy(gender_proofs),
                                 'inter_group_order_verified': False,
                                 'scope': 'selected direct completion flow internal order'}})
        used.add(key)
    review = {'gender': 'female', 'gender_selections': selections, 'rejected_selectors': rejected,
              'flow_failures': failures, 'whole_task_order_verified': False}
    return groups, review if groups or selections or rejected or failures else None

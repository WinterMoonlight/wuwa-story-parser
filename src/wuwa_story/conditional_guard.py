"""Reject known contradictions to a bounded conditional-recap variable projection.

This is a guard, not a task interpreter. Passing it does not prove absence of
external writers, callback execution, or task-runtime adjacency.
"""
from copy import deepcopy


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def conditional_variable_guard(writer_actions, writer_node, selector, nodes, reference):
    """Return evidence and rejection reasons without executing task actions."""
    reasons = []
    checked = []
    parent_order = 'not_available'

    for action in _walk(writer_actions):
        if action.get('Name') and action.get('Async', False) is not False:
            reasons.append({'code': 'async_writer_action', 'action': deepcopy(action)})

    def inspect(value, location):
        checked.append(location)
        for action in _walk(value):
            name = action.get('Name')
            if name == 'SetVar':
                params = action.get('Params')
                left = params.get('VarLeft') if isinstance(params, dict) else None
                # A well-formed other variable is not an overwrite of this one.
                if isinstance(left, dict) and left.get('Source') in ('Self', 'Global'):
                    key = 'Name' if left['Source'] == 'Self' else 'Keyword'
                    if isinstance(left.get(key), str) and left[key]:
                        if left.get('Source') != reference.get('Source'):
                            continue
                        if left[key] != reference.get(key):
                            continue
                reasons.append({'code': 'possible_variable_overwrite', 'location': location,
                                'action': deepcopy(action)})
            elif name in ('FinishState', 'ChangeState'):
                reasons.append({'code': 'intervening_state_control', 'location': location,
                                'action': deepcopy(action)})

    inspect(writer_node.get('FinishActions', []), 'writer.FinishActions')
    inspect(selector.get('EnterActions', []), 'selector.EnterActions')
    parents = [n for n in nodes if n.get('Id') == writer_node.get('ParentNodeId')]
    if len(parents) == 1 and parents[0].get('Type') == 'Sequence' and 'Children' in parents[0]:
        children = parents[0]['Children']
        if not isinstance(children, list):
            reasons.append({'code': 'invalid_parent_children'})
        else:
            ids = [c.get('Id') if isinstance(c, dict) else c for c in children]
            wi, si = writer_node.get('Id'), selector.get('Id')
            if ids.count(wi) != 1 or ids.count(si) != 1:
                reasons.append({'code': 'ambiguous_parent_child_order'})
            elif ids.index(wi) >= ids.index(si):
                reasons.append({'code': 'parent_order_contradicts_recap'})
            else:
                parent_order = 'explicit_children'
                for index in range(ids.index(wi) + 1, ids.index(si)):
                    child = children[index]
                    matches = [n for n in nodes if n.get('Id') == ids[index]]
                    # Inspect both embedded and flat copies: contradictions are
                    # evidence, not a reason to silently prefer one representation.
                    values = ([child] if isinstance(child, dict) else []) + matches
                    if not values:
                        reasons.append({'code': 'unresolved_intermediate_child', 'node_id': ids[index]})
                    for value in values:
                        inspect(value, 'parent.Children[%s]' % index)
    return {'allowed': not reasons, 'reasons': reasons, 'checked_locations': checked,
            'parent_order_evidence': parent_order, 'external_writers_verified_absent': False,
            'runtime_order_verified': False}

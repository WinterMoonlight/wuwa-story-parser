"""Exact tip/node/flow ownership for conditional recap sections.

Annotations do not prove condition values or task runtime completion.
"""
from collections import defaultdict


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _nodes(value):
    if not isinstance(value, dict):
        return
    yield value
    for child in value.get('Children', []):
        yield from _nodes(child)
    for slot in value.get('Slots', []):
        yield from _nodes(slot.get('Node'))


def _flow(value):
    if not isinstance(value, dict) or not value.get('FlowListName'):
        return None
    if 'FlowId' not in value or 'StateId' not in value:
        return None
    return f"{value['FlowListName']}_{value['FlowId']}_{value['StateId']}"


def annotate_branch_entries(entries, nodes):
    """Map exact recap occurrences to a unique selector slot via their tip.

    Return annotations keyed by entry index. A flow is tagged only if it is
    explicitly referenced by the current unique tip node; unrelated following
    flows are never inherited. Multiple/nested selector memberships stay unknown.
    """
    by_id = defaultdict(list)
    tips = defaultdict(list)
    for node in nodes:
        by_id[node.get('Id')].append(node)
        if node.get('TidTip'):
            tips[node['TidTip']].append(node)
    memberships = defaultdict(set)
    conditions = {}
    for node in nodes:
        if node.get('Type') != 'ConditionSelector' or len(by_id[node.get('Id')]) != 1:
            continue
        for slot_index, slot in enumerate(node.get('Slots', [])):
            token = (node['Id'], slot_index)
            conditions[token] = slot.get('Condition')
            for child in _nodes(slot.get('Node')):
                if type(child.get('Id')) is int and child.get('Type'):
                    memberships[child['Id']].add(token)
    annotations = {}
    active = None
    for index, entry in enumerate(entries):
        tip = entry.get('TidTip')
        if tip:
            active = None
            owners = tips.get(tip, [])
            if len(owners) == 1:
                owner = owners[0]
                tags = memberships.get(owner['Id'], set())
                if len(tags) == 1 and len(by_id[owner['Id']]) == 1:
                    token = next(iter(tags))
                    # Exclude child trees: only this tip node's own calls qualify.
                    own = {k: v for k, v in owner.items() if k not in {'Children', 'Slots'}}
                    refs = {_flow(o) for o in _walk(own)} - {None}
                    active = ({'selector_id': token[0], 'slot_index': token[1],
                               'node_id': owner['Id'], 'tip': tip,
                               'condition': conditions[token]}, refs)
                    if not _flow(entry.get('Flow')):
                        annotations[index] = dict(active[0], basis='unique_tip_node')
        key = _flow(entry.get('Flow'))
        if key and active and key in active[1]:
            annotations[index] = dict(active[0], basis='unique_tip_and_exact_flow', state_key=key)
    return annotations
